"""
Netflix API Exploration Part 4 - Find web-compatible token mechanisms
"""
import requests, json, urllib.parse, re, base64, time
import warnings
warnings.filterwarnings("ignore")
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

COOKIES_FILE = "netflix_cookies.txt"

def load_cookies():
    cookies = {}
    with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '.netflix.com' in line:
                parts = line.split('\t')
                if len(parts) >= 7:
                    cookies[parts[5].strip()] = parts[6].strip()
    return cookies

cookies = load_cookies()
cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())

ANDROID_UA = "com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)"
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
EP = "https://android13.prod.ftl.netflix.com/graphql"

base_headers = {
    'User-Agent': ANDROID_UA,
    'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
}

def gen_token(headers_override=None):
    h = dict(base_headers)
    if headers_override:
        h.update(headers_override)
    r = requests.post(EP, headers=h, json={
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
# TEST 1: Try to discover web-specific persisted queries
# ============================================================
print("="*70)
print("TEST 1: DISCOVER WEB-SPECIFIC PERSISTED QUERIES")
print("="*70)

# Common Netflix web GraphQL query hashes (from research)
# These are sha256 hashes that might correspond to web queries
web_query_hashes = [
    # These are commonly seen in Netflix web traffic
    "8g6VUr7TGs0xlL6r1LXlVQ2rrBu1SP2LOOhZPpOhlWk=",  # Common web query
    "2VlT1J6yOB9QkRNG7Gfq3p3hVlY3OXHzWQQbLkBVhNk=",  # Another common one
    "nQYqZP-KuaLMaN8w6d0M0byoXjFTiG3kF3x7Vh3BZ8Y=",  # Yet another
]

# Test different endpoints with web headers for different queries
web_endpoints = [
    "https://www.netflix.com/graphql",
    "https://www.netflix.com/api/graphql",
]

web_headers = {
    'User-Agent': BROWSER_UA,
    'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
    'Origin': 'https://www.netflix.com',
}

# First, let's check if the web endpoint has the SAME CreateAutoLoginToken query
for ep in web_endpoints[:1]:
    print(f"\n-- Testing {ep} --")
    for qhash in web_query_hashes:
        payload = {
            "operationName": "CreateAutoLoginToken",
            "variables": {"scope": "WEBVIEW_MOBILE_STREAMING"},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": qhash
                }
            }
        }
        r = requests.post(ep, headers=web_headers, json=payload, verify=False, timeout=10)
        print(f"  hash={qhash[:35]}... -> HTTP {r.status_code} | {r.text[:200]}")

# Also try with just the web query format (version 1 with id as string)
print("\n-- Trying web format queries --")
web_test_queries = [
    ("CreateAutoLoginToken", "WEBVIEW_MOBILE_STREAMING", "76e97129-f4b5-41a0-a73c-12e674896849", 102),
    ("CreateAutoLoginToken", "WEBVIEW_MOBILE_STREAMING", "76e97129-f4b5-41a0-a73c-12e674896849", 1),
    ("CreateAutoLoginToken", "WEBVIEW_MOBILE_STREAMING", "CreateAutoLoginToken", 1),
    ("CreateAutoLoginToken", "WEBVIEW_MOBILE_STREAMING", "createAutoLoginToken", 1),
]

for op, scope, qid, ver in web_test_queries:
    for ep in web_endpoints:
        payload = {
            "operationName": op,
            "variables": {"scope": scope},
            "extensions": {
                "persistedQuery": {
                    "version": ver,
                    "id": qid
                }
            }
        }
        try:
            r = requests.post(ep, headers=web_headers, json=payload, verify=False, timeout=10)
            data = r.json() if r.text.strip() else {}
            token = data.get('data', {}).get('createAutoLoginToken', '')
            err = data.get('errors', [])
            err_msg = err[0].get('message', '')[:60] if err else ''
            token_preview = token[:40] if token else 'NO'
            print(f"  {ep[8:30]:25s} ver={ver} id={qid[:30]:30s} -> token={token_preview} {err_msg}")
        except Exception as e:
            print(f"  ERROR: {str(e)[:60]}")

# ============================================================
# TEST 2: More exhaustive scope testing via enum in raw query
# ============================================================
print("\n" + "="*70)
print("TEST 2: RAW ENUM SCOPE VALUES IN PERSISTED QUERY")
print("="*70)

