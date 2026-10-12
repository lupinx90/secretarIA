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
NAP_THRESHOLD = timedelta(minutes=30)
SLEEP_THRESHOLD = timedelta(hours=4)

TELEGRAM_SESSION = requests.Session()


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
        safe_message = message.encode("ascii", errors="replace").decode("ascii")
        print(f"[LOG ONLY]: {safe_message}")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        TELEGRAM_SESSION.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)
    except requests.RequestException as err:
        print(f"Error sending Telegram notification: {err}")


def ping_ip(ip: str) -> bool:
    if os.name == "nt":
        command = ["ping", "-n", "1", "-w", "1000", ip]
    else:
        command = ["ping", "-c", "1", "-W", "1", ip]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def is_phone_online(ip_list: list[str]) -> bool:
    """Returns True if at least one candidate IP responds to a ping."""
    return any(ping_ip(ip) for ip in ip_list)


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
    was_online = False

    while True:
        now = datetime.now()
        online = is_phone_online(IP_TARGETS)

        if online:
            if first_seen is None:
                first_seen = now

            if not was_online:
                if now - first_seen <= timedelta(minutes=5):
                    send_telegram("🤖 Tracker inicializado.")
                if last_seen is not None:
                    offline_duration = now - last_seen
                    hours, minutes = format_duration(offline_duration)

                    if offline_duration <= NAP_THRESHOLD:
                        send_telegram("🤖 Microcorte detectado.")
                    elif offline_duration <= SLEEP_THRESHOLD:
                        send_telegram(" ☀️ Espero que haya sido una buena siesta!")
                        send_telegram(f"⏱️ Has descansado: {hours}h {minutes}m")
                    else:
                        send_telegram(f"☀️ A los buenos días! Despierto a las {now.strftime('%H:%M')}\n")
                        send_telegram(" 🌙 Espero que hayas pasado una buena noche!")
                        send_telegram(f"⏱️ Has descansado: {hours}h {minutes}m")
                        short_dream, hours_slept = save_sleep_warning(first_seen, last_seen)
                        if short_dream:
                            message = (
                                f"⚠️ ¡Atención! Has dormido solo {hours_slept}h. "
                                "Se ha guardado el registro."
                            )
                            send_telegram(message)
                was_online = True

            last_seen = now
            continue

        if was_online and last_seen is not None:
            duration = now - last_seen

            if duration > NAP_THRESHOLD:
                send_telegram(f"Desconectado a las {last_seen.strftime('%H:%M')}.")
            if duration > SLEEP_THRESHOLD and last_reported_date != now.date() and first_seen is not None:
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

            was_online = False

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
