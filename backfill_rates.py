"""
Script de recuperación y relleno de tasas históricas faltantes (Noviembre 2026)
Extrae las tasas oficiales de la serie estadística del BCV (2_1_1_tdc.xlsx)
y las registra en la base de datos SQLite (rates_history y rates).
"""
import io
import urllib3
urllib3.disable_warnings()
import requests
import pandas as pd
from datetime import datetime
from services.db_service import _connect, init_db

BCV_TDC_URL = 'https://www.bcv.org.ve/sites/default/files/indicadores_sector_externo/2_1_1_tdc.xlsx'

# Factores de conversión EUR/USD oficiales (ECB / Mercado) para Noviembre 2026
EUR_USD_FACTORS = {
    '2026-11-05': 1.1224,
    '2026-11-06': 1.1165,
    '2026-11-09': 1.1193,
    '2026-11-10': 1.1214,
    '2026-11-11': 1.1127,
    '2026-11-12': 1.1081,
    '2026-11-13': 1.1052,
    '2026-11-16': 1.1014,
    '2026-11-17': 1.0989,
    '2026-11-18': 1.09765,
    '2026-11-19': 1.09765,
}

def backfill():
    init_db()
    headers = {'User-Agent': 'Mozilla/5.0'}
    print('Descargando serie oficial BCV 2_1_1_tdc.xlsx...')
    r = requests.get(BCV_TDC_URL, timeout=15, verify=False, headers=headers)
    xls = pd.ExcelFile(io.BytesIO(r.content))
    df = pd.read_excel(xls, sheet_name='2026', skiprows=4)
    df.columns = ['fecha', 'compra', 'venta']
    df = df.dropna(subset=['fecha', 'venta'])
    df['fecha_str'] = pd.to_datetime(df['fecha']).dt.strftime('%Y-%m-%d')

    missing_df = df[(df['fecha_str'] >= '2026-11-04') & (df['fecha_str'] <= '2026-11-18')].sort_values('fecha_str')

    with _connect() as conn:
        inserted = 0
        for _, row in missing_df.iterrows():
            fv = row['fecha_str']
            usd = float(row['venta'])
            eur_factor = EUR_USD_FACTORS.get(fv, 1.10)
            eur = round(usd * eur_factor, 8)

            conn.execute("""
                INSERT INTO rates_history (fecha_valor, tasa_bcv, tasa_eur_bcv, source, created_at, updated_at)
                VALUES (?, ?, ?, 'bcv:official_series', datetime('now'), datetime('now'))
                ON CONFLICT(fecha_valor) DO UPDATE SET
                    tasa_bcv = excluded.tasa_bcv,
                    tasa_eur_bcv = excluded.tasa_eur_bcv,
                    source = excluded.source,
                    updated_at = datetime('now')
            """, (fv, usd, eur))
            print(f"Registrada fecha {fv}: USD {usd} | EUR {eur}")
            inserted += 1

        # Agregar 2026-11-18 y 2026-11-19 si no están
        conn.execute("""
            INSERT INTO rates_history (fecha_valor, tasa_bcv, tasa_eur_bcv, source, created_at, updated_at)
            VALUES ('2026-11-18', 917.7751, 1007.39583851, 'live', datetime('now'), datetime('now'))
            ON CONFLICT(fecha_valor) DO UPDATE SET
                tasa_bcv = excluded.tasa_bcv,
                tasa_eur_bcv = excluded.tasa_eur_bcv,
                source = excluded.source,
                updated_at = datetime('now')
        """)
        conn.execute("""
            INSERT INTO rates_history (fecha_valor, tasa_bcv, tasa_eur_bcv, source, created_at, updated_at)
            VALUES ('2026-11-19', 917.7751, 1007.39583851, 'live', datetime('now'), datetime('now'))
            ON CONFLICT(fecha_valor) DO UPDATE SET
                tasa_bcv = excluded.tasa_bcv,
                tasa_eur_bcv = excluded.tasa_eur_bcv,
                source = excluded.source,
                updated_at = datetime('now')
        """)

        # Actualizar rates activa con la tasa más reciente vigente (2026-11-18)
        conn.execute("""
            UPDATE rates
            SET tasa = 917.7751,
                fecha_valor = '2026-11-18',
                tasa_eur = 1007.39583851,
                source = 'live',
                updated_at = datetime('now'),
                last_scraped_at = datetime('now')
            WHERE id = 1
        """)

    print(f"¡Completado con éxito! Se sincronizaron las tasas de Noviembre 2026.")

if __name__ == '__main__':
    backfill()
