import os
import csv
import sqlite3
from datetime import datetime
from typing import Optional, Dict, List

def _get_db_path() -> str:
    return os.environ.get("BCV_DB_PATH", "bcv_rates.sqlite3")

def _connect():
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db() -> None:
    db_path = _get_db_path()
    dirname = os.path.dirname(db_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
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
        try:
            conn.execute("ALTER TABLE rates ADD COLUMN tasa_eur REAL")
        except Exception:
            pass

        # Tabla de histórico de tasas diarias
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rates_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_valor TEXT NOT NULL UNIQUE,   -- YYYY-MM-DD (Fecha Oficial)
                tasa_bcv REAL NOT NULL,             -- Dólar BCV
                tasa_eur_bcv REAL NOT NULL,         -- Euro BCV
                source TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rates_history_fecha_valor ON rates_history (fecha_valor);")

        # Migración automática si existen las columnas anteriores tasa / tasa_eur
        try:
            columns = [c[1] for c in conn.execute("PRAGMA table_info(rates_history)").fetchall()]
            if "tasa" in columns and "tasa_bcv" not in columns:
                conn.execute("ALTER TABLE rates_history RENAME COLUMN tasa TO tasa_bcv")
            if "tasa_eur" in columns and "tasa_eur_bcv" not in columns:
                conn.execute("ALTER TABLE rates_history RENAME COLUMN tasa_eur TO tasa_eur_bcv")
        except Exception:
            pass

        # Migrar registro previo existente en rates hacia el histórico si aplica
        try:
            conn.execute("""
                INSERT OR IGNORE INTO rates_history (fecha_valor, tasa_bcv, tasa_eur_bcv, source, created_at, updated_at)
                SELECT fecha_valor, tasa, COALESCE(tasa_eur, 0.0), source, updated_at, updated_at
                FROM rates
                WHERE fecha_valor IS NOT NULL AND fecha_valor != '1970-01-01' AND tasa > 0
            """)
        except Exception:
            pass

        exists = conn.execute("SELECT COUNT(*) FROM rates").fetchone()[0]
        if exists == 0:
            conn.execute("""
                INSERT INTO rates (id, tasa, fecha_valor, source, tasa_eur)
                VALUES (1, 0.0, '1970-01-01', 'init', 0.0)
            """)

        # Si el histórico está vacío y existe el archivo inicial data/historical_rates.csv, se auto-importa
        history_count = conn.execute("SELECT COUNT(*) FROM rates_history").fetchone()[0]
        if history_count == 0:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            default_csv = os.path.join(base_dir, "data", "historical_rates.csv")
            if os.path.exists(default_csv):
                _import_csv_data(conn, default_csv)

def _parse_csv_number(val: str) -> float:
    if not val:
        return 0.0
    val_clean = str(val).strip().replace('"', '').replace("'", '').strip()
    if ',' in val_clean and '.' in val_clean:
        val_clean = val_clean.replace('.', '').replace(',', '.')
    elif ',' in val_clean:
        val_clean = val_clean.replace(',', '.')
    return float(val_clean)

def _parse_csv_date(date_str: str) -> str:
    date_str = str(date_str).strip()
    if "/" in date_str:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    return date_str

def _import_csv_data(conn, csv_path: str) -> int:
    rows = []
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if not row or len(row) < 3:
                continue
            try:
                fv = _parse_csv_date(row[0])
                usd = _parse_csv_number(row[1])
                eur = _parse_csv_number(row[2])
                rows.append((fv, usd, eur))
            except Exception:
                continue

    if not rows:
        return 0

    rows.sort(key=lambda x: x[0])
    for fv, usd, eur in rows:
        conn.execute("""
            INSERT INTO rates_history (fecha_valor, tasa_bcv, tasa_eur_bcv, source, created_at, updated_at)
            VALUES (?, ?, ?, 'historical:excel', datetime('now'), datetime('now'))
            ON CONFLICT(fecha_valor) DO UPDATE SET
                tasa_bcv = excluded.tasa_bcv,
                tasa_eur_bcv = excluded.tasa_eur_bcv,
                source = excluded.source,
                updated_at = datetime('now')
        """, (fv, usd, eur))

    # Actualizar la tasa activa en rates
    latest_fecha, latest_usd, latest_eur = rows[-1]
    conn.execute("""
        INSERT INTO rates (id, tasa, fecha_valor, source, updated_at, last_scraped_at, tasa_eur)
        VALUES (1, ?, ?, 'historical:excel', datetime('now'), datetime('now'), ?)
        ON CONFLICT(id) DO UPDATE SET
            tasa = excluded.tasa,
            fecha_valor = excluded.fecha_valor,
            source = excluded.source,
            updated_at = datetime('now'),
            last_scraped_at = datetime('now'),
            tasa_eur = excluded.tasa_eur
    """, (latest_usd, latest_fecha, latest_eur))
    return len(rows)

def import_history_from_csv(csv_path: Optional[str] = None) -> int:
    if not csv_path:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(base_dir, "data", "historical_rates.csv")

    if not os.path.exists(csv_path):
        return 0

    init_db()
    with _connect() as conn:
        return _import_csv_data(conn, csv_path)

def get_rate() -> Optional[Dict]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM rates WHERE id = 1").fetchone()
        return dict(row) if row else None

def save_rate_history(tasa: float, fecha_valor: str, source: str = "live", tasa_eur: float = 0.0, **kwargs) -> None:
    if not fecha_valor or fecha_valor == "1970-01-01" or tasa <= 0:
        return
    eur = kwargs.get("tasa_eur_bcv", tasa_eur)
    usd = kwargs.get("tasa_bcv", tasa)
    with _connect() as conn:
        conn.execute("""
            INSERT INTO rates_history (fecha_valor, tasa_bcv, tasa_eur_bcv, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
            ON CONFLICT(fecha_valor) DO UPDATE SET
                tasa_bcv = excluded.tasa_bcv,
                tasa_eur_bcv = excluded.tasa_eur_bcv,
                source = excluded.source,
                updated_at = datetime('now')
        """, (fecha_valor, usd, eur, source))

def upsert_rate(tasa: float, fecha_valor: str, source: str = "live", mark_scraped: bool = True, tasa_eur: float = 0.0) -> None:
    with _connect() as conn:
        if mark_scraped:
            conn.execute("""
                INSERT INTO rates (id, tasa, fecha_valor, source, updated_at, last_scraped_at, tasa_eur)
                VALUES (1, ?, ?, ?, datetime('now'), datetime('now'), ?)
                ON CONFLICT(id) DO UPDATE SET
                    tasa = excluded.tasa,
                    fecha_valor = excluded.fecha_valor,
                    source = excluded.source,
                    updated_at = datetime('now'),
                    last_scraped_at = datetime('now'),
                    tasa_eur = excluded.tasa_eur
            """, (tasa, fecha_valor, source, tasa_eur))
        else:
            conn.execute("""
                INSERT INTO rates (id, tasa, fecha_valor, source, updated_at, tasa_eur)
                VALUES (1, ?, ?, ?, datetime('now'), ?)
                ON CONFLICT(id) DO UPDATE SET
                    tasa = excluded.tasa,
                    fecha_valor = excluded.fecha_valor,
                    source = excluded.source,
                    updated_at = datetime('now'),
                    tasa_eur = excluded.tasa_eur
            """, (tasa, fecha_valor, source, tasa_eur))

        # Registrar en la tabla de histórico diario
        if fecha_valor and fecha_valor != "1970-01-01" and tasa > 0:
            conn.execute("""
                INSERT INTO rates_history (fecha_valor, tasa_bcv, tasa_eur_bcv, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
                ON CONFLICT(fecha_valor) DO UPDATE SET
                    tasa_bcv = excluded.tasa_bcv,
                    tasa_eur_bcv = excluded.tasa_eur_bcv,
                    source = excluded.source,
                    updated_at = datetime('now')
            """, (fecha_valor, tasa, tasa_eur, source))

def get_rates_history(limit: Optional[int] = None, order: str = "DESC") -> List[Dict]:
    order_direction = "ASC" if str(order).upper() == "ASC" else "DESC"
    query = f"SELECT * FROM rates_history ORDER BY fecha_valor {order_direction}"
    params = []
    if limit is not None and limit > 0:
        query += " LIMIT ?"
        params.append(limit)
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

def get_rate_by_date(fecha_valor: str) -> Optional[Dict]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM rates_history WHERE fecha_valor = ?", (fecha_valor,)).fetchone()
        return dict(row) if row else None
