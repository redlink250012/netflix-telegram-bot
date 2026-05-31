"""
Netflix Universal Access Tool
Todo en uno: verificar, exportar cookies, QR, token Android y abrir navegador
"""
import os, re, json, sys, time, webbrowser
from urllib.parse import quote

warnings.filterwarnings("ignore")

COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "netflix_cookies.txt")
GRAPHQL = "https://android13.prod.ftl.netflix.com/graphql"
ANDROID_UA = "com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)"

try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False

OS = 'android' if sys.platform == 'linux' and 'android' in os.environ.get('TERMUX_VERSION', '').lower() else 'windows' if sys.platform == 'win32' else 'other'
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))

def load_cookies():
    cookies = {}
    if not os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            f.write("# Netflix Cookies - pega tus cookies aqui\n# Formato: NOMBRE=VALOR\nSecureNetflixId=\nNetflixId=\n")
        print(f"[-] Archivo '{COOKIES_FILE}' creado. Editalo con tus cookies.")
        return None

    with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('#HttpOnly_'):
                line = line[10:]
            if '.netflix.com' in line:
                parts = line.split('\t')
                if len(parts) >= 7:
                    cookies[parts[5].strip()] = parts[6].strip()
            elif '=' in line and not line.startswith('.'):
                n, v = line.split('=', 1)
                cookies[n.strip()] = v.strip()
    return cookies

def get_cookie_str(cookies):
    return '; '.join(f'{k}={v}' for k, v in cookies.items())

def verify_account(cookies):
    cookie_str = get_cookie_str(cookies)
    headers = {
        'User-Agent': 'com.netflix.mediaclient/63884',
        'Cookie': cookie_str,
        'Accept': 'application/json',
    }
    payload = {
        'operationName': 'Account',
        'variables': {},
        'extensions': {'persistedQuery': {'version': 102, 'id': '1b35e6dc1d7d236488270a1c4626d19f9872ba4e39a44209f09e4cbbea95f9da'}}
    }
    r = requests.post(GRAPHQL, headers=headers, json=payload, verify=False, timeout=15)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    data = r.json()
    if 'errors' in data:
        return None, data['errors'][0].get('message', str(data['errors']))
    return data.get('data', {}).get('account', {}), None

def generate_token(cookies):
    cookie_str = get_cookie_str(cookies)
    headers = {
        'User-Agent': ANDROID_UA,
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Cookie': cookie_str,
    }
    payload = {
        'operationName': 'CreateAutoLoginToken',
        'variables': {'scope': 'WEBVIEW_MOBILE_STREAMING'},
        'extensions': {'persistedQuery': {'version': 102, 'id': '76e97129-f4b5-41a0-a73c-12e674896849'}}
    }
    r = requests.post(GRAPHQL, headers=headers, json=payload, verify=False, timeout=15)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    data = r.json()
    if 'errors' in data:
        return None, data['errors'][0].get('message', str(data['errors']))
    return data['data']['createAutoLoginToken'], None

