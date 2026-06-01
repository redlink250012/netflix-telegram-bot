from aiohttp import web
import os

async def hello(request):
    return web.Response(text="Hola Mundo! Railway funciona!")

app = web.Application()
app.router.add_get("/", hello)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)