# The persisted query uses the enum on the server side, but in JSON we pass string
# Let me try different possible enum values - maybe there's a WEB-specific one
extended_scopes = [
    "WEBVIEW_MOBILE_STREAMING",   # Known working
    "WEBVIEW_STREAMING",
    "MOBILE_STREAMING",
    "TV_STREAMING",
    "STREAMING",
    "BROWSER",
    "WEB_STREAMING",
    "ANDROID_STREAMING",
    "IOS_STREAMING",
    "DESKTOP_STREAMING",
    "TV",
    "MOBILE",
    "WEB",
    "ANDROID",
    "IOS",
    "DESKTOP",
    "WEBVIEW",
    "NONE",
    "ALL",
    "PARTNER_ACTIVATION",
    "DEVICE_ACTIVATION",
    "PINLESS_ACTIVATION",
    "USER_ACTIVATION",
    "WEB_AUTH",
    "AUTH",
    "SESSION",
    "LOGIN",
    "SIGNIN",
    "BROWSER_AUTH",
    "AUTO_LOGIN_WEB",
    "AUTO_LOGIN_MOBILE",
    "AUTO_LOGIN_TV",
]

for scope in extended_scopes:
    payload = {
        "operationName": "CreateAutoLoginToken",
        "variables": {"scope": scope},
        "extensions": {
            "persistedQuery": {
                "version": 102,
                "id": "76e97129-f4b5-41a0-a73c-12e674896849"
            }
        }
    }
    try:
        r = requests.post(EP, headers=base_headers, json=payload, verify=False, timeout=10)
        data = r.json() if r.text.strip() else {}
        token = data.get('data', {}).get('createAutoLoginToken', '')
        err = data.get('errors', [])
        err_msg = err[0].get('message', '')[:80] if err else ''
        if token:
            print(f"  >> SCOPE={scope:35s} -> TOKEN ({len(token)} chars)")
        else:
            print(f"     {scope:35s} -> {err_msg}")
    except Exception as e:
        print(f"     {scope:35s} -> EXCEPTION: {str(e)[:50]}")

# ============================================================
# TEST 3: Try the nftoken with cookies from original session
# ============================================================
print("\n" + "="*70)
print("TEST 3: NFTOKEN WITH ORIGINAL COOKIES (combining)")
print("="*70)

token3 = gen_token()

# The theory: maybe nftoken works when combined with the ORIGINAL cookies
# Try: send original cookies PLUS the nftoken in URL
s = requests.Session()
s.cookies.update(cookies)  # Set original cookies

r = s.get(
    f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token3, safe='')}",
    headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
    allow_redirects=True, timeout=10
)
print(f"  With original cookies: url={r.url[:70]} login={'YES' if '/login' in r.url.lower() else 'NO'}")
print(f"  NetflixId: {'YES' if s.cookies.get('NetflixId') else 'NO'}")

# What if we DON'T include any cookies at all on the nftoken request?
# The server should set fresh cookies from the nftoken
s2 = requests.Session()
# Specifically clear any cookies
s2.cookies.clear()

r2 = s2.get(
    f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token3, safe='')}",
    headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
    allow_redirects=False, timeout=10
)
print(f"\n  Without ANY cookies: status={r2.status_code} loc={r2.headers.get('location','')[:60]}")
print(f"  Set-Cookie: {r2.headers.get('set-cookie','')[:200]}")
print(f"  NetflixId in session: {'YES' if s2.cookies.get('NetflixId') else 'NO'}")

# Follow redirects manually
cookies_from_token = dict(s2.cookies)
s3 = requests.Session()
# Use the cookies that were set by the nftoken
for name, value in cookies_from_token.items():
    s3.cookies.set(name, value, domain='.netflix.com', path='/')

r3 = s3.get(
    "https://www.netflix.com/account",
    headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
    allow_redirects=True, timeout=10
)
print(f"\n  With ONLY token cookies: url={r3.url[:70]} login={'YES' if '/login' in r3.url.lower() else 'NO'}")

# ============================================================
# TEST 4: Try the nftoken consumption with X-Forwarded-For etc
# ============================================================
print("\n" + "="*70)
print("TEST 4: NFTOKEN WITH APP-SPECIFIC HEADERS")
print("="*70)

