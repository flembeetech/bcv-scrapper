from flask import Flask, jsonify, request
from datetime import datetime
from zoneinfo import ZoneInfo

from services.db_service import (
    init_db,
    get_rate,
    upsert_rate,
    save_rate_history,
    get_rates_history,
    get_rate_by_date,
)
from services.scraper_service import fetch_bcv, parse_fecha_valor, parse_tasa, parse_tasa_eur

app = Flask(__name__)
CARACAS_TZ = ZoneInfo('America/Caracas')

init_db()

def _date_of(ts: str | None) -> str:
    return (ts or "")[:10]

def should_scrape(today: str, rec: dict | None) -> bool:
    if not rec:
        return True

    # Si falta la tasa euro (por migración o error previo), forzamos scrape
    if not rec.get("tasa_eur"):
        return True

    fv = rec.get("fecha_valor") or "1970-01-01"
    scraped_today = _date_of(rec.get("last_scraped_at")) == today

    # Parseamos para comparar como fechas
    today_date = datetime.strptime(today, "%Y-%m-%d").date()
    fv_date = datetime.strptime(fv, "%Y-%m-%d").date()

    # Si ya scrapeamos hoy y la fecha_valor es >= today, no scrapeamos de nuevo
    if fv_date >= today_date and scraped_today:
        return False

    # Si la tasa guardada tiene fecha_valor menor a today o no se ha scrapeado hoy → scrapea
    return True

@app.route("/")
def mostrar_tasa():
    fecha_hora_caracas = datetime.now(CARACAS_TZ)
    today = fecha_hora_caracas.strftime('%Y-%m-%d')
    today_date = datetime.strptime(today, "%Y-%m-%d").date()
    rec = get_rate()

    if not should_scrape(today, rec):
        return jsonify({
            "tasa_bcv": rec["tasa"],
            "tasa_eur_bcv": rec.get("tasa_eur"),
            "fecha_valor": rec["fecha_valor"],
            "source": "db:no_scrape_needed",
            "hora_caracas": fecha_hora_caracas.strftime('%Y-%m-%d %H:%M:%S'),
        }), 200

    try:
        soup = fetch_bcv()
        fecha_valor = parse_fecha_valor(soup)
        tasa = parse_tasa(soup)
        tasa_eur = parse_tasa_eur(soup)

        if fecha_valor is None or tasa is None:
            raise ValueError("No se pudo obtener tasa o fecha_valor")
        
        if tasa_eur is None:
             # Si falla euro, podríamos lanzar error o dejarlo None/0. 
             # Asumiremos que es crítico y lanzamos error para consistencia, 
             # o defaulting a 0 si se prefiere resiliencia parcial. 
             # El requerimiento implica que "tambien necesito almacenar la tasa euro", así que mejor fallar si no está.
             raise ValueError("No se pudo obtener la tasa euro")

        fecha_valor_date = datetime.strptime(fecha_valor, "%Y-%m-%d").date()

        # Guardar en histórico diario (incluso si fecha_valor es futura para la tasa activa)
        save_rate_history(tasa, fecha_valor, source="live", tasa_eur=tasa_eur)

        # Si la fecha valor es futura, no se guarda aún como tasa activa
        if fecha_valor_date > today_date:
            return jsonify({
                "tasa_bcv": rec["tasa"] if rec else None,
                "tasa_eur_bcv": rec.get("tasa_eur") if rec else None,
                "fecha_valor": rec["fecha_valor"] if rec else None,
                "source": "db:future_fecha_valor_skipped",
                "hora_caracas": fecha_hora_caracas.strftime('%Y-%m-%d %H:%M:%S'),
            }), 200

        # Guardar la nueva tasa
        upsert_rate(tasa, fecha_valor, source="live", mark_scraped=True, tasa_eur=tasa_eur)
        new_rec = get_rate()

        return jsonify({
            "tasa_bcv": new_rec["tasa"],
            "tasa_eur_bcv": new_rec.get("tasa_eur"),
            "fecha_valor": new_rec["fecha_valor"],
            "source": new_rec["source"],
            "hora_caracas": fecha_hora_caracas.strftime('%Y-%m-%d %H:%M:%S'),
        }), 200

    except Exception as e:
        if rec:
            return jsonify({
                "tasa_bcv": rec["tasa"],
                "tasa_eur_bcv": rec.get("tasa_eur"),
                "fecha_valor": rec["fecha_valor"],
                "source": "db:scrape_error",
                "error": str(e),
                "hora_caracas": fecha_hora_caracas.strftime('%Y-%m-%d %H:%M:%S'),
            }), 200
        return jsonify({"error": f"No BCV y sin datos en DB: {e}"}), 503

@app.route("/latest")
def ultima_tasa_guardada():
    rec = get_rate()
    if not rec:
        return jsonify({"error": "No hay datos almacenados"}), 404
    return jsonify(rec), 200

@app.route("/history")
def historico_tasas():
    limit = request.args.get("limit", default=None, type=int)
    order = request.args.get("order", default="DESC", type=str)
    records = get_rates_history(limit=limit, order=order)
    return jsonify({
        "total": len(records),
        "rates": records
    }), 200

@app.route("/history/<string:fecha>")
def tasa_por_fecha(fecha: str):
    rec = get_rate_by_date(fecha)
    if not rec:
        return jsonify({"error": f"No se encontró tasa para la fecha {fecha}"}), 404
    return jsonify(rec), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

