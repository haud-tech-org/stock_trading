# Minimal Flask web entrypoint that starts your alert manager in a background thread.
# Place this file at src/stockreports/web.py

from threading import Thread
import os
import time
from flask import Flask, jsonify

# Import the manager (adjust path if needed)
from .alert.symbol_alert_manager import SymbolAlertManager

app = Flask(__name__)
manager_thread = None

def start_manager_background():
    """
    Start the existing SymbolAlertManager in background mode.
    We call run_alert_generation which itself will run the deployment loop if MODE == "DEPLOYMENT".
    """
    try:
        manager = SymbolAlertManager()
        # Run only alert generation in background; this will run an infinite loop in deployment mode.
        manager.run_alert_generation()
    except Exception as e:
        app.logger.exception("Background manager failed: %s", e)

@app.route("/health")
def health():
    # Simple health endpoint for probe checks
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    # For local testing only: bind to PORT env var if set
    port = int(os.environ.get("PORT", 8080))
    # Start background manager also for local runs
    t = Thread(target=start_manager_background, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=port)
else:
    # When running with Gunicorn, start the background thread here.
    manager_thread = Thread(target=start_manager_background, daemon=True)
    manager_thread.start()