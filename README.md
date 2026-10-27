# BCV Scrapper API

Este proyecto es una API desarrollada en Python con Flask que se encarga de extraer (scrapear) las tasas de cambio del Dólar (USD) y Euro (EUR) desde el sitio web oficial del Banco Central de Venezuela (BCV).

La aplicación almacena tanto el caché de la tasa activa como el **histórico diario de tasas** en una base de datos SQLite para evitar peticiones redundantes al sitio del BCV y ofrecer una respuesta rápida.

## Características

- **Scraping en tiempo real**: Obtiene las tasas oficiales del BCV.
- **Soporte Multi-moneda**: Soporta Tasa Dólar (`tasa_bcv`) y Tasa Euro (`tasa_eur_bcv`).
- **Histórico Diario de Tasas**: Tabla `rates_history` para almacenar cada fecha oficial con su tasa en USD y EUR de forma persistente.
- **Almacenamiento Local**: Base de datos SQLite (`rates` para caché activo y `rates_history` para histórico).
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

Devuelve la tasa actual. Si ya se tiene una tasa actualizada en base de datos para el día de hoy, la devuelve. Si no, intenta scrapear el sitio del BCV y almacena el registro en el histórico.

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

### 3. Obtener Histórico de Tasas
`GET /history`

Devuelve la lista de tasas históricas guardadas diariamente, ordenadas de la más reciente a la más antigua por defecto.

**Parámetros de consulta opcionales:**
- `limit`: Número máximo de registros a devolver (ejemplo: `/history?limit=30`).
- `order`: Dirección de ordenamiento por fecha (`DESC` por defecto o `ASC`).

**Respuesta:**
```json
{
  "total": 2,
  "rates": [
    {
      "id": 2,
      "fecha_valor": "2026-01-23",
      "tasa": 352.7063,
      "tasa_bcv": 352.7063,
      "tasa_eur": 413.389,
      "tasa_eur_bcv": 413.389,
      "source": "live",
      "created_at": "2026-01-23 13:45:00",
      "updated_at": "2026-01-23 13:45:00"
    },
    {
      "id": 1,
      "fecha_valor": "2026-01-22",
      "tasa": 350.1500,
      "tasa_bcv": 350.1500,
      "tasa_eur": 410.200,
      "tasa_eur_bcv": 410.200,
      "source": "live",
      "created_at": "2026-01-22 14:00:00",
      "updated_at": "2026-01-22 14:00:00"
    }
  ]
}
```

### 4. Obtener Tasa de una Fecha Específica
`GET /history/<fecha>`

Devuelve la tasa histórica oficial para la fecha especificada en formato `YYYY-MM-DD` (ejemplo: `/history/2026-01-23`).

**Respuesta:**
```json
{
  "id": 2,
  "fecha_valor": "2026-01-23",
  "tasa": 352.7063,
  "tasa_bcv": 352.7063,
  "tasa_eur": 413.389,
  "tasa_eur_bcv": 413.389,
  "source": "live",
  "created_at": "2026-01-23 13:45:00",
  "updated_at": "2026-01-23 13:45:00"
}
```

Si no existe registro para esa fecha, retorna un código HTTP `404`:
```json
{
  "error": "No se encontró tasa para la fecha 2026-01-23"
}
```

## Estructura del Proyecto

- `main.py`: Punto de entrada de la aplicación Flask y lógica de endpoints (`/`, `/latest`, `/history`, `/history/<fecha>`).
- `import_history.py`: Script CLI para importar o actualizar datos históricos desde archivos CSV hacia SQLite.
- `data/`:
    - `historical_rates.csv`: Dataset inicial de tasas históricas oficiales (USD y EUR).
- `services/`
    - `db_service.py`: Manejo de la conexión a SQLite, creación de tablas, migración, seeding y operaciones CRUD para tasas activas e históricas.
    - `scraper_service.py`: Lógica para conectar con bcv.org.ve y parsear el HTML.

## Base de Datos

Se utiliza un archivo SQLite `bcv_rates.sqlite3` con dos tablas:
1. `rates`: Mantiene un único registro (`id=1`) actualizado con la última información válida para respuesta en tiempo real y caché de scrape.
2. `rates_history`: Almacena el histórico diario de tasas oficiales (`fecha_valor` única, `tasa` USD, `tasa_eur` EUR, `source`, `created_at`, `updated_at`). Al hacer scraping cada día, se crea o actualiza automáticamente el registro del día.

### Importación de Datos Históricos
El dataset inicial en `data/historical_rates.csv` se auto-importa al iniciar la aplicación en una base de datos nueva. También puedes ejecutar la importación manualmente en cualquier momento:

```bash
python import_history.py
# o especificando otro archivo:
python import_history.py ruta/a/tu_archivo.csv
```