token4 = gen_token()

header_variations = [
    # (name, headers_dict)
    ("WebView standard", {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; M2007J3SG) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36',
        'X-Requested-With': 'com.netflix.mediaclient',
        'Accept': 'text/html,*/*',
    }),
    ("Android Chrome", {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; M2007J3SG) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,*/*',
    }),
    ("Netflix App UA", {
        'User-Agent': 'com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)',
        'Accept': 'text/html,*/*',
    }),
    ("Custom origin/referer", {
        'User-Agent': BROWSER_UA,
        'Origin': 'https://android13.prod.ftl.netflix.com',
        'Referer': 'https://android13.prod.ftl.netflix.com/',
        'Accept': 'text/html,*/*',
    }),
]

for label, custom_headers in header_variations:
    s = requests.Session()
    url = f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token4, safe='')}"
    r = s.get(url, headers=custom_headers, allow_redirects=True, timeout=10)
    nf = s.cookies.get('NetflixId', '')
    login = '/login' in r.url.lower()
    print(f"  [{label:25s}] login={login} NetflixId={'YES' if nf else 'NO'}")

# ============================================================
# TEST 5: Try to exchange the nftoken at an API endpoint
# ============================================================
print("\n" + "="*70)
print("TEST 5: NFTOKEN EXCHANGE AT API ENDPOINTS")
print("="*70)

token5 = gen_token()

api_endpoints = [
    "https://www.netflix.com/api/account",
    "https://www.netflix.com/api/session",
    "https://www.netflix.com/api/auth",
    "https://www.netflix.com/api/login",
    "https://www.netflix.com/api/autologin",
    "https://www.netflix.com/api/user",
]

for ep in api_endpoints:
    # POST with token as Bearer
    r = requests.post(ep, 
        headers={
            'User-Agent': BROWSER_UA,
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token5}',
        },
        json={},
        allow_redirects=False, verify=False, timeout=10)
    print(f"  POST {ep[8:]:45s} Bearer -> HTTP {r.status_code} | {r.text[:150]}")
    
    # POST with token in body
    r2 = requests.post(ep,
        headers={
            'User-Agent': BROWSER_UA,
            'Content-Type': 'application/json',
        },
        json={"nftoken": token5},
        allow_redirects=False, verify=False, timeout=10)
    print(f"  POST {ep[8:]:45s} JSON body -> HTTP {r2.status_code} | {r2.text[:150]}")

# ============================================================
# TEST 6: Try extracting the token info (decoding more)
# ============================================================
print("\n" + "="*70)
print("TEST 6: NFTOKEN STRUCTURE ANALYSIS")
print("="*70)

token6 = gen_token()
print(f"Token length: {len(token6)} chars")

# Base64 decode attempt
try:
    padded = token6 + '=' * ((4 - len(token6) % 4) % 4)
    raw = base64.b64decode(padded)
    print(f"Decoded size: {len(raw)} bytes")
    print(f"Hex prefix: {raw[:20].hex()}")
    print(f"Raw prefix: {raw[:50]}")
    
    # The token seems to start with Bgj (which is 0x06 0x08 0xfa in base64 = bytes \x06\x08\xfa)
    # First 3 bytes: \x06\x08\xfa or similar
    # Bgj6uevcAxL+ in base64 decodes to: \x06\x08\xfa\xb9\xeb\xdc\x03\x12\xfe
    # This looks like a binary protocol (maybe protobuf?)
    
    # Parse further - 9 byte fixed header?
    header = raw[:9]
    print(f"Header: {header.hex()}")
    print(f"Header bytes: {[b for b in header]}")
except Exception as e:
    print(f"Decode error: {e}")

# Check if token is url-safe base64
token_std = token6.replace('+', '-').replace('/', '_').rstrip('=')
try:
    raw2 = base64.urlsafe_b64decode(token_std + '==')
    print(f"\nURL-safe decode: {len(raw2)} bytes")
except:
    print("\nNot URL-safe base64 either")

# Check if Bgj prefix is always present and what it means
print(f"\nToken always starts with 'Bgj': {token6.startswith('Bgj')}")
print(f"Token prefix pattern: {token6[:5]}")

# ============================================================
# TEST 7: Try the token on the native netflix API pattern
# ============================================================
print("\n" + "="*70)
print("TEST 7: TRY NFTOKEN ON NATIVE NETFLIX ENDPOINTS")
print("="*70)

