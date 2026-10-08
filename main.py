import os
import time
import subprocess
import requests
from datetime import datetime, timedelta
from db import init_db, save_sleep_warning

# Inicializar tabla SQLite al arrancar
init_db()

# Environment settings
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
MOBILE_IP = os.getenv("MOBILE_IP", "")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", ""))

def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print(f"[LOG ONLY]: {message}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)
    except Exception as err:
        print(f"Error sending Telegram notification: {err}")

def is_device_online(ip):
    # Single ICMP ping packet with 1-second timeout
    cmd = ["ping", "-c", "1", "-W", "1", ip]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0

def main():
    print(f"Tracking active state for Mobile IP: {MOBILE_IP}")
    #send_telegram(f"🤖 Tracker inicializado. Target IP: {MOBILE_IP}")

    first_seen = None
    last_seen = None
    last_reported_date = None

    while True:
        now = datetime.now()

        # Send daily consolidation report at 04:00 AM
        if now.hour == 4 and last_reported_date != now.date():
            if first_seen and last_seen:
                duration = last_seen - first_seen
                hours, remainder = divmod(duration.total_seconds(), 3600)
                minutes = remainder // 60
                
                report = (
                    f"📊 **Daily Sleep/Awake Report**\n\n"
                    f"☀️ First Active (Wi-Fi ON): {first_seen.strftime('%H:%M')}\n"
                    f"🌙 Last Active (Wi-Fi OFF): {last_seen.strftime('%H:%M')}\n"
                    f"⏱️ Tiempo despierto: {int(hours)}h {int(minutes)}m"
                )
                send_telegram(report)
            
            # Reset counters for the new cycle
            first_seen = None
            last_reported_date = now.date()

        # Check phone connectivity
        if is_device_online(MOBILE_IP):
            short_dream = None
            hours_slept = None
            if first_seen is None:
                send_telegram(f"☀️ A los buenos días! Despierto a las {now.strftime('%H:%M')}.\n")
                first_seen = now
            elif last_seen and first_seen > last_seen + timedelta(hours=2):
                duration = first_seen - last_seen
                hours, remainder = divmod(duration.total_seconds(), 3600)
                minutes = remainder // 60
                send_telegram(f"⏱️ Has dormido: {int(hours)}h {int(minutes)}m")
                # Evaluar y registrar en SQLite si fue menos de 8 horas
                short_dream, hours_slept = save_sleep_warning(last_seen, first_seen)
                    
            if short_dream:
                # Puedes personalizar el mensaje de Telegram
                mensaje = f"⚠️ ¡Atención! Has dormido solo {hours_slept}h. Se ha guardado el registro."
                send_telegram(mensaje)
            last_seen = now
        elif now.hour >= 22 or now.hour < 4: # A partir de las 10PM o antes de las 4AM desconectado se dan las buenas noches
            send_telegram(f"🌙 Felices sueños! Desconectado a las {now.strftime('%H:%M')}.")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()