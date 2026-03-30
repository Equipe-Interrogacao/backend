# Backend — ASG Rural Properties

Documentação de inicialização e uso para desenvolvedores.

> **Ambiente:** os comandos abaixo usam **PowerShell** (Windows). Onde houver variação entre PowerShell e bash/WSL, ambos são indicados.

---

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/) instalado e rodando
- Git

---

## 1. Configurar variáveis de ambiente

Crie o arquivo `.env` a partir do exemplo:

**PowerShell:**
```powershell
Copy-Item .env.exemplo .env
```

**bash / WSL:**
```bash
cp .env.exemplo .env
```

Conteúdo padrão do `.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/asg_db
```

> `postgres` no host da URL é o nome do serviço Docker — funciona dentro da rede. Para rodar um serviço localmente fora do Docker, troque por `localhost`.

---

## 2. Criar a network

A network `rede_asg` é criada automaticamente pelo `docker-compose.yml`. Não é necessário criá-la manualmente.

Caso precise criar manualmente:

```powershell
docker network create rede_asg
```

Para verificar se ela existe:

**PowerShell:**
```powershell
docker network ls | findstr rede_asg
```

**bash / WSL:**
```bash
docker network ls | grep rede_asg
```

---

## 3. Subir todos os serviços

```powershell
docker compose up --build
```

Para subir em background:

```powershell
docker compose up --build -d
```

---

## 4. Subir um serviço específico

```powershell
docker compose up --build controller-ingestao
docker compose up --build controller-cruzamento-asg
docker compose up --build controller-busca-semantica
docker compose up --build controller-gerenciamento-banco
```

---

## 5. Derrubar os serviços

```powershell
docker compose down
```

Para derrubar e remover os volumes (apaga os dados do banco):

```powershell
docker compose down -v
```

---

## 6. Ver logs

Todos os serviços:

```powershell
docker compose logs -f
```

Serviço específico:

```powershell
docker compose logs -f controller-ingestao
docker compose logs -f controller-cruzamento-asg
docker compose logs -f controller-busca-semantica
docker compose logs -f controller-gerenciamento-banco
docker compose logs -f postgres
```

---

## 7. Reconstruir a imagem de um serviço

Use quando alterar o código ou o `requirements.txt`:

```powershell
docker compose build controller-ingestao
```

---

## 8. Acessar o banco de dados

```powershell
docker exec -it postgres-container psql -U postgres -d asg_db
```

---

## Serviços e portas

| Serviço                        | Container                        | Porta local |
|:-------------------------------|:---------------------------------|:-----------:|
| Ingestão de Dados              | `controller-ingestao`            | `8001`      |
| Cruzamento ASG                 | `controller-cruzamento-asg`      | `8002`      |
| Busca Semântica                | `controller-busca-semantica`     | `8003`      |
| Gerenciamento do Banco         | `controller-gerenciamento-banco` | `8004`      |
| PostgreSQL + PostGIS           | `postgres-container`             | `5432`      |

---

## Documentação automática (Swagger)

Cada serviço expõe documentação interativa via FastAPI:

| Serviço           | Swagger UI                  | ReDoc                        |
|:------------------|:----------------------------|:-----------------------------|
| Ingestão          | http://localhost:8001/docs  | http://localhost:8001/redoc  |
| Cruzamento ASG    | http://localhost:8002/docs  | http://localhost:8002/redoc  |
| Busca Semântica   | http://localhost:8003/docs  | http://localhost:8003/redoc  |
| Gerenc. Banco     | http://localhost:8004/docs  | http://localhost:8004/redoc  |
