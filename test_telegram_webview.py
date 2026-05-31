"""
Test: Telegram WebView UA + nftoken redirect
Simula el comportamiento de Telegram Mini App en Android
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
    'Accept': 'application/json',
    'Content-Type': 'application/json',
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

# 2. Test with Telegram-like WebView UA
s = requests.Session()
webview_ua = 'Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.134 Mobile Safari/537.36'

r = s.get(url, headers={'User-Agent': webview_ua}, allow_redirects=False, timeout=10)
print('1) nftoken redirect=false: Status=' + str(r.status_code))
for h in ['Set-Cookie', 'Location']:
    if h in r.headers:
        val = str(r.headers[h])[:120]
        print('   ' + h + ': ' + val)

nf = s.cookies.get('NetflixId', 'NO')
snf = s.cookies.get('SecureNetflixId', 'NO')
print('   NetflixId: ' + (nf[:50] if nf != 'NO' else 'NO'))
print('   SecureNetflixId: ' + (snf[:50] if snf != 'NO' else 'NO'))

# Follow redirect with same session
r2 = s.get(url, headers={'User-Agent': webview_ua}, allow_redirects=True, timeout=10)
print('2) final after redirect: URL=' + str(r2.url)[:80] + ' Status=' + str(r2.status_code))

# Now try /browse with the cookies
r3 = s.get('https://www.netflix.com/browse',
           headers={'User-Agent': webview_ua}, allow_redirects=True, timeout=10)
print('3) /browse: URL=' + str(r3.url)[:80] + ' Status=' + str(r3.status_code))
if '/login' not in r3.url.lower():
    print('   >>> LOGUEADO!')
else:
    print('   -> Login page')

# Try with X-Requested-With header (Telegram WebView style)
s2 = requests.Session()
headers2 = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/126.0.6478.134 Mobile Safari/537.36',
    'X-Requested-With': 'org.telegram.messenger',
}
r4 = s2.get(url, headers=headers2, allow_redirects=False, timeout=10)
print('4) Telegram WebView UA: Status=' + str(r4.status_code))
nf2 = s2.cookies.get('NetflixId', 'NO')
print('   NetflixId: ' + (nf2[:50] if nf2 != 'NO' else 'NO'))
if nf2 != 'NO':
    s2.get('https://www.netflix.com/browse', headers=headers2, allow_redirects=True, timeout=10)
    r5 = s2.get('https://www.netflix.com/browse', headers=headers2, allow_redirects=True, timeout=10)
    print('   /browse: URL=' + str(r5.url)[:80])
    if '/login' not in r5.url.lower():
        print('   >>> LOGUEADO con Telegram UA!')
    else:
        print('   -> Login page')
