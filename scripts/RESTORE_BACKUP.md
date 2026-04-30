# Restaurar Backup no PostgreSQL (Docker)

Guia para copiar um arquivo de backup para dentro do contêiner `postgres-container` e restaurar o banco `asg_db`.

> **Pré-requisito:** o contêiner precisa estar rodando.  
> Verifique com: `docker ps | findstr postgres-container`

---

## Referência rápida

| Dado           | Valor                  |
|:---------------|:-----------------------|
| Contêiner      | `postgres-container`   |
| Banco          | `asg_db`               |
| Usuário        | `postgres`             |
| Senha          | `postgres`             |
| Diretório tmp  | `/tmp/` (dentro do contêiner) |

---

## Método 1 — Script automático (recomendado)

```powershell
.\scripts\restore.ps1 -file backup_asg_20260101_1200.sql
```

O script lê o arquivo localmente e envia direto ao `psql` via `stdin` — **não copia nada para dentro do contêiner**.

---

## Método 2 — Copiar o arquivo para dentro do contêiner e restaurar

Use quando o arquivo for grande e você preferir que o `psql` leia direto do disco do contêiner (sem pipe).

### Passo 1 — Copiar o backup para `/tmp/` do contêiner

**PowerShell:**
```powershell
docker cp backup_asg_20260101_1200.sql postgres-container:/tmp/backup.sql
```

**bash / WSL:**
```bash
docker cp backup_asg_20260101_1200.sql postgres-container:/tmp/backup.sql
```

Confirme que o arquivo chegou:
```powershell
docker exec postgres-container ls -lh /tmp/backup.sql
```

---

### Passo 2 — Restaurar a partir de dentro do contêiner

```powershell
docker exec -i postgres-container psql -U postgres -d asg_db -f /tmp/backup.sql
```

> A flag `-f` faz o `psql` ler o arquivo direto do disco, sem pipe.

---

### Passo 3 — Remover o arquivo temporário (opcional)

```powershell
docker exec postgres-container rm /tmp/backup.sql
```

---

## Método 3 — Backup em formato binário (`.dump`)

Se o backup foi gerado com `pg_dump -Fc` (formato custom/binário), use `pg_restore` em vez de `psql`.

### Copiar o arquivo
```powershell
docker cp backup_asg.dump postgres-container:/tmp/backup.dump
```

### Restaurar com `pg_restore`

```powershell
docker exec -i postgres-container pg_restore -U postgres -d asg_db --clean --if-exists /tmp/backup.dump
```

| Flag | O que faz |
|:-----|:----------|
| `--clean` | Dropa os objetos existentes antes de recriar |
| `--if-exists` | Não falha se o objeto não existir (evita erros no primeiro restore) |

---

## Resetar o banco antes de restaurar (banco limpo)

Se quiser garantir um banco zerado antes do restore:

```powershell
# 1. Conectar e dropar/recriar
docker exec -i postgres-container psql -U postgres -c "DROP DATABASE IF EXISTS asg_db;"
docker exec -i postgres-container psql -U postgres -c "CREATE DATABASE asg_db;"

# 2. Recriar a extensão PostGIS (necessária para geometrias)
docker exec -i postgres-container psql -U postgres -d asg_db -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# 3. Restaurar
docker cp backup_asg_20260101_1200.sql postgres-container:/tmp/backup.sql
docker exec -i postgres-container psql -U postgres -d asg_db -f /tmp/backup.sql
```

---

## Gerar um novo backup

```powershell
.\scripts\backup.ps1
```

Ou manualmente:

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmm"
docker exec postgres-container pg_dump -U postgres asg_db | Out-File -FilePath "backup_asg_$ts.sql" -Encoding utf8
```

---

## Verificar o restore

Acesse o banco e confirme os dados:

```powershell
docker exec -it postgres-container psql -U postgres -d asg_db
```

Comandos úteis dentro do `psql`:

```sql
-- Listar tabelas
\dt

-- Contar registros por tabela
SELECT count(*) FROM propriedades;
SELECT count(*) FROM desmatamento_prodes;
SELECT count(*) FROM alerta_deter;
SELECT count(*) FROM foco_queimada;

-- Sair
\q
```

---

## Solução de problemas

| Sintoma | Causa provável | Solução |
|:--------|:---------------|:--------|
| `could not connect to server` | Contêiner não está rodando | `docker compose up -d postgres` |
| `role "postgres" does not exist` | Banco iniciou sem as variáveis de ambiente | Recriar o contêiner com `docker compose up --build postgres` |
| `ERROR: extension "postgis" does not exist` | PostGIS não instalado no banco de destino | `CREATE EXTENSION IF NOT EXISTS postgis;` |
| `psql: error: FATAL: database "asg_db" does not exist` | Banco foi dropado | `CREATE DATABASE asg_db;` |
| Arquivo `.sql` com encoding errado (PowerShell) | `Out-File` gerou UTF-16 | Use `Encoding utf8` ou `pg_dump > arquivo.sql` no bash/WSL |
