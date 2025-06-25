$networkInterface = Get-NetAdapter | Where-Object {($_.Status -eq "Up") -and ($_.Name -like "*Wi-Fi*")} | Select-Object -First 1
if ($networkInterface) {
    $ipAddress = Get-NetIPAddress -InterfaceIndex $networkInterface.ifIndex -AddressFamily IPv4 | Select-Object -ExpandProperty IPAddress
    Write-Host "Detectado IP WiFi: $ipAddress"
} else {
    # Fallback para interface Ethernet se WiFi não estiver disponível
    $networkInterface = Get-NetAdapter | Where-Object {($_.Status -eq "Up") -and ($_.Name -like "*Ethernet*")} | Select-Object -First 1
    if ($networkInterface) {
        $ipAddress = Get-NetIPAddress -InterfaceIndex $networkInterface.ifIndex -AddressFamily IPv4 | Select-Object -ExpandProperty IPAddress
        Write-Host "Detectado IP Ethernet: $ipAddress"
    } else {
        $ipAddress = "localhost"
        Write-Host "Não foi possível detectar nenhum adaptador de rede ativo. Usando $ipAddress como padrão."
    }
}

Write-Host "Parando containers..."
docker compose down

Write-Host "Removendo imagens..."
docker image rm relatorio-expresso-fresh-backend relatorio-expresso-fresh-frontend -f

Write-Host "Limpando volumes desnecessários..."
docker volume prune -f

Write-Host "Limpando cache do Docker..."
docker builder prune -f

Write-Host "Reconstruindo com docker-compose usando IP: $ipAddress..."
$env:HOST_IP = $ipAddress
docker compose up --build

# O script continuará executando enquanto os containers estiverem em execução
