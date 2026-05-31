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
base_headers = {
    'User-Agent': 'com.netflix.mediaclient/63884 (Linux; U; Android 13; ro;)',
    'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
}

# Test sin scope
payload = {
    'operationName': 'CreateAutoLoginToken',
    'variables': {},
    'extensions': {
        'persistedQuery': {
            'version': 102,
            'id': '76e97129-f4b5-41a0-a73c-12e674896849',
        }
    },
}

r = requests.post(
    'https://android13.prod.ftl.netflix.com/graphql',
    headers=base_headers, json=payload, verify=False, timeout=15
)

print('Status:', r.status_code)
print('Content-Type:', r.headers.get('content-type'))
body = r.text[:1000]
print('Body:', repr(body))