# Netflix native apps might use a different host for token consumption
native_hosts = [
    ("https://android13.prod.ftl.netflix.com", ANDROID_UA),
    ("https://android.prod.ftl.netflix.com", ANDROID_UA),
    ("https://ios.prod.ftl.netflix.com", ANDROID_UA),
]

token7 = gen_token()

for host, ua in native_hosts:
    # Try consuming the token on the native endpoint
    payload = {
        "operationName": "ConsumeAutoLoginToken",
        "variables": {"token": token7},
        "extensions": {
            "persistedQuery": {
                "version": 102,
                "id": "76e97129-f4b5-41a0-a73c-12e674896849"
            }
        }
    }
    try:
        r = requests.post(f"{host}/graphql", headers=base_headers, json=payload, verify=False, timeout=10)
        print(f"  ConsumeAutoLoginToken on {host[8:30]:25s} -> HTTP {r.status_code} | {r.text[:200]}")
    except Exception as e:
        print(f"  {host[8:30]:25s} -> ERROR: {str(e)[:50]}")

    # Try redcemtion
    payload2 = {
        "operationName": "RedeemAutoLoginToken",
        "variables": {"token": token7},
        "extensions": {
            "persistedQuery": {
                "version": 102,
                "id": "76e97129-f4b5-41a0-a73c-12e674896849"
            }
        }
    }
    try:
        r = requests.post(f"{host}/graphql", headers=base_headers, json=payload2, verify=False, timeout=10)
        print(f"  RedeemAutoLoginToken on {host[8:30]:25s} -> HTTP {r.status_code} | {r.text[:200]}")
    except Exception as e:
        print(f"  {host[8:30]:25s} -> ERROR: {str(e)[:50]}")

# ============================================================
# TEST 8: Try with different nftoken parameter names
# ============================================================
print("\n" + "="*70)
print("TEST 8: ALTERNATIVE NFTOKEN PARAMETER NAMES")
print("="*70)

token8 = gen_token()
param_names = ["nftoken", "token", "access_token", "autologin", "auth", "t", "code", "key"]

for param in param_names:
    s = requests.Session()
    url = f"https://www.netflix.com/account?{param}={urllib.parse.quote(token8, safe='')}"
    r = s.get(url, headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
              allow_redirects=False, timeout=10)
    loc = r.headers.get('location', '')
    nf_cookie = s.cookies.get('NetflixId', '')
    print(f"  ?{param:15s} status={r.status_code} loc={loc[:50]} NetflixId={'YES' if nf_cookie else 'NO'}")

# ============================================================
# TEST 9: What if we need to request www.netflix.com token specifically?
# ============================================================
print("\n" + "="*70)
print("TEST 9: REQUEST TOKEN FROM WEB ENDPOINT WITH BROWSER HEADERS")
print("="*70)

web_headers = {
    'User-Agent': BROWSER_UA,
    'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
    'Origin': 'https://www.netflix.com',
}

web_variations = [
    # Try different version/id combos on web endpoint
    (EP, ANDROID_UA),
    ("https://www.netflix.com/graphql", BROWSER_UA),
    ("https://www.netflix.com/graphql", ANDROID_UA),
]

for ep, ua in web_variations:
    h = dict(web_headers)
    h['User-Agent'] = ua
    r = requests.post(ep, headers=h, json={
        "operationName": "CreateAutoLoginToken",
        "variables": {"scope": "WEBVIEW_MOBILE_STREAMING"},
        "extensions": {
            "persistedQuery": {
                "version": 102,
                "id": "76e97129-f4b5-41a0-a73c-12e674896849"
            }
        }
    }, verify=False, timeout=10)
    data = r.json() if r.text.strip() else {}
    token = data.get('data', {}).get('createAutoLoginToken', '')
    if token:
        # Test this token in browser
        s = requests.Session()
        url = f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token, safe='')}"
        rr = s.get(url, headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
                   allow_redirects=True, timeout=10)
        login = '/login' in rr.url.lower()
        print(f"  Token from {ep[8:30]:25s} ua={ua[:25]:25s} -> browser login={login} | token={token[:30]}...")

print("\n" + "="*70)
print("EXPLORATION PART 4 COMPLETE")
print("="*70)
