from netflix_checker import parse_cookies, check_cookies
import json

# Test 1: Pretty-printed JSON array (like Cookie-Editor export)
test_json = '''[
    {
        "domain": ".netflix.com",
        "name": "NetflixId",
        "value": "v=3&ct=test123"
    },
    {
        "domain": ".netflix.com",
        "name": "SecureNetflixId",
        "value": "v=3&mac=test456"
    }
]'''

result = parse_cookies(test_json)
print("Test 1 - JSON pretty-printed:")
print("  Keys:", list(result.keys()))
print("  NetflixId:", result.get("NetflixId", "MISSING"))
print("  SecureNetflixId:", result.get("SecureNetflixId", "MISSING"))

# Test 2: Full check with the JSON
result2 = check_cookies(test_json)
print("\nTest 2 - Full check_cookies:")
print(json.dumps({k: v for k, v in result2.items() if k != 'cookies_json'}, indent=2))
