import sqlite3
from datetime import datetime

DB_NAME = "bad_mojo.db"


def init_db():
    """Crea la tabla de registros si no existe."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS hazy_dreams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            starting_hour TEXT NOT NULL,
            ending_hour TEXT NOT NULL,
            hours_span REAL NOT NULL,
            mins_span INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def save_sleep_warning(last_seen: datetime, first_seen: datetime):
    """Guarda en la BD solo si el tiempo dormido es menor a 8 horas."""
    slept = first_seen - last_seen
    total_seconds = slept.total_seconds()

    # 8 horas = 28800 segundos
    if total_seconds < 28800:
        hours_span = round(total_seconds / 3600, 2)
        mins_span = int(total_seconds // 60)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO hazy_dreams (date, starting_hour, ending_hour, hours_span, mins_span)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                first_seen.strftime("%Y-%m-%d"),
                last_seen.strftime("%Y-%m-%d %H:%M:%S"),
                first_seen.strftime("%Y-%m-%d %H:%M:%S"),
                hours_span,
                mins_span,
            ),
        )
        conn.commit()
        conn.close()
        print(
            f"⚠️ Alerta: Duermes demasiado poco (si persiste, pide ayuda) {hours_span}h (< 8h). Registro guardado en BD.",
            flush=True,
        )
        return True, hours_span

    sleep_hours = round(total_seconds / 3600, 2)
    print(f"✅ Has dormido {sleep_hours}h (>= 8h). No requiere registro.", flush=True)
    return False, sleep_hours
