"""
Exporta las cookies en formatos listos para importar en el navegador
"""
import json, os

COOKIES_FILE = "netflix_cookies.txt"

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

if not cookies:
    print("No hay cookies en", COOKIES_FILE)
    exit(1)

# 1) Formato RAW (para pegar en Cookie-Editor import JSON)
json_format = []
for name, value in cookies.items():
    json_format.append({
        "domain": "netflix.com",
        "name": name,
        "value": value,
        "path": "/",
        "secure": True,
        "httpOnly": True if name in ('NetflixId', 'SecureNetflixId') else False,
        "hostOnly": False,
        "sameSite": "no_restriction",
    })

with open('cookies_netflix.json', 'w', encoding='utf-8') as f:
    json.dump(json_format, f, indent=2)

# 2) Formato Netscape
with open('cookies_netflix_netscape.txt', 'w', encoding='utf-8') as f:
    f.write("# Netscape HTTP Cookie File\n")
    f.write("# https://curl.haxx.se/rfc/cookie_spec.html\n")
    f.write("# Importá este archivo con Cookie-Editor (Import > Netscape)\n\n")
    for name, value in cookies.items():
        f.write(f".netflix.com\tTRUE\t/\tTRUE\t9999999999\t{name}\t{value}\n")

# 3) Formato URL (para pegar en la barra y que los redirija)
cookie_pairs = [f"{k}={v}" for k, v in cookies.items()]
raw_cookie_str = "; ".join(cookie_pairs)

print("=" * 60)
print("  COOKIES EXPORTADAS - 3 FORMATOS")
print("=" * 60)
print()
print(f"  Cookies encontradas: {len(cookies)}")
print(f"  NetflixId:     {'SI' if 'NetflixId' in cookies else 'NO'}")
print(f"  SecureNetflixId: {'SI' if 'SecureNetflixId' in cookies else 'NO'}")
print()
print("  Archivos generados:")
print(f"  1. cookies_netflix.json        (para Cookie-Editor)")
print(f"  2. cookies_netflix_netscape.txt (formato Netscape)")
print()
print("  COMO USAR:")
print("  1. Instala 'Cookie-Editor' extension en Chrome")
print("  2. Andá a https://netflix.com")
print("  3. Abri Cookie-Editor > Import > JSON")
print("  4. Selecciona cookies_netflix.json")
print("  5. Refresca la pagina - ya estas logueado")
print()
print("  O copia esto y pegalo en Cookie-Editor > Import > Paste:")
print()
print(json.dumps(json_format, indent=2))
