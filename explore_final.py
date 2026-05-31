"""
Netflix API Exploration - FINAL ROUND
Testing creative approaches for cross-platform token
"""
import requests, json, urllib.parse, re, base64
import warnings
warnings.filterwarnings("ignore")
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

COOKIES_FILE = "netflix_cookies.txt"

def load_cookies_dict():
    c = {}
    with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '.netflix.com' in line:
                parts = line.split('\t')
                if len(parts) >= 7:
                    c[parts[5].strip()] = parts[6].strip()
    return c

cookies = load_cookies_dict()
cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())

ANDROID_UA = "com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)"
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
EP = "https://android13.prod.ftl.netflix.com/graphql"

def gen_token():
    r = requests.post(EP, headers={
        'User-Agent': ANDROID_UA,
        'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
        'Content-Type': 'application/json',
        'Cookie': cookie_str,
    }, json={
        "operationName": "CreateAutoLoginToken",
        "variables": {"scope": "WEBVIEW_MOBILE_STREAMING"},
        "extensions": {
            "persistedQuery": {
                "version": 102,
                "id": "76e97129-f4b5-41a0-a73c-12e674896849"
            }
        }
    }, verify=False, timeout=10)
    return r.json()['data']['createAutoLoginToken']

# ============================================================
# TEST 1: Consume token at FTL endpoint (not www.netflix.com)
# Maybe the token needs to be consumed at the SAME endpoint?
# ============================================================
print("="*70)
print("TEST 1: CONSUME TOKEN AT FTL ENDPOINT")
print("="*70)

token = gen_token()

# Try sending the token as a mutation parameter to consume it
consume_operations = [
    "consumeAutoLoginToken",
    "redeemAutoLoginToken", 
    "exchangeAutoLoginToken",
    "verifyAutoLoginToken",
    "activateAutoLoginToken",
    "useAutoLoginToken",
    "applyAutoLoginToken",
    "validateAutoLoginToken",
    "loginWithToken",
    "authenticateWithToken",
]

for op in consume_operations:
    payload = {
        "operationName": op,
        "variables": {"token": token},
        "extensions": {
            "persistedQuery": {
                "version": 102,
                "id": "76e97129-f4b5-41a0-a73c-12e674896849"
            }
        }
    }
    try:
        r = requests.post(EP, headers={
            'User-Agent': ANDROID_UA,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }, json=payload, verify=False, timeout=10)
        data = r.json() if r.text.strip() else {}
        err = data.get('errors', [{}])
        err_msg = err[0].get('message', '')[:80] if err else ''
        print(f"  {op:30s} -> HTTP {r.status_code} | {err_msg}")
    except Exception as e:
        print(f"  {op:30s} -> ERROR: {str(e)[:50]}")

# ============================================================
# TEST 2: Try the www.netflix.com GraphQL with SHA256 hash
# Maybe web endpoint uses sha256Hash instead of UUID id
# ============================================================
print("\n" + "="*70)
print("TEST 2: SHA256 HASH ON WEB ENDPOINT")
print("="*70)

# The web endpoint responded "sha256Hash must be present"
# Let's compute the SHA256 of the query
import hashlib

query_body = """
mutation CreateAutoLoginToken($scope: TokenScope!) {
    createAutoLoginToken(scope: $scope)
}
"""
sha256_hash = hashlib.sha256(query_body.encode()).digest()
b64_hash = base64.b64encode(sha256_hash).decode()
print(f"  SHA256 of query: {b64_hash}")

# Try with this hash
web_ep = "https://www.netflix.com/graphql"
payload = {
    "operationName": "CreateAutoLoginToken",
    "variables": {"scope": "WEBVIEW_MOBILE_STREAMING"},
    "extensions": {
        "persistedQuery": {
            "version": 1,
            "sha256Hash": b64_hash
        }
    }
}
r = requests.post(web_ep, headers={
    'User-Agent': BROWSER_UA,
    'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
}, json=payload, verify=False, timeout=10)
print(f"  SHA256 attempt: HTTP {r.status_code} | {r.text[:300]}")

