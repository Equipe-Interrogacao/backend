# Cria o volume externo protegido do PostgreSQL.
# Execute UMA VEZ antes do primeiro "docker compose up".
# Volumes externos NAO sao apagados pelo "docker compose down -v".

$volumeName = "asg_db_data"

$exists = docker volume ls --format "{{.Name}}" | Where-Object { $_ -eq $volumeName }
if ($exists) {
    Write-Host "Volume '$volumeName' ja existe. Nenhuma acao necessaria."
} else {
    docker volume create $volumeName
    Write-Host "Volume '$volumeName' criado com sucesso."
}
