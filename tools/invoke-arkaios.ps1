param(
    [Parameter(Mandatory = $true)]
    [string]$Text,

    [ValidateSet("ask", "puter", "computer")]
    [string]$Mode = "ask",

    [string]$ChannelId = "neuro-login",
    [string]$ConversationId = "",
    [switch]$AutoExecute,
    [int]$WaitSeconds = 30,
    [string]$BridgeUrl = "http://127.0.0.1:8000/local-bridge"
)

$ErrorActionPreference = "Stop"

if (!$ConversationId) {
    $ConversationId = "conv-" + [guid]::NewGuid().ToString()
}

$tokenPath = Join-Path $env:LOCALAPPDATA "NeuralAgent\local_bridge_token.txt"
if (!(Test-Path $tokenPath)) {
    throw "No encontre token local: $tokenPath. Arranca ARKAIOS NUCLEO primero."
}

$token = (Get-Content $tokenPath -Raw).Trim()
$headers = @{ "X-Bridge-Token" = $token }
$bridge = $BridgeUrl.TrimEnd("/")

$payload = @{
    channel_id = $ChannelId
    conversation_id = $ConversationId
    payload = @{
        source = $ChannelId
        mode = $Mode
        text = $Text
        auto_execute = [bool]$AutoExecute
        created_by = "invoke-arkaios.ps1"
    }
} | ConvertTo-Json -Depth 8

$queued = Invoke-RestMethod `
    -Uri "$bridge/messages/inbox" `
    -Method Post `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $payload `
    -TimeoutSec 10

Write-Host "Mensaje enviado a ARKAIOS." -ForegroundColor Green
Write-Host "Channel: $ChannelId"
Write-Host "Conversation: $ConversationId"
Write-Host "MessageId: $($queued.id)"

if ($WaitSeconds -le 0) {
    return
}

$deadline = (Get-Date).AddSeconds($WaitSeconds)
do {
    Start-Sleep -Seconds 2
    $outbox = Invoke-RestMethod `
        -Uri "$bridge/messages/outbox?channel_id=$([uri]::EscapeDataString($ChannelId))" `
        -Headers $headers `
        -TimeoutSec 10

    $match = @($outbox.messages | Where-Object { $_.conversation_id -eq $ConversationId })
    if ($match.Count -gt 0) {
        foreach ($message in $match) {
            $message.payload | ConvertTo-Json -Depth 10
            Invoke-RestMethod `
                -Uri "$bridge/messages/outbox/$($message.id)/ack" `
                -Method Post `
                -Headers $headers `
                -ContentType "application/json" `
                -Body (@{ status = "read" } | ConvertTo-Json) `
                -TimeoutSec 10 | Out-Null
        }
        return
    }
} while ((Get-Date) -lt $deadline)

Write-Host "Sin respuesta aun. El mensaje queda en cola si ARKAIOS/Puter no esta abierto." -ForegroundColor Yellow
