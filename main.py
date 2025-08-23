from flask import Flask, jsonify
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo 

from services.db_service import init_db, get_rate, upsert_rate
from services.scraper_service import fetch_bcv, parse_fecha_valor, parse_tasa

app = Flask(__name__)
CARACAS_TZ = ZoneInfo('America/Caracas')

init_db()

def _date_of(ts: str | None) -> str:
    return (ts or "")[:10]

def should_scrape(today: str, rec: dict | None) -> bool:
    if not rec:
        return True

    fv = rec.get("fecha_valor") or "1970-01-01"
    scraped_today = _date_of(rec.get("last_scraped_at")) == today

    if today < fv:
        return False
    if today == fv:
        return not scraped_today
    return True

@app.route("/")
def mostrar_tasa():
    fecha_hora_caracas = datetime.now(CARACAS_TZ)
    today = fecha_hora_caracas.strftime('%Y-%m-%d')
    rec = get_rate()

    if not should_scrape(today, rec):
        return jsonify({
            "tasa_bcv": rec["tasa"],
            "fecha_valor": rec["fecha_valor"],
            "source": "db:no_scrape_needed",
            "hora_caracas": fecha_hora_caracas.strftime('%Y-%m-%d %H:%M:%S'),
        }), 200

    try:
        soup = fetch_bcv()
        fecha_valor = parse_fecha_valor(soup)
        tasa = parse_tasa(soup)
    except Exception as e:
        if rec:
            return jsonify({
                "tasa_bcv": rec["tasa"],
                "fecha_valor": rec["fecha_valor"],
                "source": "db:scrape_error",
                "error": str(e),
                "hora_caracas": fecha_hora_caracas.strftime('%Y-%m-%d %H:%M:%S'),
            }), 200
        return jsonify({"error": f"No BCV y sin datos en DB: {e}"}), 503

    if (fecha_valor is None) or (tasa is None):
        if rec:
            return jsonify({
                "tasa_bcv": rec["tasa"],
                "fecha_valor": rec["fecha_valor"],
                "source": "db:parse_error",
                "hora_caracas": fecha_hora_caracas.strftime('%Y-%m-%d %H:%M:%S'),
            }), 200
        return jsonify({"error": "No se pudo obtener tasa/fecha"}), 503

    upsert_rate(tasa, fecha_valor, source="live", mark_scraped=True)
    new_rec = get_rate()
    return jsonify({
        "tasa_bcv": new_rec["tasa"],
        "fecha_valor": new_rec["fecha_valor"],
        "source": new_rec["source"],
        "hora_caracas": fecha_hora_caracas.strftime('%Y-%m-%d %H:%M:%S'),
    }), 200

@app.route("/latest")
def ultima_tasa_guardada():
    rec = get_rate()
    if not rec:
        return jsonify({"error": "No hay datos almacenados"}), 404
    return jsonify(rec), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