# Try without variables (inline)
query_inline = "mutation { createAutoLoginToken(scope: WEBVIEW_MOBILE_STREAMING) }"
sha256_inline = hashlib.sha256(query_inline.encode()).digest()
b64_inline = base64.b64encode(sha256_inline).decode()

payload2 = {
    "operationName": "CreateAutoLoginToken",
    "variables": {},
    "extensions": {
        "persistedQuery": {
            "version": 1,
            "sha256Hash": b64_inline
        }
    }
}
r2 = requests.post(web_ep, headers={
    'User-Agent': BROWSER_UA,
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
}, json=payload2, verify=False, timeout=10)
print(f"  SHA256 inline: HTTP {r2.status_code} | {r2.text[:300]}")

# ============================================================
# TEST 3: Try the iOS endpoint maybe has different scope
# ============================================================
print("\n" + "="*70)
print("TEST 3: IOS ENDPOINT WITH DIFFERENT ENDPOINT-SPECIFIC QUERY")
print("="*70)

ios_ep = "https://ios.prod.ftl.netflix.com/graphql"
# Maybe iOS has a different query for web tokens?
r = requests.post(ios_ep, headers={
    'User-Agent': 'com.netflix.mediaclient/63884 (iOS; U; CPU iPhone OS 16_0)',
    'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
}, json={
    "operationName": "CreateAutoLoginToken",
    "variables": {"scope": "WEBVIEW_MOBILE_STREAMING"},
    "extensions": {
        "persistedQuery": {
            "version": 102,
            "id": "76e97129-f4b5-41a0-a73c-12e674896849"
        }
    }
}, verify=False, timeout=10)
data = r.json()
t = data.get('data', {}).get('createAutoLoginToken', '')
if t:
    print(f"  iOS token: {t[:40]}... (same format)")

# ============================================================
# TEST 4: What if we need to include the token in the Cookie header?
# Like: Cookie: nftoken=TOKEN
# ============================================================
print("\n" + "="*70)
print("TEST 4: TOKEN IN COOKIE HEADER")
print("="*70)

token4 = gen_token()

# Try sending nftoken as a cookie
s = requests.Session()
r = s.get("https://www.netflix.com/account", headers={
    'User-Agent': BROWSER_UA,
    'Cookie': f'nftoken={urllib.parse.quote(token4, safe="")}',
}, allow_redirects=True, timeout=10)
print(f"  nftoken as cookie: {r.status_code} {r.url[:60]} login={'YES' if '/login' in r.url.lower() else 'NO'}")
nf = None
for c in s.cookies:
    if c.name == 'NetflixId':
        nf = c.value[:30]
print(f"  NetflixId: {nf}")

# ============================================================
# TEST 5: Try with specific locale in the URL (no redirect)
# ============================================================
print("\n" + "="*70)
print("TEST 5: NFTOKEN WITH LOCALE IN URL")
print("="*70)

token5 = gen_token()

locale_urls = [
    f"https://www.netflix.com/mx-en/account?nftoken={urllib.parse.quote(token5, safe='')}",
    f"https://www.netflix.com/us-en/account?nftoken={urllib.parse.quote(token5, safe='')}",
    f"https://www.netflix.com/ar-es/account?nftoken={urllib.parse.quote(token5, safe='')}",
]

for url in locale_urls:
    s = requests.Session()
    r = s.get(url, headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
              allow_redirects=True, timeout=10)
    nf_c = None
    for c in s.cookies:
        if c.name == 'NetflixId':
            nf_c = c.value[:30]
    print(f"  url={url[8:60]:55s} -> login={'YES' if '/login' in r.url.lower() else 'NO'} NetflixId={nf_c}")

# ============================================================
# TEST 6: Try to capture the FULL response from nftoken page
# What does the /account page with nftoken param return (302)?
# ============================================================
print("\n" + "="*70)
print("TEST 6: RESPONSE HEADERS FROM NFTOKEN CONSUMPTION")
print("="*70)

