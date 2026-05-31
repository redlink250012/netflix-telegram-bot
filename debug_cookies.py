import httpx, re

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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9',
    'Cookie': cookie_str,
}

with httpx.Client(headers=headers, follow_redirects=True, timeout=20, verify=False, http2=True) as client:
    r = client.get('https://www.netflix.com/YourAccount')
    html = r.text

    checks = {
        'sign in': 'sign in' in html.lower(),
        'login': 'login' in html.lower(),
        'Account': 'Account' in html,
        'Sign Out': 'Sign Out' in html,
        'logout': 'logout' in html.lower(),
    }
    for k, v in checks.items():
        print(f'  {k}: {v}')

    emails = set(re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', html))
    emails = {e for e in emails if not any(x in e for x in ['nflxext', 'netflix.com', '.js', '.css', 'assets'])}
    if emails:
        print(f'Emails: {emails}')

    m = re.search(r'"email"\s*:\s*"([^"]+)"', html)
    if m: print(f'Email field: {m.group(1)}')
    m = re.search(r'"planName"\s*:\s*"([^"]+)"', html)
    if m: print(f'Plan: {m.group(1)}')
    m = re.search(r'"country"\s*:\s*"([A-Z]{2})"', html)
    if m: print(f'Country: {m.group(1)}')

    print(f'\nSize: {len(html)} chars')
    print(f'Final URL: {r.url}')
