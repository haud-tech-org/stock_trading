# --- Python Standard Library ---
import os
import sys
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, cast, Dict

# --- Third-Party Libraries ---
import pandas as pd

# --- Project Imports ---
from ..utils.symbol_utils import sanitize_symbol_for_filename
from src.stockreports.config import loader
from src.stockreports.services.external.notification_services.orchestrator import NotificationServiceOrchestrator
from src.stockreports.data_services import DataServiceOrchestrator
from src.stockreports.utils.data_utils import load_data_for_development
from src.stockreports.utils.time_utils import SESSIONS, TimeSimulator, TIMEZONE
from src.stockreports.alert.model.models import AlertResult
from src.stockreports.alert.common.validation.validation import calculate_alert_performance
from src.stockreports.alert.common.profitability_simulator import simulate_profitability
from src.stockreports.utils.report_utils import save_profitability_report, save_alert_report, update_alert_summary
from src.stockreports.utils.approach_utils import get_approach_executor
from src.stockreports.alert.announce.orchestrator import AnnouncementAlertOrchestrator
from src.stockreports.services.executor_configuration_service.orchestrator import ExecutorConfigurationOrchestrator
from src.stockreports.model.approach_type import ApproachType


# --- Path Setup ---
# This is handled by the entry-point script, but kept for robustness
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Settings Loader ---
# This MUST be the first project import to ensure settings are fresh.
settings = loader.get_settings()
notification_settings = loader.get_notification_settings()
validation_settings = loader.get_validation_settings()
data_provider_settings = loader.get_data_provider_settings()

# --- Constants & Configuration ---
DEFAULT_APPROACH = "VRA"


def ensure_alert_result(result: object) -> AlertResult:
    """
    Type guard function to ensure executor.run() returns AlertResult.
    
    Validates at runtime that the returned object is an AlertResult instance,
    providing explicit type safety for further processing.
    
    Args:
        result (object): The return value from executor.run()
        
    Returns:
        AlertResult: The validated AlertResult instance
        
    Raises:
        TypeError: If the result is not an AlertResult instance
        
    Example:
        result: AlertResult = ensure_alert_result(executor.run(df=daily_df, new_candle_count=10))
        if result.has_alerts:
            for _, alert_row in result.alerts.iterrows():
                # Process alert_row
    """
    if not isinstance(result, AlertResult):
        raise TypeError(
            f"executor.run() must return AlertResult, got {type(result).__name__}. "
            f"Value: {result}"
        )
    return cast(AlertResult, result)


