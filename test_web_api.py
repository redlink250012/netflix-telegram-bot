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

tests = [
    ('https://www.netflix.com/api/shakti/account', 'Mozilla/5.0 (Windows) Chrome/126'),
    ('https://www.netflix.com/api/account', 'Mozilla/5.0 (Windows) Chrome/126'),
    ('https://api.netflix.com/account', 'Mozilla/5.0 (Windows) Chrome/126'),
]

for url, ua in tests:
    try:
        r = requests.get(
            url,
            headers={
                'User-Agent': ua,
                'Accept': 'application/json',
                'Cookie': cookie_str,
            },
            allow_redirects=False,
            timeout=10,
            verify=False,
        )
        ct = r.headers.get('content-type', '?')
        print(url)
        print(f'  Status: {r.status_code}, Type: {ct[:30]}')
        if r.status_code == 200 and 'json' in ct:
            print(f'  Body: {r.text[:200]}')
        print()
    except Exception as e:
        print(f'{url}: ERROR {str(e)[:50]}')
