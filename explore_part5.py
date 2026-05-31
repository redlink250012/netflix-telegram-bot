"""
Netflix API Exploration Part 5 - FINAL focused tests
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

base_headers = {
    'User-Agent': ANDROID_UA,
    'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
}

def gen_token():
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
    return r.json()['data']['createAutoLoginToken']

# ============================================================
# TEST 1: CRITICAL - Do the cookies from nftoken work at all?
# ============================================================
print("="*70)
print("TEST 1: VALIDATE NFTOKEN-SET COOKIES")
print("="*70)

token = gen_token()

# Request 1: Get cookies from nftoken (without original cookies)
s1 = requests.Session()
r1 = s1.get(
    f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token, safe='')}",
    headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
    allow_redirects=False, timeout=10
)
# Get NetflixId from first response
nf1 = None
snf1 = None
for cookie in s1.cookies:
    if cookie.name == 'NetflixId':
        nf1 = cookie.value
    if cookie.name == 'SecureNetflixId':
        snf1 = cookie.value

print(f"Step 1 - nftoken request:")
print(f"  Status: {r1.status_code}, Location: {r1.headers.get('location','')[:60]}")
print(f"  NetflixId: {nf1[:40] if nf1 else 'NO'}...")
print(f"  SecureNetflixId: {'YES' if snf1 else 'NO'}")

# Request 2: Try using those cookies to access /account
if nf1:
    s2 = requests.Session()
    # Set a mock Cookie header manually (avoids CookieConflictError)
    s2.headers.update({
        'User-Agent': BROWSER_UA,
        'Accept': 'text/html,*/*',
        'Cookie': f'NetflixId={nf1}; SecureNetflixId={snf1 if snf1 else ""}',
    })
    r2 = s2.get("https://www.netflix.com/account", allow_redirects=True, timeout=10)
    print(f"\nStep 2 - /account with nftoken cookies:")
    print(f"  Status: {r2.status_code}, URL: {r2.url[:70]}")
    print(f"  Login page: {'YES' if '/login' in r2.url.lower() else 'NO'}")

    # Check the response for user info
    body_lower = r2.text.lower()
    has_signout = 'sign out' in body_lower or 'signout' in body_lower
    has_logout = 'log out' in body_lower or 'logout' in body_lower
    has_email = bool(re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', r2.text))
    print(f"  Contains 'sign out': {has_signout}")
    print(f"  Contains 'log out': {has_logout}")

    # If login page is NO but no signout, maybe we're on NotFound
    if not has_signout and not has_logout and '/login' not in r2.url.lower():
        print(f"  Page body (first 300 chars): {r2.text[:300]}")

# ============================================================
# TEST 2: nftoken with additional cookies from redirect chain
# ============================================================
print("\n" + "="*70)
print("TEST 2: FOLLOW COMPLETE NFTOKEN REDIRECT CHAIN")
print("="*70)

s3 = requests.Session()
# Use manual Cookie header to avoid conflicts
s3.headers.update({
    'User-Agent': BROWSER_UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
})

# Step by step redirect following
url = f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token, safe='')}"
for i in range(5):
    r = s3.get(url, allow_redirects=False, timeout=10)
    loc = r.headers.get('location', '')
    sc = r.headers.get('set-cookie', '')[:100]
    
    # Collect cookies from response
    nf = None
    for c in s3.cookies:
        if c.name == 'NetflixId':
            nf = c.value[:40]
    
    print(f"  Step {i}: {r.status_code} | {url.split('?')[0][:50]} -> {loc[:60]}")
    print(f"    Set-Cookie: {sc}")
    print(f"    NetflixId: {nf}")
    
    if r.status_code in (301, 302, 303, 307, 308) and loc:
        url = loc if loc.startswith('http') else f"https://www.netflix.com{loc}"
    else:
        # Check if we ended up on login page or actual content
        body = r.text[:400]
        has_profile = 'ProfileSelect' in r.text or 'profile' in r.text.lower()
        print(f"    Final content check: profile_select={has_profile}")
        print(f"    Body snippet: {body[:200]}")
        break

# ============================================================
# TEST 3: Try with profile selector page after nftoken
# ============================================================
print("\n" + "="*70)
print("TEST 3: NFTOKEN -> PROFILE SELECTOR?")
print("="*70)

# Maybe after nftoken, we need to select a profile first?
# Try visiting /browse after getting nftoken cookies (which might trigger profile selection)
s4 = requests.Session()
r4 = s4.get(
    f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token, safe='')}",
    headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
    allow_redirects=True, timeout=10
)
print(f"  nftoken -> final: {r4.status_code} {r4.url[:70]}")

# Now try /browse
r5 = s4.get("https://www.netflix.com/browse", headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
            allow_redirects=True, timeout=10)
print(f"  /browse after nftoken: {r5.status_code} {r5.url[:70]}")
print(f"  Login page: {'YES' if '/login' in r5.url.lower() else 'NO'}")

# ============================================================
# TEST 4: Does the nftoken URL work on different subdomains?
# ============================================================
print("\n" + "="*70)
print("TEST 4: NFTOKEN ON DIFFERENT PATHS")
print("="*70)

token2 = gen_token()

# The token seems to be consumed at the /account endpoint specifically
# What if we need to visit / without following redirects first?
paths = [
    ("/", {}),
    ("/browse", {}),
    ("/login", {}),
    ("/account", {}),
]

for path, params in paths:
    s = requests.Session()
    url = f"https://www.netflix.com{path}?nftoken={urllib.parse.quote(token2, safe='')}"
    r = s.get(url, headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
              allow_redirects=True, timeout=10)
    nf = None
    for c in s.cookies:
        if c.name == 'NetflixId':
            nf = c.value[:30]
    print(f"  {path:15s} nftoken -> final={r.url[:60]} login={'YES' if '/login' in r.url.lower() else 'NO'} NetflixId={nf}")

# ============================================================
# TEST 5: What happens if we consume nftoken AND stay on the page?
# ============================================================
print("\n" + "="*70)
print("TEST 5: DON'T FOLLOW REDIRECT - CHECK PAGE CONTENT")
print("="*70)

token3 = gen_token()

s5 = requests.Session()
r5 = s5.get(
    f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token3, safe='')}",
    headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'},
    allow_redirects=False, timeout=10
)
print(f"  Status: {r5.status_code}")
print(f"  Location: {r5.headers.get('location','N/A')}")
print(f"  Content-Type: {r5.headers.get('content-type','N/A')}")
print(f"  Set-Cookie: {r5.headers.get('set-cookie','N/A')[:200]}")
print(f"  Body (if any): {r5.text[:500] if r5.text else '(empty)'}")

# Collect the cookies
nf_val = None
snf_val = None
for c in s5.cookies:
    if c.name == 'NetflixId':
        nf_val = c.value
    if c.name == 'SecureNetflixId':
        snf_val = c.value

# Now use these cookies MANUALLY (with Cookie header) to access /account page
if nf_val:
    s6 = requests.Session()
    r6 = s6.get("https://www.netflix.com/account", headers={
        'User-Agent': BROWSER_UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Cookie': f'NetflixId={nf_val}; SecureNetflixId={snf_val}',
    }, allow_redirects=True, timeout=10)
    print(f"\n  /account with nftoken cookies: {r6.status_code} {r6.url[:70]}")
    print(f"  Login: {'YES' if '/login' in r6.url.lower() else 'NO'}")

# ============================================================
# TEST 6: See what errors invalid scopes actually say
# ============================================================
print("\n" + "="*70)
print("TEST 6: EXAMINE INVALID SCOPE ERROR RESPONSES")
print("="*70)

# Fix the error handling to properly capture responses
invalid_scopes = ["WEBVIEW_STREAMING", "BROWSER", "WEB", "MOBILE_STREAMING"]

for scope in invalid_scopes:
    try:
        r = requests.post(EP, headers=base_headers, json={
            "operationName": "CreateAutoLoginToken",
            "variables": {"scope": scope},
            "extensions": {
                "persistedQuery": {
                    "version": 102,
                    "id": "76e97129-f4b5-41a0-a73c-12e674896849"
                }
            }
        }, verify=False, timeout=10)
        data = r.json() if r.text.strip() else {}
        print(f"\n  scope={scope}:")
        print(f"    Full response: {json.dumps(data)[:300]}")
        if 'errors' in data:
            for err in data['errors']:
                print(f"    Error: {err.get('message', '')}")
    except Exception as e:
        print(f"\n  scope={scope}: ERROR: {str(e)[:60]}")

# ============================================================
# TEST 7: Check if cross-platform token requires different endpoint
# ============================================================
print("\n" + "="*70)
print("TEST 7: CHECK ALL FTL ENDPOINTS THAT GENERATE TOKENS")
print("="*70)

ftl_endpoints = [
    "https://android13.prod.ftl.netflix.com/graphql",
    "https://android.prod.ftl.netflix.com/graphql",
    "https://ios.prod.ftl.netflix.com/graphql",
    "https://www.netflix.com/graphql",
    "https://netflix.com/graphql",
]

for ep in ftl_endpoints:
    r = requests.post(ep, headers=base_headers, json={
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
    t = data.get('data', {}).get('createAutoLoginToken', '')
    if t:
        # Test this token for web
        s = requests.Session()
        rr = s.get(f"https://www.netflix.com/account?nftoken={urllib.parse.quote(t, safe='')}",
                   headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
                   allow_redirects=True, timeout=10)
        nf = None
        for c in s.cookies:
            if c.name == 'NetflixId':
                nf = c.value[:30]
        print(f"  {ep[8:40]:35s} token={t[:30]}... -> login={'YES' if '/login' in rr.url.lower() else 'NO'} NetflixId={nf}")
    else:
        print(f"  {ep[8:40]:35s} NO TOKEN")

# ============================================================
# TEST 8: CRITICAL - Search for different token operations
# Try to find other mutations via common field names
# ============================================================
print("\n" + "="*70)
print("TEST 8: SEARCH FOR OTHER TOKEN-RELATED MUTATION FIELDS")
print("="*70)

# Based on Netflix research, common auth mutations:
# We already know createAutoLoginToken works
# Let's try to see if there are related mutations by trying with
# different argument patterns

field_attempts = [
    # Maybe the mutation takes different args
    ("createAutoLoginToken", ["WEBVIEW_MOBILE_STREAMING", "BROWSER", "NATIVE"]),
]

# Try querying the mutation with different argument patterns via raw query
test_raw = """
mutation {
    createAutoLoginToken(scope: WEBVIEW_MOBILE_STREAMING, target: WEB)
}
"""
print("  Trying with additional args (target):")
r = requests.post(EP, headers=base_headers, json={"query": test_raw}, verify=False, timeout=10)
print(f"    {r.text[:300]}")

# Try to find what fields exist on Mutation type
print("\n  Trying __type on Mutation:")
intro_query = {
    "query": """
    query {
        __type(name: "Mutation") {
            name
            fields {
                name
                args {
                    name
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
r = requests.post(EP, headers=base_headers, json=intro_query, verify=False, timeout=10)
data = r.json()
if 'errors' not in data:
    print(f"    {json.dumps(data, indent=2)[:1000]}")
else:
    print(f"    Blocked: {data['errors'][0]['message'][:100]}")

# Try to get a list of all types
print("\n  Trying __schema (minimal):")
intro_query2 = {
    "query": """
    {
        __schema {
            mutationType {
                name
                fields {
                    name
                }
            }
        }
    }
    """
}
r = requests.post(EP, headers=base_headers, json=intro_query2, verify=False, timeout=10)
print(f"    {r.text[:400]}")

# ============================================================
# TEST 9: What if we use the token differently?
# The token format: Bgj6uevcAxL+... 
# Bgj could be a protobuf prefix. Let me analyze the structure
# ============================================================
print("\n" + "="*70)
print("TEST 9: TOKEN STRUCTURE DEEP ANALYSIS")
print("="*70)

tk = gen_token()
print(f"Token: {tk}")

# Decode as base64
try:
    padded = tk + '=' * ((4 - len(tk) % 4) % 4)
    raw_bytes = base64.b64decode(padded)
    print(f"\nDecoded ({len(raw_bytes)} bytes): {raw_bytes.hex()}")
    
    # First byte seems to always be \x06 (0x06)
    # This could be a protobuf tag
    if len(raw_bytes) >= 9:
        print(f"\nHeader bytes:")
        for i in range(min(20, len(raw_bytes))):
            print(f"  [{i:2d}] 0x{raw_bytes[i]:02x} ({raw_bytes[i]:3d}) '{chr(raw_bytes[i]) if 32 <= raw_bytes[i] < 127 else '?'}'")
        
        # Check for protobuf wire types
        # Tag = field_number << 3 | wire_type
        first_tag = raw_bytes[0]
        field_num = first_tag >> 3
        wire_type = first_tag & 0x07
        print(f"\nProto analysis of byte 0: field={field_num} wire_type={wire_type} "
              f"({'VARINT' if wire_type == 0 else 'LEN' if wire_type == 2 else 'OTHER'})")
        
        # Bgj6uevcAxL+ decodes to bytes: 06 08 fa b9 eb dc 03 12 fe
        # \x06 = field 0, wire_type 6? That's not standard proto
        # Or \x06 = field 0, wire_type 6???
        # Actually: 0x06 = 0000 0110 → field 0, wire type 6 (unknown)
        # Hmm, maybe it's not protobuf
except Exception as e:
    print(f"Decode error: {e}")

print("\n" + "="*70)
print("EXPLORATION COMPLETE - SEE SUMMARY BELOW")
print("="*70)
