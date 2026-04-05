# Gera backup do banco asg_db no container postgres-container
# Uso: .\scripts\backup.ps1
# Resultado: backup_asg_YYYYMMDD_HHmm.sql na pasta atual

$timestamp = Get-Date -Format "yyyyMMdd_HHmm"
$file = "backup_asg_$timestamp.sql"

Write-Host "Gerando backup em $file ..."
docker exec postgres-container pg_dump -U postgres asg_db | Out-File -FilePath $file -Encoding utf8

if ($LASTEXITCODE -eq 0) {
    $size = [math]::Round((Get-Item $file).Length / 1MB, 2)
    Write-Host "Backup concluido: $file ($size MB)"
} else {
    Write-Host "Erro ao gerar backup."
    exit 1
}
