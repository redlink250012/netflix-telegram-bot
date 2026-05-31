#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Netflix Token Generator v4.0 - Direct API Edition
Genera tokens directamente desde la API interna de Netflix
"""

import os
import json
import requests
import time
from datetime import datetime
from urllib.parse import quote
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import warnings
warnings.filterwarnings("ignore")

console = Console()
COOKIES_FILE = "netflix_cookies.txt"

ANDROID_UA = (
    "com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; "
    "Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)"
)
GRAPHQL_ENDPOINT = "https://android13.prod.ftl.netflix.com/graphql"

# ============================================================================
# CARGAR COOKIES
# ============================================================================

def load_cookies():
    if not os.path.exists(COOKIES_FILE):
        template = """# Netflix Cookies - Edita este archivo con tus cookies
# Formato Netscape: dominio TAB flag TAB ruta TAB secure TAB expiracion TAB nombre TAB valor
# O formato simple: NOMBRE=VALOR (uno por linea)

SecureNetflixId=
NetflixId=
"""
        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            f.write(template)
        console.print(f"\n[yellow]⚠️  Archivo '{COOKIES_FILE}' creado[/yellow]")
        console.print("[yellow]📝 Editalo y pega tus cookies de Netflix[/yellow]")
        exit(1)

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
                name, value = line.split('=', 1)
                cookies[name.strip()] = value.strip()

    if not cookies:
        console.print("[red]❌ No se encontraron cookies en el archivo[/red]")
        exit(1)
    return cookies

# ============================================================================
# GENERAR TOKEN (DIRECTO - SIN API EXTERNA)
# ============================================================================

def generate_token(cookies_dict):
    payload = {
        "operationName": "CreateAutoLoginToken",
        "variables": {"scope": "WEBVIEW_MOBILE_STREAMING"},
        "extensions": {
            "persistedQuery": {
                "version": 102,
                "id": "76e97129-f4b5-41a0-a73c-12e674896849",
            }
        },
    }
    headers = {
        "User-Agent": ANDROID_UA,
        "Accept": "multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json",
        "Content-Type": "application/json",
        "Cookie": "; ".join(f"{k}={v}" for k, v in cookies_dict.items()),
    }
    try:
        r = requests.post(GRAPHQL_ENDPOINT, headers=headers, json=payload, timeout=20, verify=False)
        if r.status_code != 200:
            return None, f"API HTTP {r.status_code}"
        data = r.json()
        if "errors" in data and data["errors"]:
            return None, data["errors"][0].get("message", str(data["errors"]))
        token = data.get("data", {}).get("createAutoLoginToken")
        if token:
            return token, None
        return None, "No se encontro token en la respuesta"
    except requests.Timeout:
        return None, "Timeout conectando a Netflix"
    except requests.ConnectionError:
        return None, "Error de conexion con Netflix"
    except Exception as e:
        return None, str(e)[:80]

# ============================================================================
# INTERFAZ
# ============================================================================

def show_header():
    panel = Panel(
        Text("NETFLIX TOKEN GENERATOR v4.0", style="bold cyan"),
        subtitle=Text("Direct API Edition", style="dim cyan"),
        border_style="bright_blue", padding=(1, 2)
    )
    console.print(panel)

def show_token_info(token):
    url_encoded = quote(token, safe='')
    url = f"https://netflix.com/account?nftoken={url_encoded}"

    token_table = Table(title="TOKEN INFO", border_style="bright_blue", padding=(0, 1))
    token_table.add_column("Property", style="cyan")
    token_table.add_column("Value", style="green")
    token_table.add_row("Generated", datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
    token_table.add_row("Validity", "~59 minutes")
    token_table.add_row("Length", f"{len(token)} chars")
    console.print(token_table)
    console.print()

    url_panel = Panel(
        f"[bold cyan]{url}[/bold cyan]",
        title="LOGIN URL",
        border_style="bright_cyan", padding=(1, 2)
    )
    console.print(url_panel)
    console.print()

    # Copiar al portapapeles
    try:
        import subprocess
        subprocess.run(['powershell', '-Command', 'Set-Clipboard', '-Value', url], capture_output=True)
        console.print("[green]✓ URL copiada al portapapeles![/green]")
    except:
        pass

    # Guardar
    with open('NETFLIX_TOKEN.txt', 'w', encoding='utf-8') as f:
        f.write(token)
    with open('NETFLIX_URL.txt', 'w', encoding='utf-8') as f:
        f.write(url)
    console.print("[green]✓ Token guardado en NETFLIX_TOKEN.txt[/green]")
    console.print("[green]✓ URL guardada en NETFLIX_URL.txt[/green]")
    console.print()

    console.print("[cyan]Pega la URL en tu navegador (en incognito recomendado)[/cyan]")
    return url

# ============================================================================
# MAIN
# ============================================================================

def main():
    console.clear()
    show_header()

    cookies = load_cookies()
    console.print(f"[green]✓[/green] [cyan]{len(cookies)} cookies cargadas[/cyan]")
    console.print()

    with console.status("[bold cyan]Generando token...", spinner="dots"):
        token, error = generate_token(cookies)
        time.sleep(0.3)

    console.print()

    if token:
        show_token_info(token)
    else:
        console.print(f"[red]❌ Error: {error}[/red]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrumpido[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
