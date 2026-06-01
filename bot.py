import os
import json
import uuid
import logging
from urllib.parse import urljoin, quote

import aiohttp
from aiohttp import web
from bs4 import BeautifulSoup

COOKIES_FILE = os.path.join(os.path.dirname(__file__), "cookies_store.json")

def load_cookies_store():
    try:
        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_cookies_store(store):
    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ContextTypes

from netflix_checker import check_cookies, parse_cookies, cookies_to_header

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8487797010:AAFwo0KdJWy-Gu9tkpVic9CrEVs82S1b1CM")
RAILWAY_URL = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost:8080")
WEBAPP_URL = os.environ.get("WEBAPP_URL", f"https://{RAILWAY_URL}")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))

cookies_store = load_cookies_store()


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    btn = InlineKeyboardButton(
        text="Abrir Netflix Checker",
        web_app=WebAppInfo(url=f"{WEBAPP_URL}/web_app/index.html"),
    )
    kb = InlineKeyboardMarkup([[btn]])
    await update.message.reply_text(
        "🎬 *Netflix Cookie Browser*\n\n"
        "Abrí la mini app para pegar tus cookies de Netflix y acceder a tu cuenta.\n\n"
        "1. Hacé clic en el botón de abajo\n"
        "2. Pegá tus cookies (NetflixId + SecureNetflixId)\n"
        "3. Verificá y navegá tu cuenta",
        parse_mode="Markdown",
        reply_markup=kb,
    )


async def handle_webapp_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_message.web_app_data:
        return

    data = update.effective_message.web_app_data.data
    user_id = update.effective_user.id if update.effective_user else 0

    try:
        payload = json.loads(data)
        cookie_str = payload.get("cookies", "")
    except (json.JSONDecodeError, TypeError):
        cookie_str = data

    if not cookie_str:
        await update.effective_message.reply_text("No se recibieron cookies.")
        return

    msg = await update.effective_message.reply_text("🔍 Verificando cookies con Netflix...")

    result = check_cookies(cookie_str)

    cookies_store[user_id] = {
        "cookies": cookie_str,
        "result": result,
    }

    if result.get("error"):
        await msg.edit_text(f"❌ *Error:* {result['error']}", parse_mode="Markdown")
        return

    info = result.get("account_info", {})
    profiles = info.get("profiles", [])
    plan = info.get("plan", "N/A")
    email = info.get("email", "N/A")
    country = info.get("country", "N/A")
    status = info.get("membership_status", "N/A")
    payment = info.get("payment_method", "")
    token_url = result.get("token_url", "")

    text = (
        f"✅ *Cookies Válidas*\n\n"
        f"📧 *Email:* `{email}`\n"
        f"🌍 *País:* {country}\n"
        f"📌 *Estado:* {status}\n"
        f"📺 *Plan:* {plan}\n"
        f"💳 *Pago:* {payment}"
    )

    if profiles:
        text += f"\n👤 *Perfiles:* {', '.join(profiles[:5])}"

    kb = None
    if token_url:
        btns = []
        if result.get("android_intent"):
            btns.append(InlineKeyboardButton(text="📱 Abrir en App Netflix", url=result["android_intent"]))
        btns.append(InlineKeyboardButton(text="▶ Abrir en navegador", url=token_url))
        kb = InlineKeyboardMarkup([btns])

    await msg.edit_text(text, parse_mode="Markdown", reply_markup=kb)


async def handle_api_debug(request: web.Request) -> web.Response:
    return web.Response(text=json.dumps({"status": "ok", "version": "2", "test": "áéíóú", "store_keys": list(cookies_store.keys())[:10]}, ensure_ascii=False), content_type="application/json", charset="utf-8")