class SymbolAlerter:
    """
    Manages the entire alerting lifecycle for a single stock symbol.
    """
    def __init__(self, symbol: str):
        """
        Initializes the alerter for a specific symbol.
        """
        self.symbol = symbol
        self.notification_orchestrator = NotificationServiceOrchestrator.get_instance()

        # Setup logging FIRST (before any code that uses self.logger)
        self._setup_logging()

        # Now initialize resolution dataframes (no more ResolutionCoordinator)
        self._init_resolution_dataframes()

    def _init_resolution_dataframes(self) -> None:
        """
        Initialize resolution storage for this symbol.
        Uses ExecutorConfigurationOrchestrator to get all enabled approaches and their resolutions.
        Always includes resolution 1 (1-minute) for price alerter compatibility.
        """
        try:
            approaches = ExecutorConfigurationOrchestrator.get_supported_approaches(self.symbol)
            resolutions_set = {ExecutorConfigurationOrchestrator.get(self.symbol, a).resolution for a in approaches}
            resolutions_set.add(1)  # Always add 1-minute resolution
            
            # Initialize dict: resolution (int) → DataFrame
            self._resolution_dataframes: Dict[int, Optional[pd.DataFrame]] = {
                resolution: None for resolution in sorted(resolutions_set)
            }
            
            self.logger.info(
                f"Initialized resolution storage for {len(self._resolution_dataframes)} resolutions"
            )
            self.logger.debug(f"Resolutions: {list(self._resolution_dataframes.keys())}")
        
        except Exception as e:
            self.logger.error(f"Failed to initialize resolution dataframes: {e}")
            # Fallback: Always at least have 1-minute resolution
            self._resolution_dataframes = {1: None}

    def _update_resolution_dataframes(self, from_dt: pd.Timestamp, to_dt: pd.Timestamp) -> bool:
        """
        Update all resolution dataframes with new data.
        
        Mirrors the master_df accumulation logic but does it per resolution:
        - Fetch new data for each resolution
        - Concat with existing data (same dedup/sort logic as master_df)
        
        Symbol is already self.symbol (instance property), so we only iterate resolutions.
        
        Args:
            from_dt: Start time
            to_dt: End time
            
        Returns:
            bool: True if at least one resolution has data, False if all empty
        """
        orchestrator = DataServiceOrchestrator()
        has_data = False
        
        for resolution in self._resolution_dataframes.keys():
            try:
                self.logger.debug(f"Fetching {resolution}-min data for symbol {self.symbol}...")
                
                # Fetch data for this resolution
                latest_df = orchestrator.fetch_and_process(
                    symbol=self.symbol,
                    start_time=from_dt,
                    end_time=to_dt,
                    resolution=resolution
                )
                
                # Handle fetch failure
                if latest_df is None or latest_df.empty:
                    self.logger.debug(f"No new data for {self.symbol} at {resolution}-min resolution")
                    continue
                
                # CRITICAL: Mirror master_df accumulation logic
                # If first time, initialize. Otherwise, concat and deduplicate.
                if self._resolution_dataframes[resolution] is None:
                    # First fetch for this resolution
                    self._resolution_dataframes[resolution] = latest_df
                    self.logger.debug(f"Initialized {resolution}-min resolution with {len(latest_df)} rows")
                else:
                    # Concat new data with existing
                    self._resolution_dataframes[resolution] = pd.concat([
                        self._resolution_dataframes[resolution],
                        latest_df
                    ])
                    # Remove duplicates (same as master_df logic line 328)
                    self._resolution_dataframes[resolution] = self._resolution_dataframes[resolution][
                        ~self._resolution_dataframes[resolution].index.duplicated(keep='last')
                    ]
                    # Sort index (same as master_df logic line 329)
                    self._resolution_dataframes[resolution] = self._resolution_dataframes[resolution].sort_index()
                    self.logger.debug(f"Merged into {resolution}-min resolution, now {len(self._resolution_dataframes[resolution])} rows total")
                
                has_data = True
            
            except Exception as e:
                self.logger.error(f"Failed to fetch data for {self.symbol} at {resolution}-min resolution: {e}")
                continue
        
        return has_data

    def _setup_logging(self):
        """Configures logging to file and console."""
        log_dir = os.path.join(project_root, "logs", settings.MODE.lower())
        os.makedirs(log_dir, exist_ok=True)

        # Sanitize symbol name for use in filename (use utility)
        sanitized_symbol = sanitize_symbol_for_filename(self.symbol)
        log_file_path = os.path.join(log_dir, f"alerter_{sanitized_symbol}.log")

        # Use a logger specific to this symbol instance
        self.logger = logging.getLogger(f"SymbolAlerter.{self.symbol}")
        # Avoid adding handlers if they already exist
        if not self.logger.handlers:
            # File handler
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            self.logger.addHandler(file_handler)

            # Console handler
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            self.logger.addHandler(stream_handler)

        self.logger.info(f"Logging configured for {self.symbol}. Log file: {log_file_path}")




    def execute(self):
        self.logger.info(f"Executing alerter for symbol: {self.symbol}...")
        if settings.MODE == "DEVELOPMENT":
            self._run_development_mode()
        elif settings.MODE == "DEPLOYMENT":
            self._run_deployment_mode()
        self.logger.critical(f"Execution finished for symbol: {self.symbol}.")

    def _enrich_and_save_reports(self, result: AlertResult, processing_date: str):
        """
        Enriches the alert result with suggested prices and saves all relevant reports.
        """
        # This function now only saves the report, enrichment is done prior.
        save_alert_report(result, self.symbol, processing_date)
        if settings.MODE == "DEVELOPMENT":
            update_alert_summary(result, self.symbol, processing_date)

    def _run_development_mode(self):
        self.logger.info(f"Running in DEVELOPMENT mode for {self.symbol}.")
        master_df = load_data_for_development(self.symbol)
        if master_df.empty:
            self.logger.error(f"No data loaded for {self.symbol} in development mode, cannot proceed.")
            return
        
        dates_to_process = sorted(master_df.index.strftime('%Y-%m-%d').unique())
        
        for processing_date in dates_to_process:
            self._process_date(master_df, processing_date)

    def _run_deployment_mode(self):
        """
        Acts as a resilient supervisor for the monitoring session.
        If the session crashes, this function logs the error and restarts it.
        If the session completes cleanly (replay or live), it exits.
        """
        self.logger.info(f"Entering resilient deployment mode for {self.symbol}.")
        while True:
            try:
                # This function returns True when the monitoring loop finishes without error.
                session_completed_cleanly = self._perform_monitoring_session()

                # If the session finished its work, break the supervisor loop.
                if session_completed_cleanly:
                    self.logger.info(f"Monitoring session for {self.symbol} completed successfully. Exiting supervisor.")
                    break

            except KeyboardInterrupt:
                self.logger.info(f"Stopping real-time monitor for {self.symbol}.")
                break  # Exit the supervisor loop.
            except Exception as e:
                self.logger.critical(
                    f"The monitoring session for {self.symbol} crashed. Restarting... Error: {e}",
                    exc_info=True
                )
                # In live mode, wait before restarting. In replay, stop immediately on error.
                if settings.DEBUG_REPLAY_START_TIME is None:
                    self.logger.info(f"Waiting for {settings.MONITORING_INTERVAL_SECONDS} seconds before restarting...")
                    time.sleep(settings.MONITORING_INTERVAL_SECONDS)
                else:
                    self.logger.error("Exiting replay due to critical error.")
                    break

    def _perform_monitoring_session(self) -> bool:
        """
        Executes a single, continuous monitoring session for the symbol.
        
        Orchestrates three main monitoring tasks:
        1. Scheduled close position notifications (symbol-only)
        2. Price movement alerter (symbol + fixed resolution=1)
        3. Approach executors (symbol + approach + resolution from config)
        
        All time management (timezone, trading hours) depends on symbol configuration only.
        Data is fetched for all required resolutions in one batch.

        Returns:
            bool: True if the session completed without error, signaling a clean exit.
        """
        # ════════════════════════════════════════════════════════════════
        # INITIALIZATION PHASE
        # ════════════════════════════════════════════════════════════════
        

        # [1] Validate symbol has approaches configured
        self.logger.info(f"[INIT] Validating symbol {self.symbol} has approaches configured...")
        all_approaches = ExecutorConfigurationOrchestrator.get_supported_approaches(self.symbol)
        if not all_approaches:
            self.logger.error(
                f"Symbol {self.symbol} has no approaches configured. "
                f"Cannot run monitoring session. Skipping..."
            )
            return True  # Return True to signal clean exit (not an error)
        self.logger.info(f"[INIT] Found {len(all_approaches)} approaches for {self.symbol}: {all_approaches}")

        # [2] Load symbol-level trading hours (ONCE - trading hours are symbol-dependent)
        self.logger.info(f"[INIT] Loading symbol-level trading hours for {self.symbol}...")
        try:
            symbol_trading_hours = ExecutorConfigurationOrchestrator.get_symbol_trading_hours(self.symbol)
            self.logger.info(f"[INIT] Loaded trading hours: {symbol_trading_hours.get_sessions_summary()}")
        except Exception as e:
            self.logger.error(
                f"[INIT] Failed to load trading hours for {self.symbol}. "
                f"Cannot proceed without trading hours definition. Error: {e}"
            )
            return True  # Clean exit (not an error)

        # [3] Collect all required resolutions upfront
        # - Price alerter always needs resolution 1
        # - Each approach needs its configured resolution
        self.logger.debug("[INIT] Collecting required data resolutions...")
        required_resolutions = set([1])  # Price alerter always uses 1-min
        approach_resolutions = {}
        for approach_name in all_approaches:
            try:
                approach_config = ExecutorConfigurationOrchestrator.get(self.symbol, approach_name)
                resolution = approach_config.resolution
                required_resolutions.add(resolution)
                approach_resolutions[approach_name] = resolution
                self.logger.debug(f"[INIT]   {approach_name}: requires {resolution}-min resolution")
            except Exception as e:
                self.logger.warning(
                    f"[INIT] Could not load config for {approach_name}. "
                    f"Skipping this approach. Error: {e}"
                )
                continue
        self.logger.info(
            f"[INIT] Required resolutions: {sorted(required_resolutions)} "
            f"(total: {len(required_resolutions)})"
        )

        # [4] Initialize resolution-keyed data storage
        self._resolution_dataframes = {res: None for res in sorted(required_resolutions)}
        self.logger.debug(f"[INIT] Initialized resolution storage for: {list(self._resolution_dataframes.keys())}")

        # [5] Initialize time simulator with symbol-level trading hours
        self.logger.info("[INIT] Initializing TimeSimulator with symbol trading hours...")
        time_simulator = TimeSimulator(
            replay_start_str=settings.DEBUG_REPLAY_START_TIME,
            interval_seconds=settings.MONITORING_INTERVAL_SECONDS,
            trading_hours=symbol_trading_hours
        )
        self.logger.info(
            f"[INIT] TimeSimulator ready - Mode: {'REPLAY' if time_simulator.is_replay_mode() else 'LIVE'}, "
            f"Timezone: {symbol_trading_hours.timezone}, "
            f"Processing Date: {time_simulator.processing_date}"
        )
        self.logger.info(
            f"[INIT] Session initialization complete. "
            f"Resolutions={list(self._resolution_dataframes.keys())}, "
            f"Approaches={all_approaches}"
        )
        
        # ════════════════════════════════════════════════════════════════
        # MAIN MONITORING LOOP
        # ════════════════════════════════════════════════════════════════
        
        self.logger.info(f"[LOOP] Starting main monitoring loop for {self.symbol}...")
        
        master_df = pd.DataFrame()

        # This is the main operational loop for fetching and analyzing data.
        # Main monitoring loop
        while time_simulator.is_running():
            current_time = time_simulator.get_current_time()
            
            # --- Check for scheduled 'Close Position' notifications ---
            # Task 1: Symbol-only dependency
            self.logger.debug("[TASK-1] Scheduler: Checking for scheduled notifications...")
            self.notification_orchestrator.process_scheduled_notifications(current_time)

            # Check if within trading hours before fetching data and processing
            # Uses symbol-level trading hours configuration (not approach-level)
            if not time_simulator.is_trading_hours(current_time):
                self.logger.debug(
                    f"[LOOP] Outside trading hours ({current_time.strftime('%H:%M:%S')}). "
                    f"Waiting for next interval..."
                )
                if time_simulator.is_replay_mode():
                    time_simulator.advance()  # Move time forward to find next trading window
                    continue
                else:
                    time.sleep(900)  # In live mode, wait 15 minutes
                    continue
            
            self.logger.info(f"\n--- New Interval for {self.symbol}: Analyzing at {current_time.strftime('%Y-%m-%d %H:%M:%S')} ---")

            # Define the time window for the data fetch
            to_dt: pd.Timestamp = current_time
            if self._resolution_dataframes[1] is None:  # Use resolution 1 as indicator of first run
                # First run: fetch all data from the start of the day
                # Use symbol-level trading hours sessions
                all_starts = [session.start_time for session in symbol_trading_hours.sessions]
                start_time_str = min(all_starts)
                start_h, start_m = map(int, start_time_str.split(':'))
                from_dt: pd.Timestamp = to_dt.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
            else:
                # Subsequent runs: fetch data from the last known point in time for resolution 1
                last_known_time = self._resolution_dataframes[1].index.max()
                from_dt: pd.Timestamp = last_known_time

            from_timestamp = int(from_dt.timestamp())
            to_timestamp = int(to_dt.timestamp())

            # ✅ UPDATE ALL RESOLUTION DATAFRAMES
            has_data = self._update_resolution_dataframes(from_dt, to_dt)
            
            # ✅ Handle no data available
            if not has_data:
                if not time_simulator.is_replay_mode():
                    self.logger.warning(f"Failed to fetch data for {self.symbol} or data is empty. Retrying...")
                    time.sleep(settings.MONITORING_INTERVAL_SECONDS)
                else:
                    self.logger.warning(f"No data available for {self.symbol} in replay mode. Advancing...")
                continue
            
            # Check if 1-min data is available (all approaches need it)
            if self._resolution_dataframes[1] is None or self._resolution_dataframes[1].empty:
                self.logger.warning("No 1-min resolution data available. Cannot proceed with analysis.")
                time_simulator.advance()
                continue

            # --- Announcement Alert Orchestrator (TASK 2: Announce approaches) ---
            self.logger.debug("[TASK-2] Announcement Alert Orchestrator: Starting analysis...")
            announce_approaches = ExecutorConfigurationOrchestrator.get_supported_approaches(self.symbol, ApproachType.ANNOUNCE)
            for approach_name in announce_approaches:
                announce_resolution = approach_resolutions.get(approach_name)
                if announce_resolution is None:
                    self.logger.warning(f"[TASK-2] No configured resolution for {approach_name}. Skipping analysis.")
                    continue
                announce_df = self._resolution_dataframes.get(announce_resolution).copy()
                if announce_df is not None and not announce_df.empty:
                    alert_result: AlertResult = AnnouncementAlertOrchestrator.run(
                        approach=approach_name,
                        symbol=self.symbol,
                        master_df=announce_df
                    )
                    if alert_result.has_alerts:
                        self.logger.info(f"[TASK-2] Found {len(alert_result.confirmed_alerts)} {approach_name} alerts.")
                        for alert in alert_result.confirmed_alerts:
                            self.notification_orchestrator.send_notification(alert)
                    else:
                        self.logger.debug(f"[TASK-2] No {approach_name} alerts detected.")
                else:
                    self.logger.debug(f"[TASK-2] Data not available at {announce_resolution}-min, skipping {approach_name}.")

            # --- Standard Approach Alerters (TASK 3: Trade approaches) ---
            trade_approaches = ExecutorConfigurationOrchestrator.get_supported_approaches(self.symbol, ApproachType.TRADE)
            self.logger.debug(f"[TASK-3] Approach Executors: Starting {len(trade_approaches)} approaches...")
            if trade_approaches:
                for approach_name in trade_approaches:
                    self.logger.info(f"[TASK-3] --- Running Approach: {approach_name} for {self.symbol} ---")
                    resolution = approach_resolutions.get(approach_name)
                    if resolution is None:
                        self.logger.error(f"[TASK-3] No resolution found for {approach_name}. Should have been validated during initialization.")
                        continue
                    self.logger.debug(f"[TASK-3]   {approach_name}: using {resolution}-min resolution")
                    approach_df = self._resolution_dataframes.get(resolution)
                    if approach_df is None or approach_df.empty:
                        self.logger.warning(f"[TASK-3] No data for {approach_name} at {resolution}-min resolution")
                        continue
                    executor = get_approach_executor(self.symbol, approach_name, resolution)
                    if not executor:
                        self.logger.warning(f"[TASK-3] Could not instantiate executor for {approach_name}")
                        continue
                    new_candle_count = len(approach_df)
                    self.logger.debug(f"[TASK-3] Executing {approach_name} with {new_candle_count} candles at {resolution}-min resolution")
                    result: AlertResult = ensure_alert_result(
                        executor.run(df=approach_df.copy(), new_candle_count=new_candle_count)
                    )
                    if result.has_alerts:
                        self.logger.info(f"[TASK-3] Found {len(result.confirmed_alerts)} alerts from {approach_name}")
                        for alert in result.confirmed_alerts:
                            self.notification_orchestrator.send_notification(alert)
                        self._enrich_and_save_reports(result, time_simulator.processing_date)
                    else:
                        self.logger.debug(f"[TASK-3] No alerts from {approach_name}")
            
            self.logger.info(f"[LOOP] Interval finished. Advancing time...")
            time_simulator.advance()
            # In live mode, we still need to wait for the actual interval time to pass.
            if not time_simulator.is_replay_mode():
                time.sleep(settings.MONITORING_INTERVAL_SECONDS)

        self.logger.info(f"[LOOP] Monitoring session for {self.symbol} has concluded.")
        # The session finished cleanly, return True to stop the supervisor loop.
        return True

    def _process_date(self, master_df, processing_date):
        self.logger.info(f"\n{'='*20} Processing Date: {processing_date} for {self.symbol} {'='*20}")
        start_date = pd.Timestamp(processing_date, tz=TIMEZONE).replace(hour=0, minute=0, second=0)
        end_date = start_date + timedelta(days=1)
        daily_df = master_df.loc[start_date:end_date].copy()
        # Remove the end_date boundary (loc is inclusive on both ends)
        daily_df = daily_df[daily_df.index < end_date]

        if daily_df.empty:
            self.logger.warning(f"No data found for {self.symbol} on {processing_date}.")
            return

        # Load symbol configuration for trading hours (symbol-level, not approach-level)
        try:
            symbol_config = ExecutorConfigurationOrchestrator.get_supported_approaches(self.symbol)
            if not symbol_config:
                self.logger.warning(f"No configuration found for {self.symbol}. Using global trading hours.")
                symbol_trading_hours_for_filter = None
            else:
                first_approach = symbol_config[0]
                config = ExecutorConfigurationOrchestrator.get(self.symbol, first_approach)
                symbol_trading_hours_for_filter = config.trading_hours
        except Exception as e:
            self.logger.warning(f"Could not load symbol trading hours. Using global settings. Error: {e}")
            symbol_trading_hours_for_filter = None

        # Filter by trading hours (use symbol-level trading hours if available)
        if symbol_trading_hours_for_filter:
            # Use symbol-level trading hours
            combined_mask = pd.Series([False] * len(daily_df), index=daily_df.index)
            time_col = daily_df.index.time
            for session in symbol_trading_hours_for_filter.sessions:
                start_time = datetime.strptime(session.start_time, '%H:%M').time()
                end_time = datetime.strptime(session.end_time, '%H:%M').time()
                session_mask = (time_col >= start_time) & (time_col <= end_time)
                combined_mask = combined_mask | session_mask
            daily_df = daily_df[combined_mask]
        elif SESSIONS:
            # Fallback to global SESSIONS
            combined_mask = pd.Series([False] * len(daily_df), index=daily_df.index)
            time_col = daily_df.index.time
            for session_name, hours in SESSIONS.items():
                start_time = datetime.strptime(hours['start'], '%H:%M').time()
                end_time = datetime.strptime(hours['end'], '%H:%M').time()
                session_mask = (time_col >= start_time) & (time_col <= end_time)
                combined_mask = combined_mask | session_mask
            daily_df = daily_df[combined_mask]

        if daily_df.empty:
            self.logger.warning(f"No data for {self.symbol} on {processing_date} after filtering by trading hours.")
            return
        
        self.logger.info(f"Loaded {len(daily_df)} data points for {self.symbol} on {processing_date}.")
        
        all_alerts_for_day = []
        
        # Get approaches for this symbol
        approaches_to_run = ExecutorConfigurationOrchestrator.get_supported_approaches(self.symbol)
        
        if not approaches_to_run:
            self.logger.warning(
                f"Symbol {self.symbol} has no approaches configured. "
                f"Skipping analysis for {processing_date}."
            )
            return
        
        # Collect resolutions for each approach
        approach_resolutions = {}
        for approach_name in approaches_to_run:
            try:
                config = ExecutorConfigurationOrchestrator.get(self.symbol, approach_name)
                approach_resolutions[approach_name] = config.resolution
            except Exception as e:
                self.logger.warning(f"Could not load resolution for {approach_name}: {e}")
                continue
        
        for approach_name in approaches_to_run:
            self.logger.info(f"\n--- Running Approach: {approach_name} for {self.symbol} on {processing_date} ---")
            
            # Get resolution for this approach (from config, not coordinator)
            resolution = approach_resolutions.get(approach_name)
            if resolution is None:
                self.logger.warning(f"No resolution configured for {approach_name}. Skipping.")
                continue
            
            executor = get_approach_executor(self.symbol, approach_name, resolution)
            if not executor:
                continue
            
            # Pass the full length of the daily dataframe as new_candle_count in development mode
            result: AlertResult = ensure_alert_result(
                executor.run(df=daily_df.copy(), new_candle_count=len(daily_df))
            )
            
            if result.has_alerts:
                # Alerts are already enriched with suggested prices from base Executor.update_alert_suggestions()
                # (called during alert creation in Executor._create_alert_with_details)
                
                # Send notifications (fire-and-forget)
                for alert in result.confirmed_alerts:
                    self.notification_orchestrator.send_notification(alert)

                # Further enrich with validation data and save reports
                if settings.MODE == "DEVELOPMENT":
                    for alert in result.confirmed_alerts:  # Type: AlertData (inferred from List[AlertData])
                        alert.symbol = self.symbol
                        validated_alert = calculate_alert_performance(alert, daily_df, validation_settings.VALIDATION_PERIOD_MINUTES)
                        # Copy validated fields back to alert
                        alert.status = validated_alert.status
                        alert.profit_loss = validated_alert.profit_loss
                        alert.time_to_best_price = validated_alert.time_to_best_price
                        alert.min_expected_profit_loss = validated_alert.min_expected_profit_loss
                        alert.validation_price_time = validated_alert.validation_price_time
                
                self._enrich_and_save_reports(result, processing_date)
                
                # Collect alerts for end-of-day profitability simulation
                all_alerts_for_day.extend([a.to_dict() for a in result.confirmed_alerts])

        if settings.MODE == "DEVELOPMENT" and all_alerts_for_day:
            self.logger.info(f"\n--- Running Profitability Simulation for {self.symbol} on {processing_date} ---")
            simulation_summary = simulate_profitability(all_alerts_for_day, daily_df)
            
            # Log the summary in a readable format
            self.logger.info("Profitability Simulation Summary:")
            self.logger.info(f"  Total Trades: {simulation_summary.total_trades}")
            self.logger.info(f"  Successful Trades: {simulation_summary.successful_trades} ({simulation_summary.success_rate})")
            self.logger.info(f"  Failed Trades: {simulation_summary.failed_trades} ({simulation_summary.failure_rate})")
            self.logger.info(f"  Total Profit/Loss: {simulation_summary.total_profit_loss:.2f}")

            # Save the detailed report using the new utility function
            save_profitability_report(
                summary_data=simulation_summary,
                symbol=self.symbol,
                date_str=processing_date,
                logger_instance=self.logger
            )
