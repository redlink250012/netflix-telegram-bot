# Inicia tunel localhost.run + servidor bot
# Los procesos quedan independientes, cerralos manualmente

$dir = "E:\NUEVOS PROGRAMAS MIOS Y .PY\WorldWinner API Checker\netflix_telegram"
$tunnelLog = "$dir\tunnel.log"

Remove-Item $tunnelLog -ErrorAction SilentlyContinue

Write-Output "Iniciando tunel SSH a localhost.run..."
Start-Process -WindowStyle Hidden -FilePath "ssh" -ArgumentList @(
    "-o", "StrictHostKeyChecking=no",
    "-o", "ServerAliveInterval=30",
    "-R", "80:localhost:8080",
    "nokey@localhost.run"
) -RedirectStandardOutput $tunnelLog -WorkingDirectory $dir

Write-Output "Esperando URL del tunel..."
$url = $null
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $tunnelLog) {
        $content = Get-Content $tunnelLog -Raw
        $m = [regex]::Match($content, 'https://[a-z0-9]+\.lhr\.life')
        if ($m.Success) {
            $url = $m.Value
            break
        }
    }
}

if (-not $url) {
    Write-Output "ERROR: No se pudo obtener la URL del tunel"
    exit 1
}

Write-Output "URL publica: $url"

# Iniciar servidor
$env:BOT_TOKEN = "8487797010:AAFwo0KdJWy-Gu9tkpVic9CrEVs82S1b1CM"
$env:WEBAPP_URL = $url
$env:HOST = "0.0.0.0"
$env:PORT = "8080"

Write-Output "Iniciando servidor bot..."
Start-Process -WindowStyle Hidden -FilePath "python" -ArgumentList @("-u", "bot.py") -WorkingDirectory $dir

Start-Sleep -Seconds 4

Write-Output ""
Write-Output "=================================="
Write-Output "  SISTEMA INICIADO"
Write-Output "=================================="
Write-Output ""
Write-Output "  1. Abri Telegram"
Write-Output "  2. Envia /start a @HMC_VERIFICADOR_bot"
Write-Output "  3. Toca 'Abrir Netflix Checker'"
Write-Output "  4. Pega tus cookies y usa Netflix"
Write-Output ""
Write-Output "  Mini App URL: $url/web_app/index.html"
Write-Output ""
Write-Output "  Para detener:"
Write-Output "    taskkill /f /im python.exe"
Write-Output "    taskkill /f /im ssh.exe"
Write-Output "=================================="
Write-Output ""
