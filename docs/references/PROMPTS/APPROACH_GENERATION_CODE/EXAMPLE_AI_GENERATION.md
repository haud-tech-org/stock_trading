# Example: Using AI_APPROACH_GENERATION_PROMPT for Automatic Code Generation

**Purpose**: Demonstrate how to use the AI prompt document to generate a complete approach  
**Status**: ✅ Example Ready  
**Date**: March 12, 2026

---

## 📋 Complete Example: Generating the "Volume Spike Confirmation" Approach

### Step 1: Fill in PART 1 of AI_APPROACH_GENERATION_PROMPT.md

```markdown
### 1.1 Basic Information

Approach Name: Volume Spike Confirmation
Short Code: VSC
Category: BIDIRECTIONAL
Description: Detects significant volume spikes with price confirmation. 
Identifies potential breakouts and reversals when volume exceeds historical 
averages with accompanying candle strength.

### 1.2 Trading Rules & Logic

RULE 1: Volume Spike Detection
- Input: Current candle volume vs historical average
- Condition: volume >= historical_avg_volume * 1.5
- Result: PASSES (go to next rule)

RULE 2: Candle Strength Confirmation  
- Input: Current candle body size and ratio
- Condition: body_ratio >= 0.6 AND body_size >= 30 pips
- Result: PASSES (go to next rule)

RULE 3: Price Direction from Volume
- Input: Current candle color (Green=UP, Red=DOWN)
- Condition: Color matches (no reversal in lookback window)
- Result: Signal = BUY (GREEN) or SELL (RED)

RULE 4: Cooldown Check
- Input: Time since last alert
- Condition: Current time >= (last_alert_time + cooldown_window)
- Result: Alert generated if passes

### 1.3 Configuration Thresholds

| Parameter | Default | Min | Max | Description |
|-----------|---------|-----|-----|-------------|
| LOOKBACK_WINDOW | 50 | 20 | 200 | Historical candles for volume baseline |
| VOLUME_SPIKE_MULTIPLIER | 1.5 | 1.0 | 3.0 | Volume threshold multiplier |
| MIN_BODY_RATIO | 0.6 | 0.4 | 1.0 | Minimum body ratio for confirmation |
| MIN_BODY_SIZE | 30 | 10 | 200 | Minimum body size in pips |
| COOLDOWN_WINDOW | 5 | 1 | 20 | Minimum candles between alerts |
| MAGNITUDE_THRESHOLD | 0.02 | 0.01 | 0.1 | Alert magnitude value |

### 1.4 Required Data

Data Input:
- Format: pandas DataFrame with OHLCV columns
- Columns Required: `open`, `high`, `low`, `close`, `volume`
- Index: datetime index with timestamps
- Frequency: 1 Hour
- Minimum History: 60 candles (50 lookback + buffer)
```

### Step 2: Prepare Request to AI

**Copy the entire AI_APPROACH_GENERATION_PROMPT.md document and provide this request:**

```
Please generate the complete end-to-end implementation of the Volume Spike 
Confirmation (VSC) approach following this specification document.

The specification above defines:
- Approach name: Volume Spike Confirmation
- Trading rules: 4 rules (volume, candle strength, direction, cooldown)
- Configuration: 6 parameters
- Data: 1-hour OHLCV data with 50-candle lookback

Generate all 5 files:
1. settings.py - Configuration loading
2. analyzer.py - Pure calculation methods
3. validator.py - Pure validation methods  
4. executor.py - Main orchestration logic
5. __init__.py - Module exports

Follow all architecture requirements, code quality standards, and validation 
checklist items from PART 2-5 of the document.
```

### Step 3: AI Generates Complete Code

**AI would produce 5 files ready to use:**

#### File 1: settings.py
```python
from src.stockreports.alert.common.constants import Approach
from src.stockreports.alert.common.base_settings import BaseSettings


class VolumeSpikeConfirmationSettings(BaseSettings):
    """Settings for the Volume Spike Confirmation approach.
    
    All configuration parameters are loaded from the centralized signal_settings.py
    using the get() method inherited from BaseSettings.
    """
    
    def __init__(self, symbol: str):
        """
        Initialize settings for a specific symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'AAPL', 'EURUSD')
        """
        super().__init__(symbol, Approach.VOLUME_SPIKE_CONFIRMATION)
        
        # Load approach-specific parameters from centralized configuration
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        self.volume_spike_multiplier = self.get("VOLUME_SPIKE_MULTIPLIER")
        self.min_body_ratio = self.get("MIN_BODY_RATIO")
        self.min_body_size = self.get("MIN_BODY_SIZE")
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
        self.magnitude_threshold = self.get("MAGNITUDE_THRESHOLD")
```

#### File 2: analyzer.py
```python
from src.stockreports.alert.analyzer import Analyzer


class VolumeSpikeConfirmationAnalyzer(Analyzer):
    """Analyzer for Volume Spike Confirmation approach.
    
    Inherits all calculation methods from base Analyzer class:
    - calculate_body_ratio() - Body ratio calculations
    - calculate_body_size() - Body size calculations
    - get_candle_color() - Candle color classification
    - get_max_volume_in_window() - Maximum volume in window
    - And 5 more base methods...
    
    This approach uses only inherited methods.
    """
    pass
```

