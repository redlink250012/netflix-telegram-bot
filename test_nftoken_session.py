"""
Prueba: usar nftoken y luego visitar /account con las cookies recibidas
"""
import requests

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
r = requests.post('https://android13.prod.ftl.netflix.com/graphql', headers=headers, json=payload, verify=False, timeout=15)
token = r.json()['data']['createAutoLoginToken']
print('Token OK')

# Usar session para mantener cookies entre requests
s = requests.Session()
ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# 1) Visitar nftoken - capturar cookies
r = s.get(
    f'https://www.netflix.com/account?nftoken={token}',
    headers={'User-Agent': ua},
    allow_redirects=False,
    timeout=10
)
print(f'1) nftoken visit: Status={r.status_code}')
nf_cookie = s.cookies.get('NetflixId', 'NO')
snf_cookie = s.cookies.get('SecureNetflixId', 'NO')
nf_display = nf_cookie[:50] if nf_cookie != 'NO' else 'NO'
print(f'   NetflixId recibido: {nf_display}')

# 2) Ir a /account con las cookies que nos dio el token
r2 = s.get(
    'https://www.netflix.com/account',
    headers={'User-Agent': ua},
    allow_redirects=True,
    timeout=10
)
print(f'2) /account: Status={r2.status_code} URL={r2.url[:80]}')
if '/login' in r2.url.lower():
    print('   -> Redirige a login')
else:
    print('   >>> FUNCIONA! Estamos dentro!')
    # Extraer email
    import re
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', r2.text)
    emails = [e for e in emails if not any(x in e for x in ['nflxext', '.js', '.css', '.png'])]
    if emails:
        print(f'   Email: {emails[0]}')

# 3) Probar visitar nftoken con follow_redirects=True
s2 = requests.Session()
r3 = s2.get(
    f'https://www.netflix.com/account?nftoken={token}',
    headers={'User-Agent': ua},
    allow_redirects=True,
    timeout=10
)
print(f'3) nftoken + redirects: URL={r3.url[:80]}')
r4 = s2.get(
    'https://www.netflix.com/account',
    headers={'User-Agent': ua},
    allow_redirects=True,
    timeout=10
)
print(f'   Luego /account: Status={r4.status_code} URL={r4.url[:80]}')
if '/login' not in r4.url.lower():
    print('   >>> FUNCIONA con redirects seguidos!')
else:
    print('   -> No funciona')
