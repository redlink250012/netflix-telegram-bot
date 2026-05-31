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
    'User-Agent': 'com.netflix.mediaclient/63884 (Linux; U; Android 13; ro;)',
    'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
}

# Probar distintos scopes que Netflix pueda aceptar
scopes = [
    'WEBVIEW_MOBILE_STREAMING',  # Este ya funciona
    'WEBVIEW_STREAMING',
    'MOBILE_STREAMING',
    'TV_STREAMING',
    'STREAMING',
    'WEB',
    'MOBILE',
    'BROWSER',
    'NONE',
]

for scope in scopes:
    payload = {
        'operationName': 'CreateAutoLoginToken',
        'variables': {'scope': scope},
        'extensions': {
            'persistedQuery': {
                'version': 102,
                'id': '76e97129-f4b5-41a0-a73c-12e674896849',
            }
        },
    }
    try:
        r = requests.post(
            'https://android13.prod.ftl.netflix.com/graphql',
            headers=headers, json=payload, verify=False, timeout=15
        )
        data = r.json()
        has_token = 'data' in data and data['data'] and 'createAutoLoginToken' in data['data']
        token = data['data']['createAutoLoginToken'] if has_token else None
        errors = data.get('errors', [])
        err_msg = errors[0].get('message', '')[:80] if errors else ''
        
        if token:
            print(f'SCOPE={scope:30s} -> TOKEN GENERADO ({len(token)} chars)')
            # Probar si funciona para web
            r2 = requests.get(
                f'https://www.netflix.com/account?nftoken={token}',
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                allow_redirects=True, timeout=10
            )
            if '/login' in r2.url.lower():
                print(f'  -> WEB: NO funciona (redirige a login)')
            else:
                print(f'  -> WEB: SI funciona!')
        else:
            print(f'SCOPE={scope:30s} -> ERROR: {err_msg}')
    except Exception as e:
        print(f'SCOPE={scope:30s} -> EXCEPTION: {str(e)[:50]}')
