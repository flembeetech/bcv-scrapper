from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def obtener_tasa_bcv():
    url = "https://www.bcv.org.ve/"
    try:
        response = requests.get(url, timeout=10, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        dolar_div = soup.find('div', id='dolar')
        if dolar_div:
            strong_tag = dolar_div.find('strong')
            if strong_tag:
                tasa_text = strong_tag.text.strip()
                tasa = float(tasa_text.replace(',', '.'))
                return tasa
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
    except Exception as e:
        print(f"❌ Error al parsear la página: {e}")
    return None

@app.route("/")
def mostrar_tasa():
    tasa = obtener_tasa_bcv()
    if tasa:
        return jsonify({"tasa_bcv": tasa})
    return jsonify({"error": "No se pudo obtener la tasa de cambio"})

# Solo se usa para pruebas locales, en producción se usa gunicorn
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
