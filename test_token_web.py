"""
Busca alternativas para generar un token web funcional
"""
import requests, json, re

cookies = {}
with open('netflix_cookies.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '.netflix.com' in line:
            parts = line.split('\t')
            if len(parts) >= 7:
                cookies[parts[5].strip()] = parts[6].strip()
            elif '=' in line:
                n, v = line.split('=', 1)
                cookies[n.strip()] = v.strip()

cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())

# Probar si el token nftoken funciona ENVIANDO las cookies originales tambien
print("=== TEST 1: nftoken + cookies originales ===")
token = None
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
r = requests.post('https://android13.prod.ftl.netflix.com/graphql', headers=headers, json=payload, verify=False, timeout=15)
data = r.json()
token = data.get('data', {}).get('createAutoLoginToken')
print(f'Token generado: {token[:50] if token else "NO"}...')

if token:
    # Probar nftoken CON cookies
    r = requests.get(
        f'https://www.netflix.com/account?nftoken={token}',
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                 'Cookie': cookie_str},
        allow_redirects=True, timeout=10
    )
    print(f'Con cookies: Status={r.status_code} URL={r.url[:80]}')
    if '/login' not in r.url.lower():
        print('>>> FUNCIONA con cookies!')
    else:
        print('>>> NO funciona incluso con cookies')

    # Probar nftoken SIN cookies (sesion limpia)
    r = requests.get(
        f'https://www.netflix.com/account?nftoken={token}',
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
        allow_redirects=True, timeout=10
    )
    print(f'Sin cookies: Status={r.status_code} URL={r.url[:80]}')
    if '/login' not in r.url.lower():
        print('>>> FUNCIONA sin cookies!')
    else:
        print('>>> NO funciona sin cookies')

print()

# TEST 2: Probar diferentes GraphQL queries en el endpoint web
print("=== TEST 2: API GraphQL en web ===")
tests = [
    # Probar si hay query de login en web
    {'query': 'query { viewer { id } }', 'variables': {}},
]

for test in tests:
    r = requests.post(
        'https://www.netflix.com/api/graphql',
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json',
            'Cookie': cookie_str,
        },
        json=test, verify=False, timeout=10
    )
    print(f'Status: {r.status_code}, Body: {r.text[:200]}')

print()

# TEST 3: Ver si hay alguna API que devuelva un token de sesion
print("=== TEST 3: Shakti API ===")
for path in ['/api/shakti/user', '/api/shakti/membership']:
    r = requests.get(
        f'https://www.netflix.com{path}',
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cookie': cookie_str,
        },
        allow_redirects=False, verify=False, timeout=10
    )
    print(f'{path}: Status={r.status_code}, Body={r.text[:200]}')
