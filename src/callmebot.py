import logging
import time
from typing import Optional
from urllib.parse import quote

import requests

from src.config import CallMeBotConfig

CALLMEBOT_API = "https://api.callmebot.com/whatsapp.php"
REQUEST_TIMEOUT = 15
DELAY_BETWEEN_MESSAGES = 2.0


def _send_to_phone(
    phone: str,
    text: str,
    apikey: str,
    label: str,
    logger: Optional[logging.Logger] = None,
) -> bool:
    url = f"{CALLMEBOT_API}?phone={phone}&text={quote(text)}&apikey={apikey}"

    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        body = resp.text.strip().lower()
        if "ok" in body or "queued" in body or "sent" in body:
            if logger:
                logger.info(f"CallMeBot: enviado a {label}")
            return True

        if logger:
            logger.error(f"CallMeBot: respuesta inesperada para {label} — {resp.text[:200]}")
        return False

    except requests.RequestException as e:
        if logger:
            logger.error(f"CallMeBot: error al enviar a {label} — {e}")
        return False


def send_whatsapp_message(
    text: str,
    config: CallMeBotConfig,
    logger: Optional[logging.Logger] = None,
) -> bool:
    if not config.enabled:
        if logger:
            logger.info("CallMeBot desactivado en configuracion")
        return True

    recipients = config.get_recipients()
    if not recipients:
        if logger:
            logger.warning("CallMeBot: no hay destinatarios configurados")
        return False

    success_count = 0
    for i, recipient in enumerate(recipients):
        if i > 0:
            time.sleep(DELAY_BETWEEN_MESSAGES)

        apikey = recipient.get_apikey()
        if not apikey:
            if logger:
                logger.warning(f"CallMeBot: sin apikey para {recipient.label}")
            continue

        if _send_to_phone(recipient.phone, text, apikey, recipient.label, logger):
            success_count += 1

    if logger:
        logger.info(f"CallMeBot: {success_count}/{len(recipients)} mensajes enviados")

    return success_count > 0
