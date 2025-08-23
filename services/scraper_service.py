import requests
from bs4 import BeautifulSoup
from typing import Optional

BCV_URL = "https://www.bcv.org.ve/"

def fetch_bcv() -> BeautifulSoup:
    r = requests.get(BCV_URL, timeout=10, verify=False)
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
    try:
        return float(strong_tag.text.strip().replace(',', '.'))
    except ValueError:
        return None
