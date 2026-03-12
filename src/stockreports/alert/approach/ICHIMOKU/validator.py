from typing import Tuple, Optional
import pandas as pd

from src.stockreports.alert.common.constants import Signal
from .settings import IchimokuSettings


class IchimokuValidator:
    """
    Validate Ichimoku signal conditions and components.
    Pure validation functions - no state, no logging.
    """
    
    # ===== DATA VALIDATION (APPROACH-SPECIFIC) =====
    
    @staticmethod
    def validate_data_sufficiency(df: pd.DataFrame, settings: IchimokuSettings) -> Tuple[bool, str]:
        """
        Validate that dataframe has sufficient candles for Ichimoku calculation.
        
        Ichimoku requires:
        - Senkou B: 52 periods for calculation
        - Chikou: 26 periods for confirmation/lag
        - Total minimum: 52 + 26 = 78 candles
        
        This is approach-specific validation, not in centralized requirements.py
        
        Args:
            df (pd.DataFrame): Input dataframe
            settings: IchimokuSettings instance
            
        Returns:
            Tuple[bool, str]: (is_valid, reason)
        """
        min_required = settings.senkou_b_period + settings.chikou_period
        
        if len(df) < min_required:
            return False, f"Insufficient data: {len(df)} candles < {min_required} required"
        
        # Check for required OHLCV columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return False, f"Missing required columns: {missing_cols}"
        
        return True, "Data validation passed"
    
    # ===== PRE-LOOP VALIDATION =====
    
    @staticmethod
    def validate_components(df: pd.DataFrame, settings: IchimokuSettings) -> Tuple[bool, str]:
        """
        Pre-loop validation: Check all 5 components are calculated and valid.
        
        Args:
            df (pd.DataFrame): Dataframe with calculated indicators
            settings: IchimokuSettings instance
            
        Returns:
            Tuple[bool, str]: (is_valid, reason)
        """
        required_columns = ['tenkan_sen', 'kijun_sen', 'senkou_a', 'senkou_b', 'chikou_span']
        
        # Check columns exist
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"Missing indicator columns: {missing_columns}"
        
        # Check data is available
        if df.empty:
            return False, "Dataframe is empty"
        
        # Check for critical index with enough data
        critical_idx = max(settings.senkou_b_period, settings.chikou_period)
        
        if len(df) < critical_idx:
            return False, f"Insufficient data: {len(df)} < {critical_idx}"
        
        # Check no NaN values in usable data sections
        # Note: senkou_b and senkou_a are calculated from rolling windows, then shifted forward.
        # This creates NaN values at BOTH ends:
        # - Start: first N rows (before calculation period)
        # - End: last 'shift' rows (after forward shift)
        # 
        # Valid range: from (start_nans) to (len - shift_nans)
        # For safety, we check from index where all components have valid data up to shift cutoff
        
        # senkou_a uses senkou_b calculation (52) + shift (26)
        # senkou_b uses 52 + shift (26)
        # tenkan/kijun use 9/26 with no shift
        # chikou uses 26 with backward shift (no forward NaNs)
        
        # Safe check range: from max period to (len - shift) to exclude both ends
        shift_offset = settings.senkou_shift_period
        usable_start = settings.senkou_b_period + shift_offset  # Both senkou components need this
        usable_end = len(df) - shift_offset
        
        # Ensure we have at least some usable data
        if usable_end <= usable_start:
            return False, f"Insufficient usable data: only {usable_end - usable_start} rows between {usable_start} and {usable_end}"
        
        for col in required_columns:
            nan_count = df[col].iloc[usable_start:usable_end].isna().sum()
            if nan_count > 0:
                return False, f"NaN values in {col}: {nan_count} found in usable data range [{usable_start}:{usable_end}]"
        
        return True, "All components valid"
    
    # ===== IN-LOOP VALIDATION =====
    
    @staticmethod
    def detect_signal(lookback_df: pd.DataFrame, i: int) -> Optional[Signal]:
        """
        Step 1: Detect Tenkan-sen crossing Kijun-sen.
        This represents a momentum shift from current price action.
        
        BUY Signal: Tenkan crosses ABOVE Kijun (uptrend momentum)
        SELL Signal: Tenkan crosses BELOW Kijun (downtrend momentum)
        
        Args:
            lookback_df (pd.DataFrame): Window dataframe with all indicators
            i (int): Current candle index in the window
            
        Returns:
            Optional[Signal]: Signal.BUY, Signal.SELL, or None
        """
        if i < 1:
            return None
        
        current_candle = lookback_df.iloc[i]
        prev_candle = lookback_df.iloc[i - 1]
        
        # Extract values
        current_tenkan = current_candle.get('tenkan_sen')
        current_kijun = current_candle.get('kijun_sen')
        prev_tenkan = prev_candle.get('tenkan_sen')
        prev_kijun = prev_candle.get('kijun_sen')
        
        # Check for NaN
        if pd.isna(current_tenkan) or pd.isna(current_kijun) or pd.isna(prev_tenkan) or pd.isna(prev_kijun):
            return None
        
        # BUY: Tenkan crosses ABOVE Kijun (uptrend momentum)
        if (prev_tenkan <= prev_kijun) and (current_tenkan > current_kijun):
            return Signal.BUY
        
        # SELL: Tenkan crosses BELOW Kijun (downtrend momentum)
        if (prev_tenkan >= prev_kijun) and (current_tenkan < current_kijun):
            return Signal.SELL
        
        return None
    
    @staticmethod
    def validate_trend(candle: pd.Series, signal: Signal) -> bool:
        """
        Step 2: Validate price position relative to Cloud (Kumo).
        Price must be on the correct side of the entire cloud for signal confirmation.
        
        BUY requirement: Price > Senkou A AND Price > Senkou B (above cloud)
        SELL requirement: Price < Senkou A AND Price < Senkou B (below cloud)
        
        The cloud represents a dynamic support/resistance zone. Price must be
        completely outside the cloud for a valid signal.
        
        Args:
            candle (pd.Series): Current candle with OHLCV and indicator data
            signal (Signal): Detected signal (BUY or SELL)
            
        Returns:
            bool: True if trend validation passes, False otherwise
        """
        price = candle.get('close')
        senkou_a = candle.get('senkou_a')
        senkou_b = candle.get('senkou_b')
        
        # Check for NaN values
        if pd.isna(price) or pd.isna(senkou_a) or pd.isna(senkou_b):
            return False
        
        if signal == Signal.BUY:
            # Price must be above BOTH cloud boundaries (above cloud)
            return (price > senkou_a) and (price > senkou_b)
        
        elif signal == Signal.SELL:
            # Price must be below BOTH cloud boundaries (below cloud)
            return (price < senkou_a) and (price < senkou_b)
        
        return False
    
    @staticmethod
    def validate_chikou(lookback_df: pd.DataFrame, i: int, signal: Signal, settings: IchimokuSettings) -> bool:
        """
        Step 3: Validate Chikou span confirmation.
        Chikou confirms trend strength by comparing current price to historical price.
        
        The Chikou is current close plotted 26 periods back.
        By comparing it to the historical price at that point, we confirm strength.
        
        BUY requirement: Chikou > price from 26 periods ago (shows current strength)
        SELL requirement: Chikou < price from 26 periods ago (shows current weakness)
        
        Args:
            lookback_df (pd.DataFrame): Window dataframe with all indicators
            i (int): Current candle index in the window
            signal (Signal): Detected signal (BUY or SELL)
            settings: IchimokuSettings instance
            
        Returns:
            bool: True if Chikou confirmation passes, False otherwise
        """
        current_candle = lookback_df.iloc[i]
        
        # Get Chikou value (current close shifted back in time)
        chikou = current_candle.get('chikou_span')
        
        if pd.isna(chikou):
            return False
        
        # Calculate index for historical price (26 periods back from current)
        historical_idx = i - settings.chikou_period
        
        if historical_idx < 0:
            return False
        
        historical_candle = lookback_df.iloc[historical_idx]
        historical_price = historical_candle.get('close')
        
        if pd.isna(historical_price):
            return False
        
        if signal == Signal.BUY:
            # Chikou must be above historical price (current strength > past price)
            return chikou > historical_price
        
        elif signal == Signal.SELL:
            # Chikou must be below historical price (current weakness < past price)
            return chikou < historical_price
        
        return False
