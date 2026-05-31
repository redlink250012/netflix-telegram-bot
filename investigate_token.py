"""
Investiga como funciona realmente el nftoken
"""
import requests, json

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

# 1) Generar token
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

if not token:
    print("No se pudo generar token")
    exit(1)

print(f"Token: {token[:60]}...")
print()

# 2) Visitar el nftoken URL y ver TODAS las respuestas (incluyendo redirects)
print("=== Visitando nftoken URL (siguiendo redirects) ===")
session = requests.Session()
r = session.get(
    f'https://www.netflix.com/account?nftoken={token}',
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
    allow_redirects=True, timeout=10
)

print(f"Status final: {r.status_code}")
print(f"URL final: {r.url}")
print(f"Cookies del navegador: {dict(session.cookies)}")

# Ver si hay NetflixId en las cookies de respuesta
if 'NetflixId' in session.cookies:
    print("\n>>> TOKEN FUNCIONA! NetflixId recibido como cookie!")
elif 'SecureNetflixId' in session.cookies:
    print("\n>>> TOKEN FUNCIONA! SecureNetflixId recibido!")
else:
    print("\n>>> Token NO funciono - no se recibieron cookies de sesion")
    # Mostrar todas las cookies que recibimos
    for k, v in dict(session.cookies).items():
        print(f"   Cookie: {k}={v[:40]}...")

print()

# 3) Probar con requests SIN seguir redirects para ver las respuestas intermedias
print("=== Timeline de redirects ===")
session2 = requests.Session()
r = session2.get(
    f'https://www.netflix.com/account?nftoken={token}',
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
    allow_redirects=False, timeout=10
)
print(f"1er request: Status={r.status_code} Location={r.headers.get('location','N/A')}")
print(f"   Set-Cookie: {r.headers.get('set-cookie','N/A')[:200]}")
history = []
while r.status_code in (301, 302, 303, 307, 308):
    url = r.headers.get('location')
    if not url or url in history:
        break
    history.append(url)
    r = session2.get(url, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=False, timeout=10)
    print(f"Siguiente: Status={r.status_code} URL={url}")
    sc = r.headers.get('set-cookie','')
    if sc:
        print(f"   Set-Cookie: {sc[:200]}")
