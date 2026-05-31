"""
Netflix API Exploration Part 3 - Focused on cross-platform token and nftoken consumption
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
EP_WEB = "https://www.netflix.com/graphql"

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
# TEST 1: Do the cookies set by nftoken actually work?
# ============================================================
print("="*70)
print("TEST 1: ARE NFTOKEN-SET COOKIES VALID FOR BROWSER?")
print("="*70)

token = gen_token()
print(f"Token: {len(token)} chars")

# Step 1: Visit nftoken URL WITHOUT any pre-existing cookies (clean session)
s = requests.Session()
r = s.get(
    f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token, safe='')}",
    headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
    allow_redirects=False, timeout=10
)
print(f"\n1) nftoken visit (no cookies): status={r.status_code} location={r.headers.get('location','')[:60]}")
print(f"   Cookies received: {dict(s.cookies)}")

# Also capture Set-Cookie header directly
set_cookie_raw = r.headers.get('set-cookie', '')
print(f"   Set-Cookie header: {set_cookie_raw[:200]}")

nf_cookie = s.cookies.get('NetflixId', '')
snf_cookie = s.cookies.get('SecureNetflixId', '')
print(f"   NetflixId in session: {'YES (' + nf_cookie[:30] + '...)' if nf_cookie else 'NO'}")
print(f"   SecureNetflixId in session: {'YES' if snf_cookie else 'NO'}")

# Step 2: Now try to access /account with the cookies from the redirect chain
# Follow the redirect and collect all cookies
s2 = requests.Session()
r2 = s2.get(
    f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token, safe='')}",
    headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
    allow_redirects=True, timeout=10
)
print(f"\n2) nftoken + follow redirects:")
print(f"   Final URL: {r2.url[:80]}")
print(f"   Cookies after follow: {dict(s2.cookies)}")
nf_after = s2.cookies.get('NetflixId', '')
print(f"   NetflixId: {'YES (' + nf_after[:30] + '...)' if nf_after else 'NO'}")

# Step 3: Now use the cookies we got from nftoken to try accessing /account fresh
if nf_cookie:
    print(f"\n3) Using nftoken cookies in a NEW session to access /account:")
    s3 = requests.Session()
    # Manually set the cookies we got
    s3.cookies.set('NetflixId', nf_cookie, domain='.netflix.com', path='/')
    if snf_cookie:
        s3.cookies.set('SecureNetflixId', snf_cookie, domain='.netflix.com', path='/')
    r3 = s3.get(
        "https://www.netflix.com/account",
        headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
        allow_redirects=True, timeout=10
    )
    print(f"   Final URL: {r3.url[:80]}")
    print(f"   Status: {r3.status_code}")
    if '/login' in r3.url.lower():
        print(f"   -> REDIRECTED TO LOGIN (cookies from nftoken don't work standalone)")
    else:
        print(f"   >>> NFTOKEN COOKIES WORK for browser!")

# Step 4: Check if we're being geo-redirected before token processing
print(f"\n4) Testing if geo/country redirect happens FIRST:")
s4 = requests.Session()
r4 = s4.get(
    f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token, safe='')}",
    headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
    allow_redirects=False, timeout=10
)
# Follow redirects ONE AT A TIME
history = []
urls_seen = []
current_url = f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token, safe='')}"
for i in range(10):
    if current_url in urls_seen:
        break
    urls_seen.append(current_url)
    r = s4.get(current_url, headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
               allow_redirects=False, timeout=10)
    loc = r.headers.get('location', '')
    print(f"   Step {i}: {r.status_code} -> {loc[:80]}")
    print(f"      Set-Cookie: {r.headers.get('set-cookie','')[:150]}")
    print(f"      Cookies now: NetflixId={'YES' if s4.cookies.get('NetflixId') else 'NO'} | "
          f"SecureNetflixId={'YES' if s4.cookies.get('SecureNetflixId') else 'NO'}")
    if r.status_code in (301, 302, 303, 307, 308) and loc:
        current_url = loc if loc.startswith('http') else f"https://www.netflix.com{loc}"
    else:
        break

# ============================================================
# TEST 2: Can we POST to the nftoken endpoint instead of GET?
# ============================================================
print("\n" + "="*70)
print("TEST 2: POST TO NFTOKEN ENDPOINT")
print("="*70)

token2 = gen_token()
post_urls = [
    ("/account", {"nftoken": token2}),
    ("/login", {"nftoken": token2}),
    ("/autologin", {"token": token2}),
    ("/api/nftoken", {"token": token2}),
]

for path, params in post_urls:
    url = f"https://www.netflix.com{path}"
    try:
        s = requests.Session()
        r = s.post(url, data=params, headers={
            'User-Agent': BROWSER_UA,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,*/*',
        }, allow_redirects=True, timeout=10)
        nf = s.cookies.get('NetflixId', '')
        print(f"  POST {path:30s} status={r.status_code} url={r.url[:50]} NetflixId={'YES' if nf else 'NO'} login={'YES' if '/login' in r.url.lower() else 'NO'}")
    except Exception as e:
        print(f"  POST {path:30s} ERROR: {str(e)[:40]}")

# ============================================================
# TEST 3: Try www.netflix.com/graphql with web-specific operations
# ============================================================
print("\n" + "="*70)
print("TEST 3: WEB-SPECIFIC GRAPHQL OPERATIONS ON www.netflix.com/graphql")
print("="*70)

web_headers = {
    'User-Agent': BROWSER_UA,
    'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
    'Origin': 'https://www.netflix.com',
    'Referer': 'https://www.netflix.com/browse',
}

# The web endpoint might have different queries
# Let's try to see what queries we can send
test_web_queries = [
    # Known web persisted queries
    ("AccountSummary", {"operationName": "AccountSummary", "variables": {}, 
     "extensions": {"persistedQuery": {"version": 1, "id": "account"}}}),
    ("Browse", {"operationName": "Browse", "variables": {}, 
     "extensions": {"persistedQuery": {"version": 1, "id": "browse"}}}),
    # Just try the same as Android
    ("CreateAutoLoginToken_web", {"operationName": "CreateAutoLoginToken", 
     "variables": {"scope": "WEBVIEW_MOBILE_STREAMING"},
     "extensions": {"persistedQuery": {"version": 102, "id": "76e97129-f4b5-41a0-a73c-12e674896849"}}}),
]

for test_name, payload in test_web_queries:
    r = requests.post(EP_WEB, headers=web_headers, json=payload, verify=False, timeout=10)
    data = r.json() if r.text.strip() else {}
    print(f"  {test_name:30s} HTTP {r.status_code} | {json.dumps(data)[:200]}")

# Try raw query on web endpoint
print("\n-- Raw mutation on www.netflix.com/graphql --")
raw_mut = {
    "query": "mutation { createAutoLoginToken(scope: WEBVIEW_MOBILE_STREAMING) }",
    "variables": {}
}
r = requests.post(EP_WEB, headers=web_headers, json=raw_mut, verify=False, timeout=10)
print(f"  Raw mutation: {r.text[:300]}")

# ============================================================
# TEST 4: Try to exchange the token at a different endpoint
# ============================================================
print("\n" + "="*70)
print("TEST 4: TOKEN EXCHANGE / VERIFICATION ENDPOINTS")
print("="*70)

token3 = gen_token()

exchange_tests = [
    # Try various ways to consume/validate the token
    ("GET", f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token3, safe='')}", BROWSER_UA),
    ("GET", f"https://www.netflix.com/account?nftoken={token3}", BROWSER_UA),
    ("GET", f"https://www.netflix.com/login?nftoken={urllib.parse.quote(token3, safe='')}", BROWSER_UA),
    ("GET", f"https://www.netflix.com/browse?nftoken={urllib.parse.quote(token3, safe='')}", BROWSER_UA),
    ("GET", f"https://netflix.com/account?nftoken={urllib.parse.quote(token3, safe='')}", BROWSER_UA),
    # With different Accept headers
    ("GET", f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token3, safe='')}", f"{BROWSER_UA}"),
]

seen_urls = set()
for method, url, ua in exchange_tests:
    if url in seen_urls:
        continue
    seen_urls.add(url)
    s = requests.Session()
    h = {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    r = s.get(url, headers=h, allow_redirects=True, timeout=10)
    nf = s.cookies.get('NetflixId', '')
    login = '/login' in r.url.lower()
    path_part = url.split('?')[0][:40]
    param_part = url.split('?')[1][:50] if '?' in url else ''
    print(f"  {method} {path_part:40s} ?{param_part:50s} -> login={login} NetflixId={'YES' if nf else 'NO'}")

# ============================================================
# TEST 5: Test nftoken with POST to consume it (like form submission)
# ============================================================
print("\n" + "="*70)
print("TEST 5: NFTOKEN CONSUMPTION VIA POST")
print("="*70)

token4 = gen_token()

# Try posting the token to various endpoints
endpoints_to_post = [
    "https://www.netflix.com/account",
    "https://www.netflix.com/autologin",
    "https://www.netflix.com/api/autologin",
]

for ep in endpoints_to_post:
    s = requests.Session()
    r = s.post(ep, data={"nftoken": token4}, headers={
        'User-Agent': BROWSER_UA,
        'Content-Type': 'application/x-www-form-urlencoded',
    }, allow_redirects=True, timeout=10)
    nf = s.cookies.get('NetflixId', '')
    print(f"  POST {ep:50s} status={r.status_code} login={'YES' if '/login' in r.url.lower() else 'NO'} NetflixId={'YES' if nf else 'NO'}")

    # Also try JSON
    s2 = requests.Session()
    r2 = s2.post(ep, json={"nftoken": token4}, headers={
        'User-Agent': BROWSER_UA,
        'Content-Type': 'application/json',
    }, allow_redirects=True, timeout=10)
    nf2 = s2.cookies.get('NetflixId', '')
    print(f"  POST JSON {ep:46s} status={r2.status_code} login={'YES' if '/login' in r2.url.lower() else 'NO'} NetflixId={'YES' if nf2 else 'NO'}")

# ============================================================
# TEST 6: Check if we can find more endpoints by probing
# ============================================================
print("\n" + "="*70)
print("TEST 6: ADDITIONAL ENDPOINT PROBING")
print("="*70)

# Try some additional endpoints
more_endpoints = [
    "https://www.netflix.com/api/autologin",
    "https://www.netflix.com/autologin",
    "https://www.netflix.com/session",
    "https://www.netflix.com/api/session",
    "https://www.netflix.com/api/v1/autologin",
    "https://www.netflix.com/api/v2/autologin",
]

for ep in more_endpoints:
    try:
        r = requests.get(ep, headers={
            'User-Agent': BROWSER_UA,
            'Accept': 'application/json',
            'Cookie': cookie_str,
        }, allow_redirects=False, verify=False, timeout=10)
        print(f"  GET {ep:55s} HTTP {r.status_code} | ct={r.headers.get('content-type','?')[:30]}")
        if r.status_code == 200:
            print(f"      Body: {r.text[:200]}")
    except Exception as e:
        print(f"  GET {ep:55s} ERROR: {str(e)[:50]}")

# ============================================================
# TEST 7: Try nftoken consumption using a HEAD request to trigger auth
# ============================================================
print("\n" + "="*70)
print("TEST 7: HEAD REQUEST WITH NFTOKEN")
print("="*70)

token5 = gen_token()
s = requests.Session()
r = s.head(
    f"https://www.netflix.com/account?nftoken={urllib.parse.quote(token5, safe='')}",
    headers={'User-Agent': BROWSER_UA},
    allow_redirects=True, timeout=10
)
print(f"  HEAD: status={r.status_code} url={r.url[:60]}")
print(f"  Cookies: {dict(s.cookies)}")

# ============================================================
# TEST 8: Try different www.netflix.com hostnames 
# ============================================================
print("\n" + "="*70)
print("TEST 8: TRY DIFFERENT NETFLIX HOSTNAMES")
print("="*70)

token6 = gen_token()

netflix_hosts = [
    "www.netflix.com",
    "netflix.com",
    "www.nflx.com",
    "nflx.com",
    "accounts.netflix.com",
    "www.accounts.netflix.com",
    "movies.netflix.com",
    "www.movies.netflix.com",
]

for host in netflix_hosts:
    try:
        url = f"https://{host}/account?nftoken={urllib.parse.quote(token6, safe='')}"
        s = requests.Session()
        r = s.get(url, headers={'User-Agent': BROWSER_UA, 'Accept': 'text/html,*/*'},
                  allow_redirects=True, timeout=10)
        nf = s.cookies.get('NetflixId', '')
        print(f"  {host:30s} -> {r.status_code} final_url={r.url[:50]} NetflixId={'YES' if nf else 'NO'} login={'YES' if '/login' in r.url.lower() else 'NO'}")
    except Exception as e:
        print(f"  {host:30s} -> ERROR: {str(e)[:40]}")

print("\n" + "="*70)
print("EXPLORATION PART 3 COMPLETE")
print("="*70)
