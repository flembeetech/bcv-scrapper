import requests
from bs4 import BeautifulSoup
from typing import Optional

BCV_URL = "https://www.bcv.org.ve/"

def _clean_currency_text(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    val = text.strip().replace('"', '').replace("'", '').strip()
    # Si contiene separador de miles '.' y decimal ',' (ej: 1.007,3958)
    if '.' in val and ',' in val:
        val = val.replace('.', '').replace(',', '.')
    elif ',' in val:
        val = val.replace(',', '.')
    try:
        return float(val)
    except ValueError:
        return None

def fetch_bcv() -> BeautifulSoup:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    r = requests.get(BCV_URL, timeout=15, verify=False, headers=headers)
    r.raise_for_status()
    return BeautifulSoup(r.content, 'html.parser')

def parse_fecha_valor(soup: BeautifulSoup) -> Optional[str]:
    el = soup.select_one('div.pull-right.dinpro.center span.date-display-single[content]')
    if not el:
        return None
    content = el.get('content', '')
    return content.split('T', 1)[0] if 'T' in content else content or None

def parse_tasa(soup: BeautifulSoup) -> Optional[float]:
    dolar_div = soup.find('div', id='dolar')
    if not dolar_div:
        return None
    strong_tag = dolar_div.find('strong')
    if not strong_tag:
        return None
    return _clean_currency_text(strong_tag.text)

def parse_tasa_eur(soup: BeautifulSoup) -> Optional[float]:
    euro_div = soup.find('div', id='euro')
    if not euro_div:
        return None
    strong_tag = euro_div.find('strong')
    if not strong_tag:
        return None
    return _clean_currency_text(strong_tag.text)
