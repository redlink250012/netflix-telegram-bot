"""
Test: navegador real con Playwright
1. Genera nftoken
2. Abre navegador, va a nftoken URL
3. Verifica si queda logueado
"""
import requests, urllib.parse, json, warnings, sys, os
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'netflix_cookies.txt')

# Generate token
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
        elif '=' in line and not line.startswith('.'):
            n, v = line.split('=', 1)
            cookies[n.strip()] = v.strip()

cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())
headers = {
    'User-Agent': 'com.netflix.mediaclient/63884',
    'Accept': 'application/json', 'Content-Type': 'application/json',
    'Cookie': cookie_str,
}
payload = {
    'operationName': 'CreateAutoLoginToken',
    'variables': {'scope': 'WEBVIEW_MOBILE_STREAMING'},
    'extensions': {'persistedQuery': {'version': 102, 'id': '76e97129-f4b5-41a0-a73c-12e674896849'}}
}
r = requests.post('https://android13.prod.ftl.netflix.com/graphql',
                  headers=headers, json=payload, verify=False, timeout=15)
token = r.json()['data']['createAutoLoginToken']
url = 'https://www.netflix.com/account?nftoken=' + urllib.parse.quote(token, safe='')
print('Token generado')
print('URL: ' + url)
print()

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.134 Mobile Safari/537.36',
        viewport={'width': 412, 'height': 915},
        locale='es-MX',
    )
    page = context.new_page()

    # Step 1: Go to nftoken URL
    print('1) Navegando a nftoken URL...')
    page.goto(url, wait_until='networkidle', timeout=30000)
    print('   URL final: ' + page.url[:100])

    # Check cookies
    nf = page.context.cookies()
    nf_ids = [c for c in nf if c['name'] in ('NetflixId', 'SecureNetflixId')]
    print('   Cookies NetflixId: ' + ('SI' if any(c['name']=='NetflixId' for c in nf_ids) else 'NO'))
    print('   Cookies SecureNetflixId: ' + ('SI' if any(c['name']=='SecureNetflixId' for c in nf_ids) else 'NO'))

    # Step 2: Navigate to browse
    print('2) Navegando a /browse...')
    page.goto('https://www.netflix.com/browse', wait_until='networkidle', timeout=30000)
    print('   URL final: ' + page.url[:100])

    if '/login' not in page.url.lower():
        print('   >>> LOGUEADO!')
        page_title = page.title()
        print('   Titulo: ' + page_title)
        # Take screenshot
        page.screenshot(path='netflix_logueado.png')
        print('   Screenshot guardado: netflix_logueado.png')
    else:
        print('   -> Login page')
        page.screenshot(path='netflix_login.png')
        print('   Screenshot guardado: netflix_login.png')

    # Step 3: Try with /browse directly (maybe nftoken + redirect chain works differently)
    print()
    print('3) Probando sin cookies, solo nftoken...')
    context2 = browser.new_context(
        user_agent='Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/126.0.6478.134 Mobile Safari/537.36',
        viewport={'width': 412, 'height': 915},
    )
    page2 = context2.new_page()

    # Listen for all responses to capture cookies
    def log_response(response):
        if 'Set-Cookie' in str(response.headers):
            print('   Set-Cookie en: ' + response.url[:60])

    page2.on('response', log_response)

    # Navigate to nftoken URL directly (no prior cookies)
    page2.goto(url, wait_until='networkidle', timeout=30000)
    print('   URL final: ' + page2.url[:100])

    # Then browse
    page2.goto('https://www.netflix.com/browse', wait_until='networkidle', timeout=30000)
    print('   /browse URL: ' + page2.url[:100])
    if '/login' not in page2.url.lower():
        print('   >>> LOGUEADO en test 3!')
    else:
        print('   -> Login page')

    input('Presiona Enter para cerrar...')
    browser.close()
