import requests
from bs4 import BeautifulSoup

def obtener_tasa_bcv():
    url = "https://www.bcv.org.ve/"  # Mejor usar HTTPS
    try:
        response = requests.get(url, timeout=10, verify=False)  # ⚡ Ignorando SSL
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Buscar el div con id="dolar"
        dolar_div = soup.find('div', id='dolar')

        if dolar_div:
            # Dentro de dolar_div, encontrar el primer <strong>
            strong_tag = dolar_div.find('strong')
            if strong_tag:
                tasa_text = strong_tag.text.strip()
                tasa = float(tasa_text.replace(',', '.'))  # Convertir a número
                return tasa
            else:
                print("⚠️ No se encontró la etiqueta <strong> en #dolar.")
                return None
        else:
            print("⚠️ No se encontró el div con id='dolar'.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        return None
    except Exception as e:
        print(f"❌ Error al parsear la página: {e}")
        return None

# --- Ejecución ---
if __name__ == "__main__":
    tasa = obtener_tasa_bcv()
    if tasa:
        print(f"💱 La tasa oficial del BCV es: {tasa} Bs/USD")
    else:
        print("⚠️ No se pudo obtener la tasa de cambio.")