async def handle_api_check(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        cookie_str = body.get("cookies", "")
        user_id = body.get("user_id", "")
    except Exception:
        return web.Response(text='{"error": "JSON inválido"}', content_type="application/json", charset="utf-8", status=400)

    result = check_cookies(cookie_str)

    # Generate session token for proxy access
    session_id = str(uuid.uuid4())[:8]
    cookies_store[session_id] = cookie_str
    if user_id:
        cookies_store[user_id] = cookie_str
    try:
        save_cookies_store(cookies_store)
    except Exception:
        pass

    # Add cookies_json for Cookie-Editor export
    cookies = parse_cookies(cookie_str)
    json_format = [
        {
            "domain": "netflix.com",
            "name": name,
            "value": value,
            "path": "/",
            "secure": True,
            "httpOnly": name in ('NetflixId', 'SecureNetflixId'),
            "hostOnly": False,
            "sameSite": "no_restriction",
        }
        for name, value in cookies.items()
    ]
    result["cookies_json"] = json.dumps(json_format, ensure_ascii=False)
    result["session_id"] = session_id
    result["proxy_url"] = f"/proxy/browse?session_id={session_id}"
    result["_debug_store_keys"] = list(cookies_store.keys())[:5]

    return web.Response(text=json.dumps(result, ensure_ascii=False), content_type="application/json", charset="utf-8")


async def handle_api_browse(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        cookie_str = body.get("cookies", "")
        path = body.get("path", "/")
    except Exception:
        return web.Response(text='{"error": "JSON inválido"}', content_type="application/json", charset="utf-8", status=400)

    cookies = parse_cookies(cookie_str)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Cookie": cookies_to_header(cookies),
    }

    url = urljoin("https://www.netflix.com", path)
    connector = aiohttp.TCPConnector(ssl=False)

    try:
        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                html = await resp.text()
        return web.Response(text=json.dumps({"ok": True, "html": html, "url": str(resp.url), "status": resp.status}, ensure_ascii=False), content_type="application/json", charset="utf-8")
    except Exception as e:
        return web.Response(text=json.dumps({"ok": False, "error": str(e)[:100]}, ensure_ascii=False), content_type="application/json", charset="utf-8")


async def handle_api_proxy(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        cookies_str = body.get("cookies", "")
    except Exception:
        return web.Response(text="JSON inválido", status=400)

    if not cookies_str:
        return web.Response(text="No se enviaron cookies", status=400)

    cookies = parse_cookies(cookies_str)
    base_url = f"https://{request.host}/proxy"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cookie": cookies_to_header(cookies),
    }
    connector = aiohttp.TCPConnector(ssl=False)

    try:
        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            async with session.get("https://www.netflix.com/browse", timeout=aiohttp.ClientTimeout(total=30)) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                nf_domains = ("netflix.com", "nflxext.com", "nflximg.net", "nflxvideo.net", "nflxso.net")
                session_id = str(uuid.uuid4())[:8]
                cookies_store[session_id] = cookies_str
                try:
                    save_cookies_store(cookies_store)
                except Exception:
                    pass
                for tag, attr in [("a", "href"), ("link", "href"), ("img", "src"), ("script", "src"),
                                  ("source", "src"), ("video", "src"), ("form", "action")]:
                    for el in soup.find_all(tag, **{attr: True}):
                        val = el[attr]
                        if val.startswith("//"):
                            el[attr] = f"{base_url}/https:{val}?session_id={session_id}"
                        elif val.startswith("/"):
                            el[attr] = f"{base_url}{val}?session_id={session_id}"
                        elif any(d in val for d in nf_domains):
                            el[attr] = f"{base_url}/{val}?session_id={session_id}"
                return web.Response(text=str(soup), content_type="text/html", charset="utf-8")
    except Exception as e:
        return web.Response(text=f"<html><body style='background:#141414;color:#fff;padding:40px;font-family:sans-serif'><h1>Error</h1><p>{str(e)[:200]}</p></body></html>", content_type="text/html", charset="utf-8")

async def handle_proxy(request: web.Request) -> web.Response:
    path = request.match_info.get("path", "/")
    if not path.startswith("/"):
        path = "/" + path
    session_id = request.query.get("session_id", "")
    user_id = request.query.get("user_id", "")
    cookies_str = ""
    if session_id and session_id in cookies_store:
        cookies_str = cookies_store[session_id]
    if not cookies_str and user_id and user_id in cookies_store:
        cookies_str = cookies_store[user_id]
    if not cookies_str:
        return web.Response(text='<html><body style="background:#141414;color:#fff;padding:40px;font-family:sans-serif"><h1>❌ Sesión expirada</h1><p>Volvé a la Mini App, pegá las cookies y usá "🌐 Ingresar y Abrir Netflix".</p></body></html>', content_type="text/html", charset="utf-8")
    key_param = "session_id" if session_id else "user_id"
    key = session_id or user_id
    cookies = parse_cookies(cookies_str)
    base_url = f"https://{request.host}/proxy"
    headers = {
        "User-Agent": "Mozilla/5.0 (SMART-TV; Linux; Tizen 5.0) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/2.0 Chrome/63.0.3239.84 TV Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cookie": cookies_to_header(cookies),
    }
    url = urljoin("https://www.netflix.com", path)
    connector = aiohttp.TCPConnector(ssl=False)

    try:
        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                ct = resp.headers.get("Content-Type", "")
                if "text/html" in ct:
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    nf_domains = ("netflix.com", "nflxext.com", "nflximg.net", "nflxvideo.net", "nflxso.net")
                    for tag, attr in [("a", "href"), ("link", "href"), ("img", "src"), ("script", "src"),
                                      ("source", "src"), ("video", "src"), ("form", "action")]:
                        for el in soup.find_all(tag, **{attr: True}):
                            val = el[attr]
                            if val.startswith("//"):
                                el[attr] = f"{base_url}/https:{val}?{key_param}={key}"
                            elif val.startswith("/"):
                                el[attr] = f"{base_url}{val}?{key_param}={key}"
                            elif any(d in val for d in nf_domains):
                                el[attr] = f"{base_url}/{val}?{key_param}={key}"
                    return web.Response(text=str(soup), content_type="text/html", charset="utf-8")
                else:
                    content = await resp.read()
                    return web.Response(body=content, content_type=ct)
    except Exception as e:
        return web.Response(text=f"Proxy error: {str(e)[:200]}", status=502)

async def handle_static(request: web.Request) -> web.Response:
    path = request.match_info.get("path", "index.html")
    filepath = os.path.join(os.path.dirname(__file__), "web_app", path)

    if not os.path.exists(filepath) or os.path.isdir(filepath):
        filepath = os.path.join(os.path.dirname(__file__), "web_app", "index.html")

    _, ext = os.path.splitext(filepath)
    content_type = {
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".png": "image/png",
        ".svg": "image/svg+xml",
    }.get(ext, "text/plain")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        resp = web.Response(text=content, content_type=content_type, charset="utf-8")
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    except FileNotFoundError:
        return web.Response(status=404, text="Not Found")


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        resp = web.Response()
    else:
        resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


async def run_bot(app: web.Application):
    try:
        bot_app = (
            Application.builder()
            .token(BOT_TOKEN)
            .build()
        )
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling()

        app["bot_app"] = bot_app
        log.info("✅ Bot de Telegram iniciado correctamente")
    except Exception as e:
        log.warning(f"⚠️ No se pudo iniciar el bot: {e}")
        log.warning("El servidor web sigue funcionando sin el bot")


async def cleanup(app: web.Application):
    bot_app = app.get("bot_app")
    if bot_app:
        try:
            await bot_app.updater.stop()
            await bot_app.stop()
            await bot_app.shutdown()
        except Exception:
            pass


def main():
    app = web.Application(middlewares=[cors_middleware])

    app.on_startup.append(run_bot)
    app.on_shutdown.append(cleanup)

    app.router.add_get("/", lambda r: web.Response(text="Netflix Cookie Browser API", content_type="text/plain"))
    app.router.add_get("/web_app/{path:.*}", handle_static)
    app.router.add_get("/api/debug", handle_api_debug)
    app.router.add_post("/api/check", handle_api_check)
    app.router.add_post("/api/browse", handle_api_browse)
    app.router.add_post("/api/proxy", handle_api_proxy)
    app.router.add_get("/proxy/{path:.*}", handle_proxy)
    app.router.add_post("/proxy/{path:.*}", handle_proxy)

    log.info(f"🔥 Servidor iniciado en http://{HOST}:{PORT}")
    log.info(f"📱 Web App: {WEBAPP_URL}/web_app/index.html")
    log.info(f"🤖 Bot corriendo con polling")

    web.run_app(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