#### File 3: validator.py
```python
import pandas as pd
from src.stockreports.alert.validator import Validator
from .analyzer import VolumeSpikeConfirmationAnalyzer


class VolumeSpikeConfirmationValidator(Validator):
    """Validator for Volume Spike Confirmation approach.
    
    Inherits all validation methods from base Validator class.
    Contains custom validation for volume spike detection.
    """
    
    @staticmethod
    def validate_volume_spike(
        current_volume: float,
        lookback_df: pd.DataFrame,
        spike_multiplier: float
    ) -> bool:
        """
        Validate if current volume represents a significant spike.
        
        Args:
            current_volume: Current candle volume
            lookback_df: DataFrame with lookback period
            spike_multiplier: Multiplier threshold (e.g., 1.5)
        
        Returns:
            bool: True if volume spike detected, False otherwise
        """
        avg_volume = lookback_df['volume'].mean()
        threshold = avg_volume * spike_multiplier
        return current_volume >= threshold
```

#### File 4: executor.py
```python
import pandas as pd
import logging
from typing import Optional

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, ValidationStatus, LogLevel, Trend
from src.stockreports.alert.model.models import AlertData, Validation
from varname import nameof
from src.stockreports.utils.log_factory import log

from .settings import VolumeSpikeConfirmationSettings
from .analyzer import VolumeSpikeConfirmationAnalyzer
from .validator import VolumeSpikeConfirmationValidator


class VolumeSpikeConfirmationExecutor(Executor):
    """Executor for the Volume Spike Confirmation approach.
    
    Detects significant volume spikes with candle strength confirmation
    to identify potential breakouts and reversals.
    
    CRITICAL: Implements _find_alerts(), does NOT override run()
    """
    
    def __init__(self, symbol: str):
        """
        Initialize executor with settings.
        
        Args:
            symbol: Trading symbol (e.g., 'AAPL')
        """
        self.settings = VolumeSpikeConfirmationSettings(symbol)
        self.analyzer = VolumeSpikeConfirmationAnalyzer()
        self.validator = VolumeSpikeConfirmationValidator()
        super().__init__(symbol, Approach.VOLUME_SPIKE_CONFIRMATION, self.settings)
        self.logger = logging.getLogger(__name__)
    
    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """
        Find alerts in the dataframe using Volume Spike Confirmation rules.
        
        Args:
            df: OHLCV data as pandas DataFrame
            new_candle_count: Number of new candles to process
        
        Returns:
            list[AlertData]: List of alerts found
        """
        # Validate minimum data
        if len(df) < self.settings.lookback_window:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time="N/A",
                step=0,
                message=f"Not enough data: requires {self.settings.lookback_window}, have {len(df)}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return self.alerts
        
        # Setup loop
        df_indexed, loop_start, loop_end = self.get_loop_setup(
            df=df,
            new_candle_count=new_candle_count,
            lookback_window_size=self.settings.lookback_window
        )
        
        # Main loop - process candles backward
        for i in range(loop_end, loop_start - 1, -1):
            # Extract window context
            self.set_window_context(i, df_indexed, self.settings.lookback_window)
            
            if self.lookback_window_df is None or self.last_candle is None:
                continue
            
            # Step 1: Volume Spike Detection
            self.next_step()
            
            if not self.validator.validate_volume_spike(
                current_volume=self.last_candle['volume'],
                lookback_df=self.lookback_window_df,
                spike_multiplier=self.settings.volume_spike_multiplier
            ):
                continue
            
            self.validations.append(Validation(
                name=nameof(self.settings.volume_spike_multiplier),
                step=self.current_step,
                validation=self.next_validation(),
                message="Volume spike detected",
                status=ValidationStatus.PASSED
            ))
            
            # Step 2: Candle Strength Confirmation
            self.next_step()
            
            body_ratio = self.analyzer.calculate_body_ratio(self.last_candle)
            body_size = self.analyzer.calculate_body_size(self.last_candle)
            
            if body_ratio < self.settings.min_body_ratio or body_size < self.settings.min_body_size:
                continue
            
            self.validations.append(Validation(
                name=nameof(self.settings.min_body_ratio),
                step=self.current_step,
                validation=self.next_validation(),
                message=f"Candle strength confirmed (ratio={body_ratio:.2f})",
                status=ValidationStatus.PASSED
            ))
            
            # Step 3: Determine Signal from Candle Color
            self.next_step()
            
            candle_color = self.analyzer.get_candle_color(self.last_candle)
            signal = Signal.BUY if candle_color.name == 'GREEN' else Signal.SELL
            
            self.validations.append(Validation(
                name="signal_direction",
                step=self.current_step,
                validation=self.next_validation(),
                message=f"Signal determined: {signal.name}",
                status=ValidationStatus.PASSED
            ))
            
            # Step 4: Cooldown Check
            self.next_step()
            
            if not self._step_cooldown_check(
                last_alert=None,
                signal=signal,
                cooldown_window=self.settings.cooldown_window
            ):
                continue
            
            # Create Alert
            self.next_step()
            
            details = self._add_details_for_alert(
                volume=float(self.last_candle['volume']),
                avg_volume=float(self.lookback_window_df['volume'].mean()),
                spike_ratio=float(self.last_candle['volume'] / self.lookback_window_df['volume'].mean()),
                body_ratio=body_ratio,
                candle_time=self.last_candle['time'].isoformat()
            )
            
            alert = self._create_alert_with_details(
                final_signal=signal,
                final_trend=Trend.UPTREND if signal == Signal.BUY else Trend.DOWNTREND,
                final_alert_candle=self.last_candle,
                final_magnitude=self.settings.magnitude_threshold,
                details=details
            )
            
            if alert is not None:
                self.alerts.append(alert)
                
                if not self.is_development_mode:
                    return self.alerts
        
        return self.alerts
```

