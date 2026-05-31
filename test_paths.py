"""
Test: despues de nftoken, probar diferentes paths de Netflix
"""
import requests, urllib.parse, json, warnings
warnings.filterwarnings('ignore')

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
        elif '=' in line and not line.startswith('.'):
            n, v = line.split('=', 1)
            cookies[n.strip()] = v.strip()

cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())

# 1. Generate token
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
print('Token OK')

s = requests.Session()
ua = 'Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36'

# Visit nftoken
s.get(url, headers={'User-Agent': ua}, allow_redirects=True, timeout=10)
print('nftoken visitado')

# Try different paths
paths = ['/', '/browse', '/account', '/YourAccount', '/mx-en/login', '/browse/genre/839338']
for p in paths:
    r = s.get('https://www.netflix.com' + p, headers={'User-Agent': ua},
              allow_redirects=True, timeout=10)
    status = 'LOGUEADO' if '/login' not in r.url.lower() else 'Login'
    print(f'  {p:35s} -> Status={r.status_code} {status}')

# Also try with the ORIGINAL cookies (not nftoken session)
s2 = requests.Session()
ua2 = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
for name, value in cookies.items():
    s2.cookies.set(name, value, domain='.netflix.com', path='/')

# Test original cookies directly
r = s2.get('https://www.netflix.com/browse', headers={'User-Agent': ua2},
           allow_redirects=True, timeout=10)
print()
print('Con cookies ORIGINALES (desde archivo):')
print(f'  /browse: Status={r.status_code} URL={r.url[:80]}')
if '/login' not in r.url.lower():
    print('  >>> LOGUEADO con cookies originales!')
    # Get account info
    r2 = s2.get('https://www.netflix.com/account', headers={'User-Agent': ua2},
                allow_redirects=True, timeout=10)
    print(f'  /account: Status={r2.status_code} URL={r2.url[:80]}')
    import re
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', r2.text)
    emails = [e for e in emails if not any(x in e for x in ['nflxext', '.js', '.css', '.png', '.jpg'])]
    if emails:
        print(f'  Email encontrado: {emails[0]}')
else:
    print('  -> Login page (cookies originales no funcionan en web directo)')
