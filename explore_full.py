"""
Netflix API Full Exploration
Tests multiple endpoints, query IDs, scopes, and auth operations
"""
import requests, json, itertools, time, re, urllib.parse
import warnings
warnings.filterwarnings("ignore")

# Disable SSL warnings
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
print(f"Cookies loaded: {len(cookies)}")
print(f"NetflixId present: {'NetflixId' in cookies}")
print(f"SecureNetflixId present: {'SecureNetflixId' in cookies}")

ANDROID_UA = "com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)"
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
IOT_UA = "com.netflix.mediaclient/63884 (Linux; U; Android 7; ro; M2007J3SG; Build/NRD90M; Cronet/143.0.7445.0)"

base_headers = {
    'User-Agent': ANDROID_UA,
    'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
}

browser_headers = {
    'User-Agent': BROWSER_UA,
    'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
}

simple_headers = {
    'User-Agent': ANDROID_UA,
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
}

# ============================================================
# SECTION 1: Test different GraphQL endpoints
# ============================================================
print("\n" + "="*70)
print("SECTION 1: TESTING DIFFERENT GRAPHQL ENDPOINTS")
print("="*70)

endpoints = [
    "https://android13.prod.ftl.netflix.com/graphql",
    "https://android.prod.ftl.netflix.com/graphql",
    "https://ios.prod.ftl.netflix.com/graphql",
    "https://ftl.netflix.com/graphql",
    "https://prod.ftl.netflix.com/graphql",
    "https://www.netflix.com/graphql",
    "https://www.netflix.com/api/graphql",
    "https://api.netflix.com/graphql",
    "https://netflix.com/graphql",
    "https://android13.prod.ftl.netflix.com/query",
    "https://www.netflix.com/api/shakti/graphql",
]