#### File 5: __init__.py
```python
"""Volume Spike Confirmation Alert Approach Package.

Exports:
- VolumeSpikeConfirmationExecutor: Main executor for alert detection
- VolumeSpikeConfirmationAnalyzer: Pure calculation functions
- VolumeSpikeConfirmationValidator: Pure validation functions
- VolumeSpikeConfirmationSettings: Configuration settings
"""

from .executor import VolumeSpikeConfirmationExecutor
from .analyzer import VolumeSpikeConfirmationAnalyzer
from .validator import VolumeSpikeConfirmationValidator
from .settings import VolumeSpikeConfirmationSettings

__all__ = [
    'VolumeSpikeConfirmationExecutor',
    'VolumeSpikeConfirmationAnalyzer',
    'VolumeSpikeConfirmationValidator',
    'VolumeSpikeConfirmationSettings',
]
```

### Step 4: Validate Generated Code

**Verify all 19 validation checklist items pass:**

- ✅ Settings class inherits from `BaseSettings`
- ✅ Analyzer class inherits from `Analyzer`
- ✅ Validator class inherits from `Validator`
- ✅ Executor class inherits from `Executor`
- ✅ Executor implements `_find_alerts()` (not override `run()`)
- ✅ All type hints present
- ✅ All docstrings complete
- ✅ All Analyzer methods are `@staticmethod`
- ✅ All Validator methods are `@staticmethod`
- ✅ Uses base class utilities correctly
- ✅ Proper logging statements
- ✅ Development/deployment mode handling
- ✅ Alert creation with details
- ✅ Backward loop implementation
- ✅ Step and validation tracking
- ✅ Proper imports and constants
- ✅ All 5 files created
- ✅ `__init__.py` exports all classes
- ✅ Code meets quality standards

### Step 5: Copy to Repository

```bash
# Create approach directory
mkdir -p src/stockreports/alert/approach/VOLUME_SPIKE_CONFIRMATION

# Copy generated files
cp generated_settings.py src/stockreports/alert/approach/VOLUME_SPIKE_CONFIRMATION/settings.py
cp generated_analyzer.py src/stockreports/alert/approach/VOLUME_SPIKE_CONFIRMATION/analyzer.py
cp generated_validator.py src/stockreports/alert/approach/VOLUME_SPIKE_CONFIRMATION/validator.py
cp generated_executor.py src/stockreports/alert/approach/VOLUME_SPIKE_CONFIRMATION/executor.py
cp generated_init.py src/stockreports/alert/approach/VOLUME_SPIKE_CONFIRMATION/__init__.py

# Verify
ls -la src/stockreports/alert/approach/VOLUME_SPIKE_CONFIRMATION/
```

---

## ⏱️ Time Breakdown

| Step | Time | Action |
|------|------|--------|
| 1. Fill Specification | 10 min | Define rules, thresholds, data |
| 2. Prepare Request | 5 min | Copy document + write request |
| 3. AI Generation | ~1 min | AI generates 5 files |
| 4. Validation | 5 min | Check 19 validation items |
| 5. Copy & Deploy | 5 min | Move files to repository |
| **Total** | **~25 min** | Complete approach ready |

---

## 📋 What You Get

**5 Complete Production-Ready Files:**
- ✅ Type hints throughout
- ✅ Docstrings complete
- ✅ Pattern correct (Settings→Analyzer→Validator→Executor)
- ✅ All imports correct
- ✅ All base class utilities used properly
- ✅ Proper logging and error handling
- ✅ Development/deployment mode support
- ✅ Step tracking and validation
- ✅ Ready to test and deploy

---

## 🚀 Key Benefits

**Speed**: ~25 minutes from concept to production-ready code  
**Quality**: Guaranteed pattern adherence, type hints, docstrings  
**Consistency**: All approaches follow identical structure  
**Reliability**: AI follows strict validation checklist  
**Zero Manual Setup**: Complete folder structure and files  

---

**This example shows how to use the AI_APPROACH_GENERATION_PROMPT.md to generate a complete, production-ready trading approach in under 30 minutes!**

---

*Last Updated: March 12, 2026*
*Status: ✅ Example Complete*
