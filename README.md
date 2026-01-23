# BCV Scrapper API

Este proyecto es una API desarrollada en Python con Flask que se encarga de extraer (scrapear) las tasas de cambio del Dólar (USD) y Euro (EUR) desde el sitio web oficial del Banco Central de Venezuela (BCV).

La aplicación almacena el historial de tasas en una base de datos SQLite para evitar peticiones redundantes al sitio del BCV y ofrece una respuesta rápida.

## Características

- **Scraping en tiempo real**: Obtiene las tasas oficiales del BCV.
- **Soporte Multi-moneda**: Soporta Tasa Dólar (`tasa_bcv`) y Tasa Euro (`tasa_eur_bcv`).
- **Almacenamiento Local**: Guarda las tasas en una base de datos SQLite (`rates` table) para persistencia y caché.
- **Optimización**: Lógica inteligente para decidir cuándo scrapear basándose en la fecha valor y la fecha actual (Timezone America/Caracas).
- **API REST**: Endpoints sencillos y respuestas en formato JSON.

## Requisitos

- Python 3.9+
- `flask`
- `requests`
- `beautifulsoup4`
- `urllib3`

## Instalación

1.  Clona el repositorio.
2.  Crea un entorno virtual (opcional pero recomendado):
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```
3.  Instala las dependencias:
    ```bash
    pip install flask requests beautifulsoup4
    ```

## Uso

Para iniciar el servidor:

```bash
python main.py
```

El servidor se iniciará en `http://0.0.0.0:5000`.

## API Endpoints

### 1. Obtener Tasa Actual
`GET /`

Devuelve la tasa actual. Si ya se tiene una tasa actualizada en base de datos para el día de hoy, la devuelve. Si no, intenta scrapear el sitio del BCV.

**Respuesta Exitosa:**
```json
{
  "fecha_valor": "2026-01-23",
  "hora_caracas": "2026-01-23 13:45:00",
  "source": "live", 
  "tasa_bcv": 352.7063,
  "tasa_eur_bcv": 413.389
}
```

- `tasa_bcv`: Precio del Dólar.
- `tasa_eur_bcv`: Precio del Euro.
- `fecha_valor`: Fecha de vigencia de la tasa según el BCV.
- `source`: Origen del dato (e.g., `live`, `db:no_scrape_needed`, `db:future_fecha_valor_skipped`).

### 2. Obtener Última Tasa Guardada
`GET /latest`

Devuelve la última tasa almacenada en la base de datos sin intentar scrapear.

**Respuesta:**
```json
{
  "id": 1,
  "tasa": 352.7063,
  "tasa_eur": 413.389,
  "fecha_valor": "2026-01-23",
  "source": "live",
  "updated_at": "2026-01-23 13:45:00",
  "last_scraped_at": "2026-01-23 13:45:00"
}
```

## Estructura del Proyecto

- `main.py`: Punto de entrada de la aplicación Flask y lógica de endpoints.
- `services/`
    - `db_service.py`: Manejo de la conexión a SQLite y operaciones CRUD.
    - `scraper_service.py`: Lógica para conectar con bcv.org.ve y parsear el HTML.

## Base de Datos

Se utiliza un archivo SQLite `bcv_rates.sqlite3`. La tabla principal es `rates` que mantiene un único registro (ID=1) actualizado con la última información válida.