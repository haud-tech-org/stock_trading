# src/stockreports/utils/ntfy_utils.py
import logging
import requests
from src.stockreports.config import loader
from src.stockreports.alert.model.models import AlertNotification

def send_ntfy_notification(notification: AlertNotification):
    """
    Sends a push notification using the ntfy.sh service.
    """
    notification_settings = loader.get_notification_settings()

    if not notification_settings.NTFY_TOPICS:
        logging.warning("Ntfy is enabled but no topics are configured. Skipping.")
        return

    profit_thresh = ""
    if notification.suggested_profit_threshold is not None:
        profit_thresh = f" | Profit Threshold: {notification.suggested_profit_threshold:.2f}"
    title = f"{notification.signal} - {notification.symbol} - Suggest: {notification.suggested_price:.2f}{profit_thresh} - at signal price {notification.alert_price:.2f} ({notification.approach})"
    message = f"Time: {notification.alert_time.strftime('%H:%M:%S')}"

    for topic in notification_settings.NTFY_TOPICS:
        try:
            requests.post(
                f"https://ntfy.sh/{topic}",
                data=message.encode('utf-8'),
                headers={"Title": title}
            )
            logging.info(f"Successfully sent ntfy push notification to topic '{topic}' for {notification.approach} signal.")
        except Exception as e:
            logging.error(f"Failed to send ntfy push notification to topic '{topic}': {e}")
