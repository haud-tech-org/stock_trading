import logging
from typing import Optional
from src.stockreports.alert.common.constants import LogLevel, ValidationStatus

def log(
    logger: logging.Logger,
    name: str,
    step: int,
    message: str,
    log_level: LogLevel,
    status: Optional[ValidationStatus] = None,
    alert_time: Optional[str] = None,
    execution_symbol: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    validation: Optional[int] = None,
):
    """
    Generates and writes a standardized log message.
    """
    log_items = []
    if execution_symbol:
        log_items.append(f"[Symbol: {execution_symbol}]")
    
    log_items.append(f"[{name}]")
    if alert_time:
        log_items.append(f"[{alert_time}]")

    if start_time and end_time:
        log_items.append(f"[Window: {start_time} to {end_time}]")

    if status:
        log_items.append(f"[Status: {status}]")

    if validation:
        log_items.append(f"[Validation: {validation}]")

    if step:
        log_items.append(f"[Step: {step}]")

    log_items.append(f"- {message}")

    log_message = " ".join(log_items)

    if log_level == LogLevel.DEBUG:
        logger.debug(log_message)
    elif log_level == LogLevel.INFO:
        logger.info(log_message)
    elif log_level == LogLevel.WARNING:
        logger.warning(log_message)
    elif log_level == LogLevel.ERROR:
        logger.error(log_message)
    elif log_level == LogLevel.CRITICAL:
        logger.critical(log_message)
