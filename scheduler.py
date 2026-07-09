#!/usr/bin/env python3
"""Scheduler que ejecuta el reporter diario a las 9:00 AM Venezuela."""

import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytz
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scheduler")

CONFIG_PATH = os.environ.get("CONFIG_PATH", "/app/config.yaml")
TIMEZONE = os.environ.get("TIMEZONE", "America/Caracas")
TARGET_HOUR = int(os.environ.get("TARGET_HOUR", "9"))
TARGET_MINUTE = int(os.environ.get("TARGET_MINUTE", "0"))
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "30"))
HEALTH_PORT = int(os.environ.get("HEALTH_PORT", "8080"))


def should_run(hour: int, minute: int) -> bool:
    return hour == TARGET_HOUR and minute == TARGET_MINUTE


def run_reporter() -> bool:
    logger.info("Ejecutando reporter...")
    result = subprocess.run(
        [sys.executable, "/app/rate_reporter.py", "--config", CONFIG_PATH],
        capture_output=True,
        text=True,
    )
    if result.stdout:
        for line in result.stdout.strip().split("\n"):
            logger.info(f"[reporter] {line}")
    if result.stderr:
        for line in result.stderr.strip().split("\n"):
            if line:
                logger.warning(f"[reporter] {line}")
    success = result.returncode == 0
    logger.info(f"Reporter finalizo con exit code {result.returncode}")
    return success


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def start_health_server(port: int) -> None:
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health check escuchando en puerto {port}")
    server.serve_forever()


def main() -> None:
    tz = pytz.timezone(TIMEZONE)
    logger.info(f"Scheduler iniciado. Se ejecutara a las {TARGET_HOUR:02d}:{TARGET_MINUTE:02d} ({TIMEZONE})")
    logger.info(f"Revisando cada {CHECK_INTERVAL} segundos...")

    health_thread = threading.Thread(target=start_health_server, args=(HEALTH_PORT,), daemon=True)
    health_thread.start()

    last_run_date = None

    while True:
        now = datetime.now(tz)
        today = now.date()

        if should_run(now.hour, now.minute) and last_run_date != today:
            logger.info(f"Disparando ejecucion programada — {now.strftime('%d/%m/%Y %H:%M')}")
            run_reporter()
            last_run_date = today

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
