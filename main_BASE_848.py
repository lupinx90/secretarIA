import os
import subprocess
import time
from datetime import datetime, timedelta

import requests

from db import init_db, save_sleep_warning

# Inicializar tabla SQLite al arrancar
init_db()

# Environment settings
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
raw_targets = os.getenv("IP_TARGETS", "127.0.0.1")
IP_TARGETS = [ip.strip() for ip in raw_targets.split(",") if ip.strip()]
NAP_THRESHOLD = timedelta(minutes=30)  # Minimum off-line time for a nap
SLEEP_THRESHOLD = timedelta(hours=6)  # Minimum off-line time for full sleep


def get_check_interval():
    raw_value = os.getenv("CHECK_INTERVAL", "60")
    try:
        interval = int(raw_value)
    except ValueError:
        print(f"Invalid CHECK_INTERVAL value '{raw_value}'. Using default 60 seconds.")
        return 60
    return max(1, interval)


CHECK_INTERVAL = get_check_interval()


def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print(f"[LOG ONLY]: {message}")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)
    except requests.RequestException as err:
        print(f"Error sending Telegram notification: {err}")

def is_phone_online(ip_list: list[str]) -> bool:
    """Returns True if at least one candidate IP responds to a ping."""
    for ip in ip_list:
        # Sends 1 ping packet with a 1-second timeout
        res = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if res.returncode == 0:
            return True  # Device found on this interface
    return False  # Device not reachable on any defined IP


def format_duration(delta):
    total_seconds = max(delta.total_seconds(), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return int(hours), int(minutes)


def main():
    print(f"Tracking active state for stashed IPs: {', '.join(IP_TARGETS)}")

    first_seen = None
    last_seen = None
    last_reported_date = None

    while True:
        now = datetime.now()

        if is_phone_online(IP_TARGETS):
            if first_seen is None:
                
                first_seen = now
                if last_seen is None:
                    last_seen = now

                duration = first_seen - last_seen
                hours, minutes = format_duration(duration)

                if duration < NAP_THRESHOLD:
                    send_telegram(f"🤖 Tracker inicializado.")
                elif duration <= SLEEP_THRESHOLD:
                    send_telegram(" ☀️ Espero que haya sido una buena siesta!")
                    send_telegram(f"⏱️ Has descansado: {hours}h {minutes}m")
                else:
                    send_telegram(f"☀️ A los buenos días! Despierto a las {now.strftime('%H:%M')}\n")
                    send_telegram(" 🌙 Espero que hayas pasado una buena noche!")
                    send_telegram(f"⏱️ Has descansado: {hours}h {minutes}m")
                    short_dream, hours_slept = save_sleep_warning(last_seen, first_seen)
                    if short_dream:
                        message = (
                            f"⚠️ ¡Atención! Has dormido solo {hours_slept}h. "
                            "Se ha guardado el registro."
                        )
                        send_telegram(message)

            last_seen = now

        elif first_seen is not None:
            if now - last_seen > NAP_THRESHOLD:
                send_telegram(f"Desconectado a las {now.strftime('%H:%M')}.")

                if last_reported_date != now.date():
                    if last_seen is not None:
                        duration = last_seen - first_seen
                        hours, minutes = format_duration(duration)
                        report = (
                            f"📊 **Daily Sleep/Awake Report**\n\n"
                            f"☀️ First Active (Wi-Fi ON): {first_seen.strftime('%H:%M')}\n"
                            f"🌙 Last Active (Wi-Fi OFF): {last_seen.strftime('%H:%M')}\n"
                            f"⏱️ Tiempo despierto: {hours}h {minutes}m"
                        )
                        send_telegram(report)

                    last_reported_date = now.date()

                first_seen = None

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
