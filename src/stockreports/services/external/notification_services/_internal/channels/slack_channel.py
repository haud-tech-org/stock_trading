"""
SlackNotificationChannel - Slack notification channel via Incoming Webhook.

Delivers alerts as Block Kit attachment payloads to one or more Slack
channel webhook URLs. Each webhook URL is obtained from:
  Slack App → Your App → Incoming Webhooks → Add New Webhook to Workspace
"""

# --- Python Standard Library ---
import logging
import time
from typing import Optional

# --- Third-Party Libraries ---
import requests

# --- Project Imports ---
from .base_channel import BaseNotificationChannel
from src.stockreports.alert.model.models import AlertNotification
from src.stockreports.config import loader as config_loader

logger = logging.getLogger(__name__)


class SlackNotificationChannel(BaseNotificationChannel):
    def __init__(self, config: Optional[object] = None) -> None:
        self._config = config
        self._notification_config = config_loader.get_notification_settings()

    def _get_notification_settings(self) -> object:
        if self._notification_config is None:
            self._notification_config = config_loader.get_notification_settings()
        return self._notification_config

    # -------------------------------------------------------------------------
    # BaseNotificationChannel interface
    # -------------------------------------------------------------------------

    def _send(self, notification: AlertNotification) -> bool:
        """
        Send a Slack Block Kit notification for the given AlertNotification.
        """
        notification_settings = self._get_notification_settings()

        webhook_urls: list[str] = notification_settings.SLACK_WEBHOOK_URLS or []
        if not webhook_urls:
            logger.warning(
                "Slack channel is enabled but no SLACK_WEBHOOK_URLS configured. Skipping."
            )
            return False

        payload = self._build_payload(notification)
        return self._send_with_retry(webhook_urls, payload, max_retries=3, initial_delay=1.0)

    def validate_config(self) -> None:
        notification_settings = self._get_notification_settings()
        if not notification_settings.SLACK_WEBHOOK_URLS:
            raise ValueError(
                "SlackNotificationChannel: SLACK_WEBHOOK_URLS must be set."
            )

    # -------------------------------------------------------------------------
    # Message formatting — Slack Block Kit with attachment colour bar
    # -------------------------------------------------------------------------

    @staticmethod
    def _build_payload(notification: AlertNotification) -> dict:
        """
        Builds a Slack payload using the attachments + Block Kit format.

        Colour coding (left sidebar stripe):
          - BUY / REMINDER → #00B050  (green)
          - SELL / CLOSE   → #FF0000  (red)
          - Other          → #0078D4  (blue)

        Footer context block (appended via BaseNotificationChannel._get_run_context_footer()):
          - Environment  ← _secrets_loader.environment_type  (LOCAL / GCP / DOCKER …)
          - Run Mode     ← settings.DEBUG_REPLAY_START_TIME  (LIVE / REPLAY <timestamp>)

        Slack expects POST body: {"attachments": [...]}
        Success response: HTTP 200, body text "ok"
        """
        alert_price = (
            f"{notification.alert_price:.2f}"
            if notification.alert_price is not None else "N/A"
        )
        suggested_price = (
            f"{notification.suggested_price:.2f}"
            if notification.suggested_price is not None else "N/A"
        )
        alert_time_str = (
            notification.alert_time.strftime("%Y-%m-%d %H:%M:%S")
            if notification.alert_time is not None else "N/A"
        )
        profit_thresh = (
            f"{notification.suggested_profit_threshold:.2f}"
            if notification.suggested_profit_threshold is not None else "N/A"
        )

        signal_str = str(notification.signal).upper()
        if "BUY" in signal_str or "REMINDER" in signal_str:
            color = "#00B050"   # green
        elif "SELL" in signal_str or "CLOSE" in signal_str:
            color = "#FF0000"   # red
        else:
            color = "#0078D4"   # blue

        # --- run-context footer (common method from BaseNotificationChannel) ---
        ctx = SlackNotificationChannel._get_run_context_footer()
        footer_text = (
            f"*Env:* `{ctx.environment}`\u2003"
            f"*Run:* `{ctx.run_mode}`"
        )

        return {
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f"*{notification.signal}* — {notification.symbol}\n"
                                    f">Approach: `{notification.approach}`"
                                ),
                            },
                        },
                        {
                            "type": "section",
                            "fields": [
                                {"type": "mrkdwn", "text": f"*Signal Price*\n{alert_price}"},
                                {"type": "mrkdwn", "text": f"*Suggested Entry*\n{suggested_price}"},
                                {"type": "mrkdwn", "text": f"*Profit Threshold*\n{profit_thresh}"},
                                {"type": "mrkdwn", "text": f"*Time*\n{alert_time_str}"},
                            ],
                        },
                        {"type": "divider"},
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": footer_text,
                                }
                            ],
                        },
                    ],
                }
            ]
        }

    # -------------------------------------------------------------------------
    # Delivery with exponential-backoff retry
    # -------------------------------------------------------------------------

    def _send_with_retry(
        self,
        webhook_urls: list[str],
        payload: dict,
        max_retries: int = 3,
        initial_delay: float = 1.0,
    ) -> bool:
        """
        POSTs the payload to every webhook URL, retrying on transient failures.
        Slack returns HTTP 200 with body text "ok" on success.
        Returns True only if all URLs succeeded.
        """
        all_ok = True
        for url in webhook_urls:
            success = False
            delay = initial_delay
            for attempt in range(max_retries + 1):
                try:
                    response = requests.post(url, json=payload, timeout=10)
                    if response.status_code == 200 and response.text == "ok":
                        logger.info(
                            f"Slack notification sent successfully (attempt {attempt + 1})."
                        )
                        success = True
                        break
                    else:
                        logger.warning(
                            f"Slack webhook returned HTTP {response.status_code} "
                            f"(attempt {attempt + 1}): {response.text[:200]}"
                        )
                except requests.exceptions.RequestException as e:
                    logger.warning(
                        f"Slack webhook request failed (attempt {attempt + 1}): {e}"
                    )
                if attempt < max_retries:
                    logger.info(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    delay *= 2

            if not success:
                logger.error(
                    f"Slack notification failed after {max_retries} retries for URL: "
                    f"{url[:60]}..."
                )
                all_ok = False

        return all_ok
