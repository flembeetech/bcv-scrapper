import os
import sqlite3
from typing import Optional, Dict

DB_PATH = os.environ.get("BCV_DB_PATH", "bcv_rates.sqlite3")

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rates (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                tasa REAL NOT NULL,
                fecha_valor TEXT NOT NULL,   -- YYYY-MM-DD
                source TEXT,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_scraped_at TEXT
            )
        """)
        try:
            conn.execute("ALTER TABLE rates ADD COLUMN last_scraped_at TEXT")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE rates ADD COLUMN source TEXT")
        except Exception:
            pass

        exists = conn.execute("SELECT COUNT(*) FROM rates").fetchone()[0]
        if exists == 0:
            conn.execute("""
                INSERT INTO rates (id, tasa, fecha_valor, source)
                VALUES (1, 0.0, '1970-01-01', 'init')
            """)

def get_rate() -> Optional[Dict]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM rates WHERE id = 1").fetchone()
        return dict(row) if row else None

def upsert_rate(tasa: float, fecha_valor: str, source: str = "live", mark_scraped: bool = True) -> None:
    with _connect() as conn:
        if mark_scraped:
            conn.execute("""
                INSERT INTO rates (id, tasa, fecha_valor, source, updated_at, last_scraped_at)
                VALUES (1, ?, ?, ?, datetime('now'), datetime('now'))
                ON CONFLICT(id) DO UPDATE SET
                    tasa = excluded.tasa,
                    fecha_valor = excluded.fecha_valor,
                    source = excluded.source,
                    updated_at = datetime('now'),
                    last_scraped_at = datetime('now')
            """, (tasa, fecha_valor, source))
        else:
            conn.execute("""
                INSERT INTO rates (id, tasa, fecha_valor, source, updated_at)
                VALUES (1, ?, ?, ?, datetime('now'))
                ON CONFLICT(id) DO UPDATE SET
                    tasa = excluded.tasa,
                    fecha_valor = excluded.fecha_valor,
                    source = excluded.source,
                    updated_at = datetime('now')
            """, (tasa, fecha_valor, source))
