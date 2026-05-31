@echo off
cd /d "E:\NUEVOS PROGRAMAS MIOS Y .PY\WorldWinner API Checker\netflix_telegram"
setlocal enabledelayedexpansion

echo ====================================
echo  Netflix Mini App - Iniciar
echo ====================================
echo.

REM Kill old processes
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im ssh.exe >nul 2>&1
timeout /t 2 >nul

REM Start server
echo [1/3] Iniciando servidor...
set BOT_TOKEN=8487797010:AAFwo0KdJWy-Gu9tkpVic9CrEVs82S1b1CM
set WEBAPP_URL=http://localhost:8080
set HOST=0.0.0.0
set PORT=8080
start /B python -u bot.py > server.log 2>&1
timeout /t 4 >nul
curl.exe -s http://localhost:8080/ >nul && echo   OK - Servidor corriendo en puerto 8080

REM Start tunnel and capture URL
echo.
echo [2/3] Iniciando tunel publico...
set TUNNEL_LOG=tunnel.log
type nul > %TUNNEL_LOG%

REM Start SSH tunnel in background
start /B ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -R 80:localhost:8080 nokey@localhost.run > %TUNNEL_LOG% 2>&1

REM Wait for URL
set URL=
for /l %%i in (1,1,20) do (
    timeout /t 1 >nul
    for /f "tokens=*" %%a in ('findstr "https://" %TUNNEL_LOG% 2^>nul') do (
        set LINE=%%a
        echo !LINE! | findstr /C:"lhr.life" >nul
        if !errorlevel! equ 0 (
            for /f "tokens=3" %%b in ("!LINE!") do set URL=%%b
        )
    )
    if not "!URL!"=="" goto :goturl
)
echo   ERROR: No se pudo obtener la URL del tunel
echo   Revisa tunnel.log para mas detalles
goto :end

:goturl
echo   Tunel URL: !URL!

REM Update bot menu button via Telegram API
echo.
echo [3/3] Configurando bot...
curl.exe -s -X POST "https://api.telegram.org/bot%BOT_TOKEN%/setChatMenuButton" ^
  -H "Content-Type: application/json" ^
  -d "{\"menu_button\":{\"type\":\"web_app\",\"text\":\"Abrir Netflix\",\"web_app\":{\"url\":\"!URL!/web_app/index.html\"}}}" >nul

curl.exe -s -X POST "https://api.telegram.org/bot%BOT_TOKEN%/setMyDescription" ^
  -H "Content-Type: application/json" ^
  -d "{\"description\":\"Mini app para acceder a Netflix con cookies\"}" >nul

echo.
echo ====================================
echo  LISTO!
echo ====================================
echo.
echo  Abri Telegram y busca @HMC_VERIFICADOR_bot
echo  Toca el boton "Abrir Netflix" en el menu
echo.
echo  O usa la URL directa:
echo  !URL!/web_app/index.html
echo.
echo  IMPORTANTE: NO cierres esta ventana
echo  mientras uses la mini app.
echo.
echo  Para salir, cerra esta ventana.
echo ====================================
echo.

REM Keep tunnel alive
:keepalive
timeout /t 10 >nul
findstr /C:"closed" %TUNNEL_LOG% >nul 2>&1
if !errorlevel! equ 0 (
    echo.
    echo [!date! !time!] Tunel caido! Reconectando...
    goto :start_tunnel
)
goto :keepalive

:end
pause
