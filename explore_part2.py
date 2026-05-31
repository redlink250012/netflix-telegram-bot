"""
Netflix API Exploration Part 2 - Deep dive based on Part 1 findings
"""
import requests, json, urllib.parse, re, base64
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
WEBVIEW_UA = "Mozilla/5.0 (Linux; Android 13; M2007J3SG) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"
EP = "https://android13.prod.ftl.netflix.com/graphql"

base_headers = {
    'User-Agent': ANDROID_UA,
    'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
}

# ============================================================
# TEST 1: Raw GraphQL with enum values (no quotes on enum)
# ============================================================
print("="*70)
print("TEST 1: RAW GRAPHQL WITH ENUM VALUES")
print("="*70)

# The scope is a TokenScope enum - passed without quotes in GraphQL
# In JSON, we must pass it as a string still but the query syntax uses enum
enum_scopes = [
    "WEBVIEW_MOBILE_STREAMING",
    "WEBVIEW_STREAMING",
    "MOBILE_STREAMING",
    "TV_STREAMING",
    "STREAMING",
    "WEB_STREAMING",
    "BROWSER",
    "WEB",
    "MOBILE",
    "TV",
    "ANDROID",
    "IOS",
    "DESKTOP",
    "WEBVIEW",
]

# First, let's try to discover the enum values via a __type query
print("\n-- Trying to discover TokenScope enum values --")
introspect_enum = {
    "query": """
    query {
        __type(name: "TokenScope") {
            name
            kind
            enumValues {
                name
            }
        }
    }
    """
}
r = requests.post(EP, headers=base_headers, json=introspect_enum, verify=False, timeout=10)
print(f"TokenScope introspection: {r.text[:500]}")

# Try to get ALL types
introspect_all = {
    "query": """
    query {
        __schema {
            types {
                name
                kind
                enumValues {
                    name
                }
            }
        }
    }
    """
}
r2 = requests.post(EP, headers=base_headers, json=introspect_all, verify=False, timeout=10)
# Filter for enum types
try:
    data = r2.json()
    if 'errors' not in data:
        types = data.get('data', {}).get('__schema', {}).get('types', [])
        enum_types = [t for t in types if t.get('kind') == 'ENUM']
        print(f"\nFound {len(enum_types)} enum types:")
        for et in enum_types:
            values = [ev['name'] for ev in (et.get('enumValues') or [])]
            print(f"  {et['name']}: {values}")
    else:
        print(f"Schema query blocked: {data['errors'][0]['message'][:100]}")
except Exception as e:
    print(f"Parse error: {e}")
    print(f"Raw: {r2.text[:300]}")

# Try different enum values using persisted query
print("\n-- Testing different enum values via persisted query --")
persist_base = {
    "operationName": "CreateAutoLoginToken",
    "extensions": {
        "persistedQuery": {
            "version": 102,
            "id": "76e97129-f4b5-41a0-a73c-12e674896849"
        }
    }
}

for scope_val in enum_scopes:
    try:
        payload = dict(persist_base)
        payload["variables"] = {"scope": scope_val}
        r = requests.post(EP, headers=base_headers, json=payload, verify=False, timeout=10)
        data = r.json() if r.text.strip() else {}
        
        # Check both locations for error
        err = None
        if 'errors' in data and data['errors']:
            err = data['errors'][0].get('message', '')[:80]
        elif 'data' in data and data['data'] is None:
            continue
        
        token = data.get('data', {}).get('createAutoLoginToken', '')
        if token:
            print(f"  [{scope_val:30s}] TOKEN! ({len(token)} chars)")
        else:
            print(f"  [{scope_val:30s}] err: {err}")
    except Exception as e:
        print(f"  [{scope_val:30s}] EXCEPTION: {str(e)[:50]}")

# ============================================================
# TEST 2: Try different mutations that might exist
# ============================================================
print("\n" + "="*70)
print("TEST 2: FINDING OTHER AUTH MUTATIONS VIA OPERATION NAMES")
print("="*70)

# Try as raw queries (if we can figure out the schema)
# First, let's try mutations with different casing/names
mutation_names = [
    "createAutoLoginToken",
    "createAutoLoginTokenBrowser",
    "createAutoLoginTokenWeb",
    "createSessionToken",
    "createWebSession",
    "createBrowserSession",
    "generateAutoLoginToken",
    "nftoken",
]

base_mutation = """
mutation {
    %s(scope: WEBVIEW_MOBILE_STREAMING)
}
"""

for m_name in mutation_names:
    try:
        query_text = base_mutation % m_name
        r = requests.post(EP, headers=base_headers, json={
            "query": query_text,
            "variables": {}
        }, verify=False, timeout=10)
        data = r.json() if r.text.strip() else {}
        err = data.get('errors', [])
        err_msg = err[0].get('message', '')[:80] if err else ''
        has_data = 'data' in data and data['data'] is not None
        # Check if the error is about unknown field (meaning it doesn't exist)
        # vs argument type issues (meaning it DOES exist but params are wrong)
        print(f"  {m_name:35s} -> HTTP {r.status_code} | has_data={has_data} | {err_msg}")
    except Exception as e:
        print(f"  {m_name:35s} -> ERROR: {str(e)[:50]}")

