import os
import json
import logging
from urllib.parse import urljoin

import aiohttp
from aiohttp import web
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

cookies_store = {}


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

    if token_url:
        text += f"\n\n🔑 *Token generado* (válido ~59min)"

    btn = InlineKeyboardButton(
        text="🔑 Abrir Netflix con Token",
        web_app=WebAppInfo(url=f"{WEBAPP_URL}/web_app/index.html"),
    )
    kb = InlineKeyboardMarkup([[btn]])

    await msg.edit_text(text, parse_mode="Markdown", reply_markup=kb)


async def handle_api_check(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        cookie_str = body.get("cookies", "")
    except Exception:
        return web.json_response({"error": "JSON inválido"}, status=400)

    result = check_cookies(cookie_str)

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
    result["cookies_json"] = json.dumps(json_format)

    return web.json_response(result)


async def handle_api_browse(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        cookie_str = body.get("cookies", "")
        path = body.get("path", "/")
    except Exception:
        return web.json_response({"error": "JSON inválido"}, status=400)

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
        return web.json_response({
            "ok": True,
            "html": html,
            "url": str(resp.url),
            "status": resp.status,
        })
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)[:100]})


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
        return web.Response(text=content, content_type=content_type, charset="utf-8")
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
    app.router.add_post("/api/check", handle_api_check)
    app.router.add_post("/api/browse", handle_api_browse)

    log.info(f"🔥 Servidor iniciado en http://{HOST}:{PORT}")
    log.info(f"📱 Web App: {WEBAPP_URL}/web_app/index.html")
    log.info(f"🤖 Bot corriendo con polling")

    web.run_app(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
