import httpx, json

# Cookie-Editor JSON format
payload = {
    "cookies": '''[
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
}

resp = httpx.post(
    "https://netflix-telegram-bot-production.up.railway.app/api/check",
    json=payload,
    timeout=30
)
print("Status:", resp.status_code)
data = resp.json()
print("Error:", data.get("error", "None"))
print("Valid:", data.get("valid"))
print("Token:", "YES" if data.get("token") else "NO")
print("Keys in cookies:", list(data.get("account_info", {}).keys()))