# ============================================================
# TEST 3: Test nftoken with Android WebView headers
# ============================================================
print("\n" + "="*70)
print("TEST 3: NFTOKEN WITH WEBVIEW / APP HEADERS")
print("="*70)

# Get a fresh token
r = requests.post(EP, headers=base_headers, json={
    "operationName": "CreateAutoLoginToken",
    "variables": {"scope": "WEBVIEW_MOBILE_STREAMING"},
    "extensions": {
        "persistedQuery": {
            "version": 102,
            "id": "76e97129-f4b5-41a0-a73c-12e674896849"
        }
    }
}, verify=False, timeout=10)
token = r.json()['data']['createAutoLoginToken']

# Test different header combinations for nftoken consumption
test_configs = [
    # (label, headers, follow_redirects)
    ("Browser Chrome", {
        'User-Agent': BROWSER_UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }, True),
    ("Android WebView", {
        'User-Agent': WEBVIEW_UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'X-Requested-With': 'com.netflix.mediaclient',
    }, True),
    ("Android Chrome", {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; M2007J3SG) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }, True),
    ("Chrome + Origin", {
        'User-Agent': BROWSER_UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Origin': 'https://www.netflix.com',
        'Referer': 'https://www.netflix.com/',
    }, True),
    ("No redirect, Chrome", {
        'User-Agent': BROWSER_UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }, False),
    ("No redirect, WebView", {
        'User-Agent': WEBVIEW_UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'X-Requested-With': 'com.netflix.mediaclient',
    }, False),
]

for label, headers, follow in test_configs:
    s = requests.Session()
    
    # Try encoded URL
    url_enc = f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token, safe='')}"
    r = s.get(url_enc, headers=headers, allow_redirects=follow, timeout=10)
    
    redirect_chain = []
    if not follow:
        redirect_chain.append(f"{r.status_code} -> {r.headers.get('location','none')[:80]}")
        hist = []
        loc = r.headers.get('location', '')
        while loc and loc not in hist:
            hist.append(loc)
            r2 = s.get(loc, headers=headers, allow_redirects=False, timeout=10)
            redirect_chain.append(f"{r2.status_code} -> {r2.headers.get('location','none')[:80]}")
            loc = r2.headers.get('location', '')
    
    nf_cookie = s.cookies.get('NetflixId', 'NO')
    snf_cookie = s.cookies.get('SecureNetflixId', 'NO')
    
    login_check = '/login' in str(r.url).lower()
    
    hist_str = ' | '.join(redirect_chain) if redirect_chain else 'followed'
    print(f"  [{label:25s}] final_url={str(r.url)[:70]}")
    print(f"    NetflixId={'YES' if nf_cookie != 'NO' else 'NO'} | SecureNetflixId={'YES' if snf_cookie != 'NO' else 'NO'} | login_page={login_check}")
    print(f"    redirects={hist_str}")

# ============================================================
# TEST 4: Try www.netflix.com/graphql as endpoint for web tokens
# ============================================================
print("\n" + "="*70)
print("TEST 4: www.netflix.com/graphql - POSSIBLY DIFFERENT SCOPE BEHAVIOR")
print("="*70)

browser_headers = {
    'User-Agent': BROWSER_UA,
    'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
    'Origin': 'https://www.netflix.com',
}

alt_endpoints = [
    ("https://www.netflix.com/graphql", BROWSER_UA),
    ("https://www.netflix.com/graphql", ANDROID_UA),
    ("https://netflix.com/graphql", BROWSER_UA),
    ("https://ios.prod.ftl.netflix.com/graphql", ANDROID_UA),
]

