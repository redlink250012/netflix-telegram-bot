#!/usr/bin/env python3
"""
Netflix Account Tool - Version todo-en-uno
Verifica cookies, muestra info de cuenta y genera acceso.
"""
import os, re, json, webbrowser
from urllib.parse import quote
from netflix_checker import check_cookies

COOKIES_FILE = "netflix_cookies.txt"

def load_cookies_from_file():
    cookies = {}
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

def main():
    if not os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            f.write("# Pega tus cookies de Netflix aqui\n# Formato: NOMBRE=VALOR\nSecureNetflixId=\nNetflixId=\n")
        print(f"[-] Archivo '{COOKIES_FILE}' creado. Editalo con tus cookies.")
        return

    cookies = load_cookies_from_file()
    if not cookies:
        print("[-] No se encontraron cookies en", COOKIES_FILE)
        return

    cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())
    print(f"[*] Cookies cargadas: {len(cookies)}")
    print()

    result = check_cookies(cookie_str)

    if not result['valid']:
        print(f"[-] Cookies invalidas: {result.get('error', 'error desconocido')}")
        return

    info = result.get('account_info', {})
    token = result.get('token', '')
    token_url = result.get('token_url', '')

    print("=" * 55)
    print("  CUENTA NETFLIX - VERIFICADA")
    print("=" * 55)
    print(f"  Email:     {info.get('email', 'N/A')}")
    print(f"  Pais:      {info.get('country', 'N/A')}")
    print(f"  Estado:    {info.get('membership_status', 'N/A')}")
    print(f"  Owner:     {'SI' if info.get('is_owner') else 'NO'}")
    print(f"  Activa:    {'SI' if info.get('is_active') else 'NO'}")
    print(f"  Pago:      {info.get('payment_method', 'N/A')}")
    print(f"  Plan:      {info.get('plan', 'N/A')}")
    print()

    perfiles = info.get('profiles', [])
    if perfiles:
        print(f"  Perfiles ({len(perfiles)}):")
        for p in perfiles[:6]:
            print(f"    - {p}")
    print()

    print("-" * 55)
    print("  ACCESO DIRECTO:")
    print()
    print("  Las cookies son validas. Podes:")
    print()
    print("  1) Usar un exportador de cookies (Cookie-Editor extension)")
    print("     para importarlas en tu navegador")
    print()
    print("  2) O abrir Netflix directamente con este link:")
    print()

    if token:
        clean_url = f"https://netflix.com/account?nftoken={token}"
        encoded_url = f"https://netflix.com/account?nftoken={quote(token, safe='')}"
        print(f"     {encoded_url}")
        print()
        print("  (NOTA: Token valido ~59min. Si no funciona, usa")
        print("   el metodo 1 de exportar cookies en tu navegador)")

        with open('netflix_access_url.txt', 'w') as f:
            f.write(encoded_url)
        print(f"\n  [Link guardado en netflix_access_url.txt]")

        try:
            import subprocess
            subprocess.run(['powershell', '-Command', 'Set-Clipboard', '-Value', encoded_url], capture_output=True)
            print("  [Link copiado al portapapeles]")
        except:
            pass
    else:
        print("     (Usa las cookies directamente en tu navegador)")

    print()

if __name__ == '__main__':
    main()
