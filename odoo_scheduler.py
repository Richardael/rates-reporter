#!/usr/bin/env python3
"""Scheduler que ejecuta odoo_sync.py en las horas de ODOO_SYNC_TIMES (hora Venezuela)."""

import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

import pytz
from dotenv import load_dotenv

from scheduler import start_health_server

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("odoo_scheduler")

TIMEZONE = os.environ.get("TIMEZONE", "America/Caracas")
SYNC_TIMES = [t.strip() for t in os.environ.get("ODOO_SYNC_TIMES", "09:00,17:00").split(",") if t.strip()]
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "30"))
HEALTH_PORT = int(os.environ.get("HEALTH_PORT", "8080"))
RUN_ON_STARTUP = os.environ.get("RUN_ON_STARTUP", "false").lower() == "true"


def run_sync() -> bool:
    logger.info("Ejecutando odoo_sync...")
    result = subprocess.run([sys.executable, "/app/odoo_sync.py"], capture_output=True, text=True)
    for stream in (result.stdout, result.stderr):
        for line in stream.strip().split("\n"):
            if line:
                logger.info(f"[odoo_sync] {line}")
    logger.info(f"odoo_sync finalizo con exit code {result.returncode}")
    return result.returncode == 0


def main() -> None:
    tz = pytz.timezone(TIMEZONE)
    logger.info(f"Scheduler Odoo iniciado. Horas: {', '.join(SYNC_TIMES)} ({TIMEZONE})")

    threading.Thread(target=start_health_server, args=(HEALTH_PORT,), daemon=True).start()

    if RUN_ON_STARTUP:
        logger.info("RUN_ON_STARTUP=true — ejecutando sincronizacion de arranque...")
        time.sleep(3)
        run_sync()

    done = set()
    while True:
        now = datetime.now(tz)
        slot = now.strftime("%H:%M")
        key = f"{now.date()} {slot}"
        if slot in SYNC_TIMES and key not in done:
            logger.info(f"Disparando sincronizacion programada — {now.strftime('%d/%m/%Y %H:%M')}")
            run_sync()
            done = {k for k in done if k.startswith(str(now.date()))} | {key}
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
