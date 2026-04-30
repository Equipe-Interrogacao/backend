#!/bin/bash
# Executado automaticamente pelo postgres na PRIMEIRA inicialização do volume.
# Dropa e recria o banco para restaurar o backup limpo.

set -e

echo "[init-restore] Removendo banco existente para restauração limpa..."
psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"
psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB;"

echo "[init-restore] Restaurando backup (pode levar alguns minutos)..."
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /tmp/backup_asg.sql

echo "[init-restore] Restauração concluída."