def export_cookies_json(cookies):
    json_format = []
    for name, value in cookies.items():
        json_format.append({
            "domain": "netflix.com",
            "name": name,
            "value": value,
            "path": "/",
            "secure": True,
            "httpOnly": name in ('NetflixId', 'SecureNetflixId'),
            "hostOnly": False,
            "sameSite": "no_restriction",
        })
    path = os.path.join(TEMP_DIR, 'cookies_netflix.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(json_format, f, indent=2)
    return path, json_format

def export_cookies_netscape(cookies):
    lines = ["# Netscape HTTP Cookie File\n"]
    for name, value in cookies.items():
        lines.append(f".netflix.com\tTRUE\t/\tTRUE\t9999999999\t{name}\t{value}\n")
    path = os.path.join(TEMP_DIR, 'cookies_netflix_netscape.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    return path

def show_qr(text):
    if not HAS_QR:
        return
    qr = qrcode.QRCode(box_size=2, border=1)
    qr.add_data(text)
    qr.make(fit=True)
    qr.print_ascii(invert=True)

def show_title(text):
    if HAS_RICH:
        console.print(Panel(Text(text, style="bold cyan"), border_style="bright_blue", padding=(1, 2)))
    else:
        print(f"\n{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}")

def show_info(label, value, color='green'):
    if HAS_RICH:
        console.print(f"  [cyan]{label}:[/cyan] [{color}]{value}[/{color}]")
    else:
        print(f"  {label}: {value}")

def show_account_info(info):
    show_title("CUENTA NETFLIX")
    show_info("Email", info.get('email', 'N/A'))
    show_info("Pais", info.get('country', 'N/A'))
    show_info("Estado", info.get('membership_status', 'N/A'))
    show_info("Owner", 'SI' if info.get('is_owner') else 'NO')
    show_info("Activa", 'SI' if info.get('is_active') else 'NO')
    show_info("Pago", info.get('payment_method', 'N/A'))
    show_info("Plan", info.get('plan', 'N/A'))

    perfiles = info.get('profiles', [])
    if perfiles:
        print()
        show_info("Perfiles", f"{len(perfiles)}")
        for p in perfiles[:6]:
            print(f"      - {p}")
    print()

def menu():
    show_title("NETFLIX UNIVERSAL ACCESS TOOL")
    print("  1) Ver cuenta + exportar cookies")
    print("  2) Generar token Android + QR")
    print("  3) Abrir Netflix en navegador (desktop)")
    print("  4) Hacer TODO (verificar + exportar + QR + navegador)")
    print("  0) Salir")
    print()

def do_all(cookies):
    info, err = verify_account(cookies)
    if info:
        show_account_info(info)
    else:
        print(f"[-] Error verificando cuenta: {err}")
        print("[-] Las cookies pueden haber expirado.\n")

    show_title("EXPORTANDO COOKIES")
    json_path, json_data = export_cookies_json(cookies)
    netscape_path = export_cookies_netscape(cookies)
    print(f"  JSON:     {json_path}")
    print(f"  Netscape: {netscape_path}")
    print()
    print(f"  Como usar: Abri Cookie-Editor > Import > JSON")
    print(f"  y selecciona cookies_netflix.json")
    print()

    total_cookies = len(cookies)
    has_nf = 'NetflixId' in cookies
    has_snf = 'SecureNetflixId' in cookies
    show_info("Cookies", f"{total_cookies} (NetflixId: {'SI' if has_nf else 'NO'}, SecureNetflixId: {'SI' if has_snf else 'NO'})")
    print()

    show_title("TOKEN ANDROID + QR")
    token, err = generate_token(cookies)
    if token:
        url = f"https://www.netflix.com/account?nftoken={quote(token, safe='')}"
        print(f"  Token: {token[:40]}...")
        print(f"  URL:   {url}")
        print()
        print("  Escaneá el QR desde tu Android:")
        show_qr(url)
        print()

        url_path = os.path.join(TEMP_DIR, 'netflix_access_url.txt')
        with open(url_path, 'w') as f:
            f.write(url)
        print(f"  URL guardada en: {url_path}")
        print()
    else:
        print(f"  [-] Error generando token: {err}")
        print()

    if OS == 'windows':
        show_title("ABRIENDO NAVEGADOR")
        try:
            from playwright.sync_api import sync_playwright
            cookies_pl = []
            for name, value in cookies.items():
                cookies_pl.append({
                    "name": name, "value": value,
                    "domain": ".netflix.com", "path": "/",
                    "httpOnly": name in ('NetflixId', 'SecureNetflixId'),
                    "secure": True, "sameSite": "Lax",
                })
            print("  Abriendo Chrome con sesion iniciada...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    viewport={"width": 1280, "height": 720},
                )
                context.add_cookies(cookies_pl)
                page = context.new_page()
                page.goto("https://www.netflix.com/account")
                print("  [+] Navegador abierto. Cerra la terminal para salir.")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
                finally:
                    browser.close()
        except ImportError:
            print("  [-] playwright no instalado. 'pip install playwright'")
        except Exception as e:
            print(f"  [-] Error: {e}")

choices = {
    '1': lambda c: (lambda info: (show_account_info(info) if info else print(f"[-] Error: {err}")) if (info := verify_account(c)[0]) is not None else print(f"[-] Error: {verify_account(c)[1]}"))(c) or (export_cookies_json(c), export_cookies_netscape(c), print(f"\n  Cookies exportadas a cookies_netflix.json y cookies_netflix_netscape.txt\n"), None),
    '2': lambda c: (lambda t, u: (print(f"  Token: {t[:40]}...\n  URL:   {u}\n"), show_qr(u), None) if t else print(f"  [-] Error: {u}"))(*((token := generate_token(c))[0], f"https://www.netflix.com/account?nftoken={quote(token[0], safe='')}") if token[0] else (None, token[1])),
}

if __name__ == '__main__':
    import requests, warnings
    cookies = load_cookies()
    if not cookies:
        sys.exit(1)

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == '--all':
            do_all(cookies)
        elif arg == '--verify':
            info, err = verify_account(cookies)
            if info:
                show_account_info(info)
            else:
                print(f"Error: {err}")
        elif arg == '--token':
            token, err = generate_token(cookies)
            if token:
                url = f"https://www.netflix.com/account?nftoken={quote(token, safe='')}"
                print(url)
        elif arg == '--export':
            json_path, _ = export_cookies_json(cookies)
            netscape_path = export_cookies_netscape(cookies)
            print(f"JSON: {json_path}")
            print(f"Netscape: {netscape_path}")
        elif arg == '--browser':
            do_all(cookies)
        else:
            print(f"Usage: {sys.argv[0]} [--all|--verify|--token|--export|--browser]")
        sys.exit(0)

    while True:
        menu()
        op = input("  Opcion: ").strip()
        print()

        if op == '0':
            print("  Bye!")
            break
        elif op == '1':
            info, err = verify_account(cookies)
            if info:
                show_account_info(info)
            else:
                print(f"  [-] Error: {err}")
            json_path, _ = export_cookies_json(cookies)
            netscape_path = export_cookies_netscape(cookies)
            print(f"  Cookies exportadas:")
            print(f"    {json_path}")
            print(f"    {netscape_path}")
            print()
        elif op == '2':
            token, err = generate_token(cookies)
            if token:
                url = f"https://www.netflix.com/account?nftoken={quote(token, safe='')}"
                print(f"  URL: {url}\n")
                show_qr(url)
                print()
                with open(os.path.join(TEMP_DIR, 'netflix_access_url.txt'), 'w') as f:
                    f.write(url)
            else:
                print(f"  [-] Error: {err}")
        elif op == '3':
            try:
                from playwright.sync_api import sync_playwright
                cookies_pl = []
                for name, value in cookies.items():
                    cookies_pl.append({
                        "name": name, "value": value,
                        "domain": ".netflix.com", "path": "/",
                        "httpOnly": name in ('NetflixId', 'SecureNetflixId'),
                        "secure": True, "sameSite": "Lax",
                    })
                print("  Abriendo Chrome...")
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=False)
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        viewport={"width": 1280, "height": 720},
                    )
                    context.add_cookies(cookies_pl)
                    page = context.new_page()
                    page.goto("https://www.netflix.com/account")
                    print("  [+] Navegador abierto.")
                    try:
                        while True:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        pass
                    finally:
                        browser.close()
            except ImportError:
                print("  [-] playwright no instalado. 'pip install playwright'")
                print("  [-] Instala con: pip install playwright && playwright install chromium")
            except Exception as e:
                print(f"  [-] Error: {e}")
        elif op == '4':
            do_all(cookies)
        else:
            print("  Opcion invalida\n")

        if op != '0':
            input("  Presiona Enter para continuar...")
            print()
