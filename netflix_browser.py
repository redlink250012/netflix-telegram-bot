"""
Netflix Browser - Abre Netflix directamente con tus cookies
"""
import json, os, time
from playwright.sync_api import sync_playwright

COOKIES_FILE = "netflix_cookies.txt"

def load_cookies_playwright():
    cookies_pl = []
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
                    name = parts[5].strip()
                    value = parts[6].strip()
                    cookies_pl.append({
                        "name": name,
                        "value": value,
                        "domain": ".netflix.com",
                        "path": "/",
                        "httpOnly": name in ('NetflixId', 'SecureNetflixId'),
                        "secure": True,
                        "sameSite": "Lax",
                    })
    return cookies_pl

def main():
    print("[*] Cargando cookies...")
    cookies = load_cookies_playwright()
    if not cookies:
        print("[-] No hay cookies en", COOKIES_FILE)
        return
    print(f"[*] {len(cookies)} cookies cargadas")
    
    print("[*] Abriendo navegador...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
        )
        
        context.add_cookies(cookies)
        page = context.new_page()
        
        print("[*] Navegando a Netflix...")
        page.goto("https://www.netflix.com/account")
        time.sleep(2)
        
        print("[+] Navegador abierto. Netflix ya esta logueado con tus cookies.")
        print("[*] Presioná Ctrl+C en la terminal para cerrar.")
        print()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            browser.close()
            print("[*] Navegador cerrado.")

if __name__ == "__main__":
    main()
