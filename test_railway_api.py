import httpx, json

cookies = open("netflix_cookies.txt").read()
resp = httpx.post(
    "https://netflix-telegram-bot-production.up.railway.app/api/check",
    json={"cookies": cookies},
    timeout=30
)
print(resp.status_code)
print(json.dumps(resp.json(), indent=2))
