from src.stockreports.config import loader
from src.stockreports.alert.common.constants_charts import PlotConfigs, ChartDefaults, PlotKeys, Chart, PlotConfigKeys


class PlotConfigurations:
    """
    A class to generate plot configurations for the visibility chart.
    It encapsulates the logic for creating different plot types based on signal settings.
    """
    def __init__(self, signal_type='BUY'):
        """
        Initializes the PlotConfigurations class.

        Args:
            signal_type (str): The type of signal ('BUY' or 'SELL').
        """
        self.signal_type = signal_type
        self.signal_settings = loader.get_signal_settings()
        self.plot_keys = PlotConfigKeys

    def _create_plot_config(self, cfg):
        """Creates a generic plot configuration."""
        base_config = {
            self.plot_keys.TITLE: cfg.TITLE_VALUE,
            self.plot_keys.INDICATOR_COL: cfg.INDICATOR_COL_VALUE,
            self.plot_keys.Y_TITLE: cfg.Y_TITLE_VALUE,
            self.plot_keys.TRACES: [],
            self.plot_keys.CONFIRMATION_CHECK: None,
        }

        # Start with a clean if/elif structure
        if cfg.KEY in [PlotKeys.SHORT_MA, PlotKeys.LONG_MA, PlotKeys.PRIMARY_MA]:
            base_config[self.plot_keys.TYPE] = Chart.PRICE_INDICATOR
            base_config[self.plot_keys.TRACES].append({
                self.plot_keys.TYPE: Chart.CANDLESTICK,
                self.plot_keys.Y_COL: ['open', 'high', 'low', 'close'],
                self.plot_keys.NAME: cfg.PRICE_NAME_VALUE,
                self.plot_keys.INCREASING_LINE_COLOR: cfg.PRICE_INCREASING_COLOR,
                self.plot_keys.DECREASING_LINE_COLOR: cfg.PRICE_DECREASING_COLOR
            })
            base_config[self.plot_keys.TRACES].append({
                self.plot_keys.TYPE: Chart.SCATTER,
                self.plot_keys.Y_COL: cfg.INDICATOR_COL_VALUE,
                self.plot_keys.NAME: cfg.NAME_VALUE,
                self.plot_keys.MODE: PlotConfigKeys.MODES_LINES,
                self.plot_keys.LINE: {self.plot_keys.COLOR: cfg.COLOR_VALUE}
            })
            def check_ma(breakout_candle, price_at_breakout):
                indicator_val = breakout_candle[cfg.INDICATOR_COL_VALUE]
                is_confirmed = price_at_breakout > indicator_val if self.signal_type == 'BUY' else price_at_breakout < indicator_val
                return is_confirmed, price_at_breakout
            base_config[self.plot_keys.CONFIRMATION_CHECK] = check_ma
            base_config[self.plot_keys.ANNOTATION_YSHIFT] = 15

        elif cfg.KEY in [PlotKeys.RSI, PlotKeys.ADX]:
            base_config[self.plot_keys.TYPE] = Chart.INDICATOR_THRESHOLD
            if cfg.KEY == PlotKeys.RSI:
                threshold = self.signal_settings.RSI_BULLISH_THRESHOLD if self.signal_type == 'BUY' else self.signal_settings.RSI_BEARISH_THRESHOLD
                compare_op = self.plot_keys.COMPARE_GREATER if self.signal_type == 'BUY' else self.plot_keys.COMPARE_LESS
            else:  # ADX
                threshold = self.signal_settings.ADX_CONFIRMATION_THRESHOLD
                compare_op = self.plot_keys.COMPARE_GREATER

            def check_threshold(breakout_candle, price_at_breakout):
                indicator_val = breakout_candle[cfg.INDICATOR_COL_VALUE]
                is_confirmed = (indicator_val > threshold) if compare_op == 'greater' else (indicator_val < threshold)
                return is_confirmed, indicator_val
            base_config[self.plot_keys.CONFIRMATION_CHECK] = check_threshold

            base_config[self.plot_keys.TRACES].extend([
                {self.plot_keys.TYPE: Chart.SCATTER, self.plot_keys.Y_COL: cfg.INDICATOR_COL_VALUE, self.plot_keys.NAME: cfg.NAME_VALUE, self.plot_keys.MODE: PlotConfigKeys.MODES_LINES, self.plot_keys.LINE: {self.plot_keys.COLOR: cfg.COLOR_VALUE}},
                {self.plot_keys.TYPE: Chart.HLINE, self.plot_keys.LINE_DASH: self.plot_keys.DASH_STYLE_DASH, self.plot_keys.LINE_COLOR: ChartDefaults.COLOR_GREY}
            ])
            base_config.update({
                self.plot_keys.THRESHOLD: threshold,
                self.plot_keys.COMPARE: compare_op,
                self.plot_keys.ANNOTATION_YSHIFT: 10
            })

        elif cfg.KEY == PlotKeys.MACD:
            base_config[self.plot_keys.TYPE] = Chart.INDICATOR_CROSS
            def check_macd(breakout_candle, price_at_breakout):
                val1 = breakout_candle[cfg.INDICATOR_COL_VALUE]
                val2 = breakout_candle[cfg.CROSS_COL_VALUE]
                is_confirmed = val1 > val2 if self.signal_type == 'BUY' else val1 < val2
                return is_confirmed, val1
            base_config[self.plot_keys.CONFIRMATION_CHECK] = check_macd

            base_config[self.plot_keys.TRACES].extend([
                {self.plot_keys.TYPE: Chart.SCATTER, self.plot_keys.Y_COL: cfg.INDICATOR_COL_VALUE, self.plot_keys.NAME: cfg.NAME_VALUE, self.plot_keys.MODE: PlotConfigKeys.MODES_LINES, self.plot_keys.LINE: {self.plot_keys.COLOR: cfg.COLOR_VALUE}},
                {self.plot_keys.TYPE: Chart.SCATTER, self.plot_keys.Y_COL: cfg.CROSS_COL_VALUE, self.plot_keys.NAME: cfg.SIGNAL_NAME_VALUE, self.plot_keys.MODE: PlotConfigKeys.MODES_LINES, self.plot_keys.LINE: {self.plot_keys.COLOR: cfg.SIGNAL_COLOR_VALUE}}
            ])
            base_config.update({
                self.plot_keys.CROSS_COL: cfg.CROSS_COL_VALUE,
                self.plot_keys.ANNOTATION_YSHIFT: 10
            })

        return base_config

    def get_all_configs(self):
        """
        Assembles and returns a dictionary of all plot configurations.
        """
        return {
            PlotKeys.SHORT_MA: self._create_plot_config(PlotConfigs.SHORT_MA),
            PlotKeys.LONG_MA: self._create_plot_config(PlotConfigs.LONG_MA),
            PlotKeys.PRIMARY_MA: self._create_plot_config(PlotConfigs.PRIMARY_MA),
            PlotKeys.RSI: self._create_plot_config(PlotConfigs.RSI),
            PlotKeys.MACD: self._create_plot_config(PlotConfigs.MACD),
            PlotKeys.ADX: self._create_plot_config(PlotConfigs.ADX),
        }