token6 = gen_token()
s = requests.Session()
r = s.get(
    f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token6, safe='')}",
    headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
    allow_redirects=False, timeout=10
)
print(f"  Status: {r.status_code}")
print(f"  All headers:")
for k, v in r.headers.items():
    print(f"    {k}: {v[:200]}")

# ============================================================
# TEST 7: What if we need to include gsid cookie?
# gsid (guest session id) might be required alongside nftoken
# ============================================================
print("\n" + "="*70)
print("TEST 7: NFTOKEN WITH GUEST SESSION (gsid)")
print("="*70)

# First get a guest session
s_guest = requests.Session()
r_guest = s_guest.get("https://www.netflix.com/account", headers={
    'User-Agent': BROWSER_UA,
}, allow_redirects=True, timeout=10)

gsid = None
for c in s_guest.cookies:
    if c.name == 'gsid':
        gsid = c.value
if gsid:
    print(f"  Guest gsid: {gsid[:20]}...")
    
    # Now try nftoken with this guest session
    token7a = gen_token()
    s2 = requests.Session()
    s2.cookies.set('gsid', gsid, domain='.netflix.com', path='/')
    r2 = s2.get(
        f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token7a, safe='')}",
        headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
        allow_redirects=True, timeout=10
    )
    print(f"  With gsid: {r2.status_code} {r2.url[:60]} login={'YES' if '/login' in r2.url.lower() else 'NO'}")

# ============================================================
# TEST 8: Final attempt - try to call the token endpoint 
# with HTTP/2 and android native headers exactly like the app
# ============================================================
print("\n" + "="*70)
print("TEST 8: EXACT ANDROID APP BEHAVIOR SIMULATION")
print("="*70)

token8 = gen_token()

# The Android app would:
# 1. Create a WebView
# 2. Set specific headers
# 3. Load the nftoken URL
# Let's try with ALL the headers an Android app/WebView would send

exact_android_headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; M2007J3SG) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/126.0.0.0 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'X-Requested-With': 'com.netflix.mediaclient',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-User': '?1',
    'Sec-Fetch-Dest': 'document',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

s = requests.Session()
# Clear any cookies
s.cookies.clear()
r = s.get(
    f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token8, safe='')}",
    headers=exact_android_headers,
    allow_redirects=True, timeout=10
)
print(f"  Android WebView emulation:")
print(f"    Status: {r.status_code}")
print(f"    URL: {r.url[:70]}")
print(f"    Login: {'YES' if '/login' in r.url.lower() else 'NO'}")
nf_c = None
for c in s.cookies:
    if c.name == 'NetflixId':
        nf_c = c.value[:30]
print(f"    NetflixId: {nf_c}")

# Check for profile page indicators
has_avatar = 'avatar' in r.text.lower()
has_profile_select = 'profile' in r.text.lower() and 'select' in r.text.lower()
has_browse = '/browse' in r.text.lower()
print(f"    Has avatar: {has_avatar}")
print(f"    Has profile select: {has_profile_select}")

# If failed, try one more: maybe the token needs to NOT be URL-encoded
# on Android (since Android WebView might handle it differently)
s2 = requests.Session()
s2.cookies.clear()
r2 = s2.get(
    f"https://www.netflix.com/account?nftoken={token8}",
    headers=exact_android_headers,
    allow_redirects=True, timeout=10
)
print(f"\n  Android WebView (raw token, no URL encoding):")
print(f"    Status: {r2.status_code}")
print(f"    URL: {r2.url[:70]}")
print(f"    Login: {'YES' if '/login' in r2.url.lower() else 'NO'}")
nf_c2 = None
for c in s2.cookies:
    if c.name == 'NetflixId':
        nf_c2 = c.value[:30]
print(f"    NetflixId: {nf_c2}")

print("\n" + "="*70)
print("ALL EXPLORATION COMPLETE")
print("="*70)
