"""
Netflix Mini App Launcher
Inicia el server + tunel SSH + configura el bot
Solo ejecutar: python launcher.py
"""
import subprocess, sys, os, time, re, signal, atexit, threading

DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(DIR)
LOG = os.path.join(DIR, 'launcher.log')

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

# Quitar logs viejos
for f in ['launcher.log', 'tunnel.log', 'server.log']:
    try:
        os.remove(os.path.join(DIR, f))
    except:
        pass

# 1. Iniciar servidor PRIMERO (para que el tunel encuentre el puerto abierto)
log('Iniciando servidor bot...')
env = os.environ.copy()
env['BOT_TOKEN'] = '8487797010:AAFwo0KdJWy-Gu9tkpVic9CrEVs82S1b1CM'
env['WEBAPP_URL'] = 'http://localhost:8080'
env['HOST'] = '0.0.0.0'
env['PORT'] = '8080'
server = subprocess.Popen(
    [sys.executable, '-u', 'bot.py'],
    stdout=open('server.log', 'w'), stderr=subprocess.STDOUT, env=env
)
time.sleep(4)

# Verificar que el servidor esta respondiendo
try:
    import requests
    r = requests.get('http://localhost:8080/', timeout=5)
    log(f'Servidor OK en puerto 8080')
except:
    log('ERROR: Servidor no responde en puerto 8080')
    server.kill()
    input('Presiona Enter para salir...')
    sys.exit(1)

# 2. Iniciar tunel cloudflared
log('Iniciando tunel cloudflared...')
tunnel_log_path = os.path.join(DIR, 'tunnel.log')
cloudflared_path = r'C:\Users\djred\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe'
tunnel = subprocess.Popen(
    [cloudflared_path, 'tunnel', '--url', 'http://localhost:8080'],
    stdout=open(tunnel_log_path, 'w'), stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
)

# 3. Esperar URL
url = None
for i in range(40):
    time.sleep(1)
    try:
        with open(tunnel_log_path, 'r') as f:
            content = f.read()
        m = re.search(r'(https://[a-z0-9-]+\.trycloudflare\.com)', content)
        if m:
            url = m.group(1)
            break
    except:
        pass

if not url:
    log('ERROR: No se obtuvo URL del tunel')
    try:
        with open(tunnel_log_path, 'r') as f:
            log('LOG: ' + f.read().replace('\n', ' | '))
    except:
        pass
    tunnel.kill()
    input('Presiona Enter para salir...')
    sys.exit(1)

log(f'URL publica: {url}')

# 4. Actualizar WEBAPP_URL en el servidor via API de Telegram
log(f'Configurando bot con URL: {url}')

# 5. Configurar bot (menu button)
log('Configurando bot en Telegram...')
try:
    import requests
    r = requests.post(
        f'https://api.telegram.org/bot8487797010:AAFwo0KdJWy-Gu9tkpVic9CrEVs82S1b1CM/setChatMenuButton',
        json={'menu_button': {'type': 'web_app', 'text': 'Abrir Netflix',
              'web_app': {'url': f'{url}/web_app/index.html'}}},
        timeout=10
    )
    if r.json().get('ok'):
        log('Menu button actualizado OK')
    else:
        log(f'Error API: {r.json()}')
except Exception as e:
    log(f'Error configurando bot: {e}')

# 6. Verificar tunel
time.sleep(3)
log('Verificando tunel...')
for intento in range(5):
    try:
        r = requests.get(f'{url}/', timeout=10)
        if r.status_code == 200:
            log(f'Tunel OK - respuesta: {r.text[:50]}')
            break
        else:
            log(f'Intento {intento+1}: status {r.status_code}')
    except Exception as e:
        if intento < 4:
            log(f'Intento {intento+1}: {str(e)[:60]}, reintentando...')
            time.sleep(2)
        else:
            log(f'ERROR: No se puede acceder al tunel: {e}')
            log('Revisa tunnel.log para mas detalles')

log('')
log('=' * 55)
log('  SISTEMA INICIADO CORRECTAMENTE')
log('=' * 55)
log('')
log(f'  Mini App URL: {url}/web_app/index.html')
log('')
log('  1. Abri Telegram en tu celular')
log('  2. Busca @HMC_VERIFICADOR_bot')
log('  3. Toca el boton "Abrir Netflix" en el menu')
log('  4. Pega tus cookies y toca "Ingresar"')
log('  5. Toca "▶ Abrir Netflix" para abrir Netflix')
log('')
log('  (Android: funciona dentro del WebView de Telegram)')
log('  (Desktop: anda a la Mini App URL directo desde Chrome)')
log('')
log('  Deja esta ventana abierta mientras uses la app.')
log('  Presiona Ctrl+C para detener todo.')
log('')

def cleanup():
    log('Deteniendo...')
    for p in [server, tunnel]:
        try:
            p.kill()
        except:
            pass
    log('Detenido.')

atexit.register(cleanup)
signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))

try:
    while True:
        time.sleep(5)
        if tunnel.poll() is not None:
            log('ATENCION: Tunel caido!')
            log('Reinicia el launcher para reconectar.')
            break
        if server.poll() is not None:
            log('ATENCION: Servidor caido!')
            break
except KeyboardInterrupt:
    pass
finally:
    cleanup()
