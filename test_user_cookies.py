import httpx, json

cookies_str = open("user_cookies.json").read()
resp = httpx.post(
    "https://netflix-telegram-bot-production.up.railway.app/api/check",
    json={"cookies": cookies_str},
    timeout=30
)
data = resp.json()
print("Status:", resp.status_code)
print("Error:", data.get("error", "None"))
print("Valid:", data.get("valid"))
if data.get("error"):
    print("Full response:", json.dumps(data, indent=2))