for alt_ep, alt_ua in alt_endpoints:
    h = dict(browser_headers)
    h['User-Agent'] = alt_ua
    r = requests.post(alt_ep, headers=h, json={
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
    err = data.get('errors', [])
    err_msg = err[0].get('message', '')[:60] if err else ''
    token_preview = token[:50] if token else 'NO'
    print(f"  {alt_ep[:55]:55s} ua={alt_ua[:25]:25s} -> {token_preview} | err={err_msg}")

# ============================================================
# TEST 5: Check if we can use the token differently
# ============================================================
print("\n" + "="*70)
print("TEST 5: ALTERNATIVE TOKEN USAGE")
print("="*70)

# Get fresh token
r = requests.post(EP, headers=base_headers, json={
    "operationName": "CreateAutoLoginToken",
    "variables": {"scope": "WEBVIEW_MOBILE_STREAMING"},
    "extensions": {
        "persistedQuery": {
            "version": 102,
            "id": "76e97129-f4b5-41a0-a73c-12e674896849"
        }
    }
}, verify=False, timeout=10)
token = r.json()['data']['createAutoLoginToken']
print(f"Fresh token: {len(token)} chars")

# Analyze the token structure
# It starts with "Bgj" - let's see if we can decode parts
print(f"Token prefix: {token[:20]}")
print(f"Token suffix: {token[-20:]}")

# The token seems to be base64url-like but with + and /
# Try decoding from base64
try:
    # Add padding
    padded = token + '=' * (4 - len(token) % 4) if len(token) % 4 else token
    decoded = base64.b64decode(padded)
    print(f"Base64 decoded: {len(decoded)} bytes, preview: {decoded[:50]}")
except Exception as e:
    print(f"Base64 decode failed: {e}")

# Try different URL paths for nftoken
nftoken_paths = [
    f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token, safe='')}",
    f"https://www.netflix.com/account?nftoken={token}",
    f"https://www.netflix.com/login?nftoken={urllib.parse.quote(token, safe='')}",
    f"https://www.netflix.com/browse?nftoken={urllib.parse.quote(token, safe='')}",
    f"https://www.netflix.com/?nftoken={urllib.parse.quote(token, safe='')}",
    f"https://www.netflix.com/account/autologin?token={urllib.parse.quote(token, safe='')}",
]

for nf_url in nftoken_paths:
    s = requests.Session()
    r = s.get(nf_url, headers={
        'User-Agent': BROWSER_UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }, allow_redirects=True, timeout=10)
    nf = s.cookies.get('NetflixId', 'NO')
    login = '/login' in str(r.url).lower()
    print(f"  path={nf_url.split('?')[1][:50]:55s} NetflixId={'YES' if nf != 'NO' else 'NO'} login_page={login}")

# ============================================================
# TEST 6: Try with the token as a header/bearer
# ============================================================
print("\n" + "="*70)
print("TEST 6: USING TOKEN AS BEARER / AUTH HEADER")
print("="*70)

# Try using the nftoken as an Authorization header
auth_urls = [
    "https://www.netflix.com/account",
    "https://www.netflix.com/browse",
    "https://www.netflix.com/YourAccount",
]

for auth_url in auth_urls:
    r = requests.get(auth_url, headers={
        'User-Agent': BROWSER_UA,
        'Authorization': f'Bearer {token}',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }, allow_redirects=True, verify=False, timeout=10)
    login = '/login' in str(r.url).lower()
    print(f"  Bearer token on {auth_url[:40]:40s} -> login_page={login} | status={r.status_code}")

    # Try with x-nftoken header
    r2 = requests.get(auth_url, headers={
        'User-Agent': BROWSER_UA,
        'X-NFToken': token,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }, allow_redirects=True, verify=False, timeout=10)
    login2 = '/login' in str(r2.url).lower()
    print(f"  X-NFToken header on {auth_url[:40]:40s} -> login_page={login2} | status={r2.status_code}")

# ============================================================
# TEST 7: Try to enumerate the full mutation list
# ============================================================
print("\n" + "="*70)
print("TEST 7: ENUMERATE POSSIBLE MUTATIONS")
print("="*70)

# Since __schema is blocked, let's try common mutations
# Try to call them and see what errors we get
mutation_guesses = [
    # Auto login tokens
    "createAutoLoginToken(scope: WEBVIEW_MOBILE_STREAMING)",
    "createAutoLoginTokenBrowser(scope: WEBVIEW_MOBILE_STREAMING)",
    "createWebAutoLoginToken(scope: WEBVIEW_MOBILE_STREAMING)",
    "createSession",
    "createSessionToken(scope: WEBVIEW_MOBILE_STREAMING)",
    "createAuthToken(scope: WEBVIEW_MOBILE_STREAMING)",
    # Maybe the mutation returns an object with token field
    "createAutoLoginToken(scope: WEBVIEW_MOBILE_STREAMING) { token }",
    "createAutoLoginToken(scope: WEBVIEW_MOBILE_STREAMING) { nftoken }",
    "createAutoLoginToken(scope: WEBVIEW_MOBILE_STREAMING) { url }",
    "createAutoLoginToken(scope: WEBVIEW_MOBILE_STREAMING) { accessToken }",
]

for mutation_text in mutation_guesses:
    full_query = f"mutation {{ {mutation_text} }}"
    try:
        r = requests.post(EP, headers=base_headers, json={
            "query": full_query,
        }, verify=False, timeout=10)
        data = r.json() if r.text.strip() else {}
        err = data.get('errors', [])
        err_msg = err[0].get('message', '')[:100] if err else ''
        has_data = 'data' in data and data['data'] is not None
        print(f"  {mutation_text:70s} -> data={has_data} | {err_msg}")
    except Exception as e:
        print(f"  {mutation_text:70s} -> ERROR: {str(e)[:50]}")

print("\n" + "="*70)
print("EXPLORATION PART 2 COMPLETE")
print("="*70)