for ep in endpoints:
    try:
        r = requests.post(ep, headers=simple_headers, json={
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
        token_preview = token[:50] + '...' if token else 'NO TOKEN'
        print(f"  {ep[:55]:55s} HTTP {r.status_code} -> {token_preview} {err_msg}")
    except Exception as e:
        print(f"  {ep[:55]:55s} ERROR: {str(e)[:50]}")

# ============================================================
# SECTION 2: Try different persisted query IDs
# ============================================================
print("\n" + "="*70)
print("SECTION 2: TRYING DIFFERENT PERSISTED QUERY IDs")
print("="*70)

# These are various Netflix GraphQL query IDs from different sources
# The real ones are hard to guess, but we try the known one plus variations
query_ids = [
    "76e97129-f4b5-41a0-a73c-12e674896849",  # Known working for CreateAutoLoginToken
    
    # Common Netflix query IDs (from apk decompilations / research)
    "5b1a0e5e-ef15-4ab0-8acf-ab2a4a49bdee",  # AccountSummary
    "f2644e66-37c9-4a7b-8f07-4aa30b6eeec5",  # ProfileSelect
    "27b120ff-9690-4016-8a6a-c6f015f6a436",  # Browse
    "c7f94d5e-5528-4ea9-9d49-a88e4e646f8a",  # VideoView
    "b79e5d23-136f-4836-a3b6-4f5a3e0e9b7c",  # Search
    "f29e45f6-3b27-4e5d-905b-a17b5e9e9d50",  # MyList
    "a7efd4f3-12cb-4869-b433-2e8161a889f6",  # Similar to above
    "00000000-0000-0000-0000-000000000000",  # Zero UUID (sometimes works)
]

EP_ANDROID = "https://android13.prod.ftl.netflix.com/graphql"

for qid in query_ids:
    try:
        r = requests.post(EP_ANDROID, headers=simple_headers, json={
            "operationName": "CreateAutoLoginToken",
            "variables": {"scope": "WEBVIEW_MOBILE_STREAMING"},
            "extensions": {
                "persistedQuery": {
                    "version": 102,
                    "id": qid
                }
            }
        }, verify=False, timeout=10)
        data = r.json() if r.text.strip() else {}
        token = data.get('data', {}).get('createAutoLoginToken', '')
        err = data.get('errors', [])
        err_msg = err[0].get('message', '')[:60] if err else ''
        token_preview = token[:50] + '...' if token else 'NO TOKEN'
        print(f"  ID={qid} -> HTTP {r.status_code} | token={token_preview} | err={err_msg}")
    except Exception as e:
        print(f"  ID={qid} -> ERROR: {str(e)[:50]}")

# ============================================================
# SECTION 3: Exhaustive scope testing
# ============================================================
print("\n" + "="*70)
print("SECTION 3: EXHAUSTIVE SCOPE TESTING")
print("="*70)

scopes_to_test = [
    # Current working scope
    "WEBVIEW_MOBILE_STREAMING",
    # Variations
    "WEBVIEW_STREAMING",
    "MOBILE_STREAMING",
    "TV_STREAMING",
    "STREAMING",
    "WEB",
    "MOBILE",
    "BROWSER",
    "NONE",
    "WEB_STREAMING",
    "ANDROID_STREAMING",
    "IOS_STREAMING",
    "DESKTOP_STREAMING",
    "WEBVIEW",
    "ANDROID_WEBVIEW",
    # Other possible scopes
    "SIGN_IN",
    "LOGIN",
    "SESSION",
    "AUTH",
    "TOKEN",
    "AUTO_LOGIN",
    "CREDENTIALS",
    "ACTIVATE",
    "ACTIVATION",
    "DEVICE_ACTIVATION",
    "PARTNER",
    "PARTNER_TOKEN",
    "EXTERNAL",
    "API",
    "SERVICE",
    # Empty / null
    "",
]

for scope in scopes_to_test:
    try:
        variables = {}
        if scope:
            variables['scope'] = scope
        r = requests.post(EP_ANDROID, headers=simple_headers, json={
            "operationName": "CreateAutoLoginToken",
            "variables": variables,
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
        err_msg = err[0].get('message', '')[:80] if err else ''
        if token:
            print(f"  scope={scope!r:30s} -> TOKEN GENERATED! ({len(token)} chars)")
            # Verify if it works cross-platform
            test_url_encoded = f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token, safe='')}"
            test_url_raw = f"https://www.netflix.com/account?nftoken={token}"
            print(f"    Encoded URL: {test_url_encoded[:100]}...")
            print(f"    Raw URL:     {test_url_raw[:100]}...")
        else:
            print(f"  scope={scope!r:30s} -> err={err_msg}")
    except Exception as e:
        print(f"  scope={scope!r:30s} -> EXCEPTION: {str(e)[:50]}")

# ============================================================
# SECTION 4: Test other GraphQL operation names
# ============================================================
print("\n" + "="*70)
print("SECTION 4: OTHER GRAPHQL OPERATIONS")
print("="*70)

# Try different operation names that might generate auth tokens
operations = [
    ("CreateAutoLoginToken", {"scope": "WEBVIEW_MOBILE_STREAMING"}),
    ("generateToken", {}),
    ("generateAutoLoginToken", {}),
    ("createToken", {}),
    ("CreateToken", {}),
    ("CreateSession", {}),
    ("createSession", {}),
    ("Authenticate", {}),
    ("authenticate", {}),
    ("Login", {}),
    ("login", {}),
    ("GetToken", {}),
    ("getToken", {}),
    ("CreateAuthToken", {}),
    ("createAuthToken", {}),
    ("GetAuthToken", {}),
    ("getAuthToken", {}),
]

for op_name, op_vars in operations:
    try:
        r = requests.post(EP_ANDROID, headers=simple_headers, json={
            "operationName": op_name,
            "variables": op_vars,
            "extensions": {
                "persistedQuery": {
                    "version": 102,
                    "id": "76e97129-f4b5-41a0-a73c-12e674896849"
                }
            }
        }, verify=False, timeout=10)
        data = r.json() if r.text.strip() else {}
        err = data.get('errors', [])
        err_msg = err[0].get('message', '')[:80] if err else ''
        has_data = 'data' in data and data['data'] is not None
        print(f"  {op_name:30s} -> HTTP {r.status_code} | has_data={has_data} | err={err_msg}")
    except Exception as e:
        print(f"  {op_name:30s} -> ERROR: {str(e)[:50]}")

# ============================================================
# SECTION 5: Try GraphQL schema introspection
# ============================================================
print("\n" + "="*70)
print("SECTION 5: GRAPHQL SCHEMA INTROSPECTION")
print("="*70)

introspection_query = {
    "query": """
    query IntrospectionQuery {
        __schema {
            queryType { name }
            mutationType { name }
            types {
                name
                kind
                fields {
                    name
                    args {
                        name
                        type {
                            name
                            kind
                        }
                    }
                    type {
                        name
                        kind
                    }
                }
            }
        }
    }
    """
}

schema_headers = {
    'User-Agent': ANDROID_UA,
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
}

r = requests.post(EP_ANDROID, headers=schema_headers, json=introspection_query, verify=False, timeout=15)
print(f"Schema introspection: HTTP {r.status_code}")
print(f"Response: {r.text[:500]}")

# Try without cookies
r2 = requests.post(EP_ANDROID, headers={
    'User-Agent': ANDROID_UA,
    'Accept': 'application/json',
    'Content-Type': 'application/json',
}, json=introspection_query, verify=False, timeout=15)
print(f"Schema no-cookies: HTTP {r2.status_code}")
print(f"Response: {r2.text[:500]}")

# ============================================================
# SECTION 6: Shakti API endpoints
# ============================================================
print("\n" + "="*70)
print("SECTION 6: SHAKTI API ENDPOINTS")
print("="*70)

shakti_endpoints = [
    "/api/shakti/user",
    "/api/shakti/membership",
    "/api/shakti/account",
    "/api/shakti/profile",
    "/api/shakti/browse",
    "/api/shakti/device",
    "/api/shakti/session",
    "/api/shakti/auth",
    "/api/shakti/token",
    "/api/shakti/activation",
    "/api/shakti/permissions",
    "/api/shakti/config",
    "/api/shakti/status",
    "/api/shakti/plan",
    "/api/shakti/payment",
    "/api/shakti/subscription",
    "/api/shakti/autologin",
    "/api/shakti/nftoken",
    "/api/shakti/login",
    "/api/shakti/check",
    "/api/shakti/v2/user",
    "/api/shakti/v2/account",
    "/api/shakti/v2/membership",
]

for ep in shakti_endpoints:
    url = f"https://www.netflix.com{ep}"
    try:
        r = requests.get(url, headers={
            'User-Agent': BROWSER_UA,
            'Accept': 'application/json',
            'Cookie': cookie_str,
        }, allow_redirects=False, verify=False, timeout=10)
        ct = r.headers.get('content-type', '')
        body = r.text[:150] if 'json' in ct else r.text[:80]
        print(f"  {ep:35s} HTTP {r.status_code} | type={ct[:25]:25s} | {body}")
    except Exception as e:
        print(f"  {ep:35s} ERROR: {str(e)[:50]}")

# ============================================================
# SECTION 7: Test nftoken with/without encoding
# ============================================================
print("\n" + "="*70)
print("SECTION 7: NFTOKEN ENCODING TEST")
print("="*70)

# First get a fresh token
r = requests.post(EP_ANDROID, headers=simple_headers, json={
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
token = data.get('data', {}).get('createAutoLoginToken')

if token:
    print(f"Token obtained: {len(token)} chars")
    print(f"Token preview: {token[:80]}...")
    
    # Check if token contains + or / (raw base64 chars)
    has_plus = '+' in token
    has_slash = '/' in token
    print(f"Token contains '+': {has_plus}")
    print(f"Token contains '/': {has_slash}")
    
    # Test 1: URL-encoded token
    url_encoded = f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token, safe='')}"
    # Test 2: Raw token (no encoding)
    url_raw = f"https://www.netflix.com/account?nftoken={token}"
    
    print(f"\nEncoded URL: {url_encoded[:120]}...")
    print(f"Raw URL:     {url_raw[:120]}...")
    
    # Test both with a clean session (no cookies)
    for label, test_url in [("ENCODED", url_encoded), ("RAW", url_raw)]:
        s = requests.Session()
        r = s.get(test_url, headers={
            'User-Agent': BROWSER_UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }, allow_redirects=True, timeout=10)
        
        final_url = str(r.url)
        redirected_to_login = '/login' in final_url.lower()
        
        # Check cookies received
        nf_cookie = s.cookies.get('NetflixId', None)
        secure_nf = s.cookies.get('SecureNetflixId', None)
        
        print(f"  [{label}] Status={r.status_code} | login_page={redirected_to_login} | "
              f"NetflixId={'YES' if nf_cookie else 'NO'} | "
              f"SecureNetflixId={'YES' if secure_nf else 'NO'}")
        
        if nf_cookie and not redirected_to_login:
            print(f"  >> SUCCESS! Token works cross-platform! <<")

# ============================================================
# SECTION 8: Try different User-Agents
# ============================================================
print("\n" + "="*70)
print("SECTION 8: DIFFERENT USER-AGENTS")
print("="*70)

user_agents = [
    ("Android13", ANDROID_UA),
    ("Android7", IOT_UA),
    ("iOS", "com.netflix.mediaclient/63884 (iOS; U; CPU iPhone OS 16_0)"),
    ("Chrome", BROWSER_UA),
    ("Firefox", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0"),
    ("Safari", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"),
    ("Edge", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"),
]

for label, ua in user_agents:
    try:
        r = requests.post(EP_ANDROID, headers={
            'User-Agent': ua,
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
        data = r.json() if r.text.strip() else {}
        token = data.get('data', {}).get('createAutoLoginToken', '')
        err = data.get('errors', [])
        err_msg = err[0].get('message', '')[:60] if err else ''
        token_preview = token[:40] if token else 'NO'
        print(f"  {label:15s} HTTP {r.status_code} | token={token_preview}... | err={err_msg}")
    except Exception as e:
        print(f"  {label:15s} ERROR: {str(e)[:50]}")

# ============================================================
# SECTION 9: Check if nftoken endpoint exists directly
# ============================================================
print("\n" + "="*70)
print("SECTION 9: DIRECT NFTOKEN ENDPOINTS")
print("="*70)

nftoken_endpoints = [
    "https://www.netflix.com/api/nftoken",
    "https://www.netflix.com/api/v1/nftoken",
    "https://www.netflix.com/api/v2/nftoken",
    "https://www.netflix.com/nftoken",
    "https://www.netflix.com/account/nftoken",
    "https://netflix.com/api/nftoken",
]

for ep in nftoken_endpoints:
    try:
        r = requests.get(ep, headers={
            'User-Agent': BROWSER_UA,
            'Accept': 'application/json',
            'Cookie': cookie_str,
        }, allow_redirects=False, verify=False, timeout=10)
        body = r.text[:150]
        print(f"  {ep[:60]:60s} HTTP {r.status_code} | {body}")
    except Exception as e:
        print(f"  {ep[:60]:60s} ERROR: {str(e)[:50]}")

# ============================================================
# SECTION 10: VERSION probe - different API versions
# ============================================================
print("\n" + "="*70)
print("SECTION 10: DIFFERENT API VERSIONS")
print("="*70)

# Try different version numbers for the persisted query
for version in [1, 2, 100, 101, 102, 103, 200]:
    try:
        r = requests.post(EP_ANDROID, headers=simple_headers, json={
            "operationName": "CreateAutoLoginToken",
            "variables": {"scope": "WEBVIEW_MOBILE_STREAMING"},
            "extensions": {
                "persistedQuery": {
                    "version": version,
                    "id": "76e97129-f4b5-41a0-a73c-12e674896849"
                }
            }
        }, verify=False, timeout=10)
        data = r.json() if r.text.strip() else {}
        token = data.get('data', {}).get('createAutoLoginToken', '')
        err = data.get('errors', [])
        err_msg = err[0].get('message', '')[:40] if err else ''
        token_preview = token[:40] if token else 'NO'
        print(f"  version={version:4d} -> HTTP {r.status_code} | token={token_preview}... | err={err_msg}")
    except Exception as e:
        print(f"  version={version:4d} -> ERROR: {str(e)[:40]}")

# ============================================================
# SECTION 11: Try without Accept header variations
# ============================================================
print("\n" + "="*70)
print("SECTION 11: ACCEPT HEADER VARIATIONS")
print("="*70)

accept_headers = [
    "multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json",
    "application/json",
    "application/graphql-response+json",
    "application/x-ndjson",
    "*/*",
]

for accept in accept_headers:
    try:
        r = requests.post(EP_ANDROID, headers={
            'User-Agent': ANDROID_UA,
            'Accept': accept,
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
        data = r.json() if r.text.strip() else {}
        token = data.get('data', {}).get('createAutoLoginToken', '')
        err = data.get('errors', [])
        err_msg = err[0].get('message', '')[:40] if err else ''
        token_preview = token[:40] if token else 'NO'
        print(f"  accept={accept[:35]:35s} HTTP {r.status_code} | token={token_preview}... | err={err_msg}")
    except Exception as e:
        print(f"  accept={accept[:35]:35s} ERROR: {str(e)[:40]}")

# ============================================================
# SECTION 12: Try raw GraphQL query instead of persisted query
# ============================================================
print("\n" + "="*70)
print("SECTION 12: RAW GRAPHQL QUERY (NO PERSISTED QUERY)")
print("="*70)

# Try sending the raw query instead of using persistedQuery
raw_query = {
    "query": """
    mutation CreateAutoLoginToken($scope: String!) {
        createAutoLoginToken(scope: $scope)
    }
    """,
    "variables": {"scope": "WEBVIEW_MOBILE_STREAMING"},
    "operationName": "CreateAutoLoginToken",
}

r = requests.post(EP_ANDROID, headers=simple_headers, json=raw_query, verify=False, timeout=10)
print(f"Raw query: HTTP {r.status_code} | {r.text[:300]}")

# Try without operationName
raw_query2 = {
    "query": "mutation { createAutoLoginToken(scope: \"WEBVIEW_MOBILE_STREAMING\") }",
}
r2 = requests.post(EP_ANDROID, headers=simple_headers, json=raw_query2, verify=False, timeout=10)
print(f"Minimal query: HTTP {r2.status_code} | {r2.text[:300]}")

# ============================================================
# SECTION 13: Try to discover what's available on different FTL endpoints
# ============================================================
print("\n" + "="*70)
print("SECTION 13: FTL ENDPOINT DISCOVERY")
print("="*70)

ftl_endpoints_test = [
    ("https://android13.prod.ftl.netflix.com/", "GET"),
    ("https://android13.prod.ftl.netflix.com/health", "GET"),
    ("https://android13.prod.ftl.netflix.com/status", "GET"),
    ("https://android13.prod.ftl.netflix.com/v1/graphql", "POST"),
    ("https://android13.prod.ftl.netflix.com/v2/graphql", "POST"),
]

for ftl_url, method in ftl_endpoints_test:
    try:
        if method == "GET":
            r = requests.get(ftl_url, headers=simple_headers, verify=False, timeout=10)
        else:
            r = requests.post(ftl_url, headers=simple_headers, json={}, verify=False, timeout=10)
        print(f"  {method} {ftl_url[:60]:60s} HTTP {r.status_code} | {r.text[:200]}")
    except Exception as e:
        print(f"  {method} {ftl_url[:60]:60s} ERROR: {str(e)[:50]}")

# ============================================================
# SECTION 14: Try with Content-Type variations
# ============================================================
print("\n" + "="*70)
print("SECTION 14: CONTENT-TYPE VARIATIONS")
print("="*70)

content_types = [
    "application/json",
    "application/json; charset=utf-8",
    "application/graphql-response+json",
    "text/plain",
    "",
]

for ct in content_types:
    h = dict(simple_headers)
    if ct:
        h['Content-Type'] = ct
    else:
        h.pop('Content-Type', None)
    try:
        r = requests.post(EP_ANDROID, headers=h, json={
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
        err_msg = err[0].get('message', '')[:40] if err else ''
        token_preview = token[:40] if token else 'NO'
        print(f"  ct={ct[:30]:30s} HTTP {r.status_code} | token={token_preview}... | err={err_msg}")
    except Exception as e:
        print(f"  ct={ct[:30]:30s} ERROR: {str(e)[:40]}")

print("\n" + "="*70)
print("EXPLORATION COMPLETE")
print("="*70)
