class ChartDefaults:
    COLOR_GREEN = "green"
    COLOR_RED = "red"
    COLOR_ORANGE = "orange"
    COLOR_PURPLE = "purple"
    COLOR_BROWN = "brown"
    COLOR_CYAN = "cyan"
    COLOR_BLUE = "blue"
    COLOR_MAGENTA = "magenta"
    COLOR_GREY = "grey"
    ANNOTATION_FONT_FAMILY = "Arial"
    ANNOTATION_BG_COLOR = "rgba(255,255,255,0.7)"
    TEMPLATE = "plotly_white"
    CHECK_TEXT_PREFIX = "Check: "
    STATUS_PASSED = "PASSED"
    STATUS_FAILED = "FAILED"
    VLINE_DASH = "dash"


class Chart:
    # Plot Types
    PRICE_INDICATOR = "price_indicator"
    INDICATOR_THRESHOLD = "indicator_threshold"
    INDICATOR_CROSS = "indicator_cross"

    # Trace Types
    CANDLESTICK = "candlestick"
    SCATTER = "scatter"
    HLINE = "hline"


class PlotConfigKeys:
    TITLE = "title"
    TYPE = "type"
    INDICATOR_COL = "indicator_col"
    Y_TITLE = "y_title"
    TRACES = "traces"
    CONFIRMATION_CHECK = "confirmation_check"
    Y_COL = "y_col"
    NAME = "name"
    MODE = "mode"
    LINE = "line"
    COLOR = "color"
    INCREASING_LINE_COLOR = "increasing_line_color"
    DECREASING_LINE_COLOR = "decreasing_line_color"
    WIDTH = "width"
    CROSS_COL = "cross_col"
    THRESHOLD = "threshold"
    COMPARE = "compare"
    LINE_DASH = "line_dash"
    LINE_COLOR = "line_color"
    MODES_LINES = "lines"
    DASH_STYLE_DASH = "dash"
    COMPARE_GREATER = "greater"
    COMPARE_LESS = "less"
    ANNOTATION_YSHIFT = "annotation_yshift"
    HAS_PRICE_TRACE = "has_price_trace"


class PlotConfigs:
    """
    Namespace for plot configuration constants.
    """
    # Common Values
    MODES_LINES = 'lines'
    DASH_STYLE_DASH = 'dash'

    class Base:
        TITLE = PlotConfigKeys.TITLE
        TYPE = PlotConfigKeys.TYPE
        INDICATOR_COL = PlotConfigKeys.INDICATOR_COL
        Y_TITLE = PlotConfigKeys.Y_TITLE
        TRACES = PlotConfigKeys.TRACES
        CONFIRMATION_CHECK = PlotConfigKeys.CONFIRMATION_CHECK
        Y_COL = PlotConfigKeys.Y_COL
        NAME = PlotConfigKeys.NAME
        MODE = PlotConfigKeys.MODE
        LINE = PlotConfigKeys.LINE
        COLOR = PlotConfigKeys.COLOR
        INCREASING_LINE_COLOR = PlotConfigKeys.INCREASING_LINE_COLOR
        DECREASING_LINE_COLOR = PlotConfigKeys.DECREASING_LINE_COLOR
        WIDTH = PlotConfigKeys.WIDTH
        CROSS_COL = PlotConfigKeys.CROSS_COL
        THRESHOLD = PlotConfigKeys.THRESHOLD
        COMPARE = PlotConfigKeys.COMPARE
        LINE_DASH = PlotConfigKeys.LINE_DASH
        LINE_COLOR = PlotConfigKeys.LINE_COLOR
        MODES_LINES = PlotConfigKeys.MODES_LINES
        DASH_STYLE_DASH = PlotConfigKeys.DASH_STYLE_DASH
        COMPARE_GREATER = PlotConfigKeys.COMPARE_GREATER
        COMPARE_LESS = PlotConfigKeys.COMPARE_LESS
        ANNOTATION_YSHIFT = PlotConfigKeys.ANNOTATION_YSHIFT
        HAS_PRICE_TRACE = PlotConfigKeys.HAS_PRICE_TRACE

        # Common values
        PRICE_NAME_VALUE = "Price"
        PRICE_INCREASING_COLOR = ChartDefaults.COLOR_GREEN
        PRICE_DECREASING_COLOR = ChartDefaults.COLOR_RED
        PRICE_LINE_COLOR = ChartDefaults.COLOR_BLUE
        PRICE_LINE_WIDTH = 0.5

    class SHORT_MA(Base):
        KEY = "short_ma"
        TITLE_VALUE = "Short-Term MA Confirmation"
        INDICATOR_COL_VALUE = "ma_short"
        Y_TITLE_VALUE = "Price"
        NAME_VALUE = "Short MA"
        COLOR_VALUE = ChartDefaults.COLOR_ORANGE
        HAS_PRICE_TRACE_VALUE = True

    class LONG_MA(Base):
        KEY = "long_ma"
        TITLE_VALUE = "Long-Term MA Confirmation"
        INDICATOR_COL_VALUE = "ma_long"
        Y_TITLE_VALUE = "Price"
        NAME_VALUE = "Long MA"
        COLOR_VALUE = ChartDefaults.COLOR_PURPLE
        HAS_PRICE_TRACE_VALUE = True

    class PRIMARY_MA(Base):
        KEY = "primary_ma"
        TITLE_VALUE = "Primary Trend MA Filter"
        INDICATOR_COL_VALUE = "ma_long_term"
        Y_TITLE_VALUE = "Price"
        NAME_VALUE = "Primary MA"
        COLOR_VALUE = ChartDefaults.COLOR_BROWN
        HAS_PRICE_TRACE_VALUE = True

    class RSI(Base):
        KEY = "rsi"
        TITLE_VALUE = "RSI Confirmation"
        INDICATOR_COL_VALUE = "rsi"
        Y_TITLE_VALUE = "RSI"
        NAME_VALUE = "RSI"
        COLOR_VALUE = ChartDefaults.COLOR_CYAN
        HAS_PRICE_TRACE_VALUE = False

    class MACD(Base):
        KEY = "macd"
        TITLE_VALUE = "MACD Confirmation"
        INDICATOR_COL_VALUE = "macd"
        CROSS_COL_VALUE = "macdsignal"
        Y_TITLE_VALUE = "MACD"
        NAME_VALUE = "MACD Line"
        SIGNAL_NAME_VALUE = "Signal Line"
        COLOR_VALUE = ChartDefaults.COLOR_BLUE
        SIGNAL_COLOR_VALUE = ChartDefaults.COLOR_RED
        HAS_PRICE_TRACE_VALUE = False

    class ADX(Base):
        KEY = "adx"
        TITLE_VALUE = "ADX Trend Strength"
        INDICATOR_COL_VALUE = "adx"
        Y_TITLE_VALUE = "ADX"
        NAME_VALUE = "ADX"
        COLOR_VALUE = ChartDefaults.COLOR_MAGENTA
        HAS_PRICE_TRACE_VALUE = False


class PlotKeys:
    SHORT_MA = PlotConfigs.SHORT_MA.KEY
    LONG_MA = PlotConfigs.LONG_MA.KEY
    PRIMARY_MA = PlotConfigs.PRIMARY_MA.KEY
    RSI = PlotConfigs.RSI.KEY
    MACD = PlotConfigs.MACD.KEY
    ADX = PlotConfigs.ADX.KEY
