# Restaura um backup SQL no banco asg_db
# Uso: .\scripts\restore.ps1 -file backup_asg_20260101_1200.sql

param(
    [Parameter(Mandatory=$true)]
    [string]$file
)

if (-not (Test-Path $file)) {
    Write-Host "Arquivo nao encontrado: $file"
    exit 1
}

Write-Host "Restaurando $file no banco asg_db ..."
Get-Content $file | docker exec -i postgres-container psql -U postgres -d asg_db

if ($LASTEXITCODE -eq 0) {
    Write-Host "Restore concluido."
} else {
    Write-Host "Erro durante o restore."
    exit 1
}
