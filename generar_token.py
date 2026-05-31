from urllib.parse import quote
from netflix_checker import check_cookies

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
result = check_cookies(cookie_str)

if result['valid'] and result['token']:
    url = 'https://netflix.com/account?nftoken=' + quote(result['token'], safe='')
    with open('NETFLIX_TOKEN_URL.txt', 'w') as f:
        f.write(url)
    print('Token generado!')
    print('Link:', url)
    print('(guardado en NETFLIX_TOKEN_URL.txt)')
else:
    print('Error:', result.get('error'))
