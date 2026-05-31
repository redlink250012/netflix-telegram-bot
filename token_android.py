"""
Genera token de acceso para Netflix en Android
Muestra URL + QR para escanear desde el celular
"""
import requests
import urllib.parse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import qrcode
    from qrcode.image.pil import PilImage
    HAS_QR = True
except ImportError:
    HAS_QR = False

COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'netflix_cookies.txt')

def generar_token():
    cookies = {}
    with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '.netflix.com' in line:
                parts = line.split('\t')
                if len(parts) >= 7:
                    cookies[parts[5].strip()] = parts[6].strip()

    if not cookies:
        print("No se encontraron cookies en netflix_cookies.txt")
        return None

    cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())
    headers = {
        'User-Agent': 'com.netflix.mediaclient/63884',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Cookie': cookie_str,
    }
    payload = {
        'operationName': 'CreateAutoLoginToken',
        'variables': {'scope': 'WEBVIEW_MOBILE_STREAMING'},
        'extensions': {'persistedQuery': {'version': 102, 'id': '76e97129-f4b5-41a0-a73c-12e674896849'}}
    }
    r = requests.post(
        'https://android13.prod.ftl.netflix.com/graphql',
        headers=headers, json=payload, verify=False, timeout=15
    )
    data = r.json()
    if 'errors' in data:
        print(f"Error: {data['errors']}")
        return None
    return data['data']['createAutoLoginToken']

token = generar_token()
if not token:
    sys.exit(1)

url_encoded = urllib.parse.quote(token, safe='')
url = f'https://www.netflix.com/account?nftoken={url_encoded}'

print()
print("=" * 60)
print("  TOKEN NETFLIX PARA ANDROID")
print("=" * 60)
print(f"  Token: {token[:40]}...")
print()
print(f"  URL: {url}")
print()
print("  Abrí esta URL en Chrome en tu Android")
print("  y se va a logear automáticamente.")
print("=" * 60)
print()

if HAS_QR:
    try:
        qr = qrcode.QRCode(box_size=3, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except Exception as e:
        print(f"  (QR no disponible: {e})")
else:
    print("  (Instalá 'qrcode[pil]' para ver QR: pip install qrcode[pil])")

print()
