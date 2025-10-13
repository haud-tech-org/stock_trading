# src/stockreports/alert/price_movement_alerter.py

import pandas as pd
from ..config.loader import get_price_alert_settings

class PriceMovementAlerter:
    """
    A stateless calculator to detect price movements against predefined levels.
    """

    def __init__(self, symbol: str, triggered_levels_today: set):
        """
        Initializes the PriceMovementAlerter.

        Args:
            symbol (str): The stock symbol to check.
            triggered_levels_today (set): A set of price levels that have already
                                          triggered an alert today for this symbol.
        """
        self.symbol = symbol
        self.triggered_levels_today = triggered_levels_today
        self.settings = get_price_alert_settings()
        self.config = self.settings.PRICE_ALERTS.get(self.symbol, {})
        self.allow_repeated_alerts = self.settings.ALLOW_REPEATED_LEVEL_ALERTS

    def execute(self, master_df: pd.DataFrame) -> list:
        """
        Checks for price level crossings based on the latest data.

        Args:
            master_df (pd.DataFrame): All data received so far today.

        Returns:
            list: A list of strings, where each string is a notification message
                  for a triggered alert.
        """
        if not self.config or master_df.empty:
            return []

        if len(master_df) < 2:
            return []

        # Use the last two entries of the master_df to represent the most recent price movement
        last_two_ticks = master_df.iloc[-2:]
        prev_price = last_two_ticks.iloc[0]['close']
        curr_price = last_two_ticks.iloc[-1]['close']

        triggered_alerts = []
        newly_triggered_levels = set()

        # 1. Check for fixed level alerts
        fixed_levels = self.config.get("fixed_levels")
        if fixed_levels:
            for level in fixed_levels:
                if self._has_straddled(prev_price, curr_price, level):
                    if self.allow_repeated_alerts or level not in self.triggered_levels_today:
                        direction = "crossed above" if curr_price > prev_price else "crossed below"
                        message = (f"'{self.symbol}' {direction} fixed price level of {level:.2f}. "
                                   f"Current price: {curr_price:.2f}.")
                        triggered_alerts.append(message)
                        newly_triggered_levels.add(level)

        # 2. Check for absolute interval alerts
        interval = self.config.get("absolute_interval")
        ref_price = self.config.get("reference_price")

        if interval and ref_price is not None:
            prev_level = self._get_interval_level(prev_price, ref_price, interval)
            curr_level = self._get_interval_level(curr_price, ref_price, interval)

            if curr_level != prev_level:
                # Determine the actual boundary that was crossed
                crossed_boundary = max(prev_level, curr_level) * interval + ref_price if curr_price > prev_price else min(prev_level, curr_level) * interval + ref_price
                
                if self.allow_repeated_alerts or crossed_boundary not in self.triggered_levels_today:
                    direction = "crossed above" if curr_price > prev_price else "crossed below"
                    message = (f"'{self.symbol}' {direction} an interval price level. "
                               f"New level boundary: {crossed_boundary:.2f}. Current price: {curr_price:.2f}.")
                    triggered_alerts.append(message)
                    newly_triggered_levels.add(crossed_boundary)

        # Update the master set of triggered levels for the day
        self.triggered_levels_today.update(newly_triggered_levels)

        return triggered_alerts

    def _has_straddled(self, price1: float, price2: float, level: float) -> bool:
        """
        Checks if the price crossed a specific level between two points.
        """
        return (price1 < level <= price2) or (price1 > level >= price2)

    def _get_interval_level(self, price: float, ref_price: float, interval: float) -> int:
        """
        Calculates which interval band a price belongs to.
        """
        return int((price - ref_price) / interval)
