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

cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())
base_headers = {
    'User-Agent': 'com.netflix.mediaclient/63884 (Linux; U; Android 13; ro;)',
    'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
}

scopes = ['', 'WEB_STREAMING', 'STREAMING', 'BROWSER', 'WEB', 'SIGN_IN', None]

for scope in scopes:
    variables = {}
    if scope is not None:
        variables['scope'] = scope
    payload = {
        'operationName': 'CreateAutoLoginToken',
        'variables': variables,
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
            headers=base_headers, json=payload, verify=False, timeout=15
        )
        data = r.json()
        token = data.get('data', {}).get('createAutoLoginToken', '')
        err = ''
        if 'errors' in data:
            err = data['errors'][0].get('message', str(data['errors'][0]))[:60]
        
        token_preview = token[:40] if token else 'NO'
        print(f'scope={scope!r:20s} token={token_preview} err={err}')
    except Exception as e:
        print(f'scope={scope!r:20s} ERROR: {str(e)[:50]}')
