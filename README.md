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

## Busca de imóvel por CAR (SCRUM-3) — `gerenciamento_banco` (porta 8004)

| Método | Caminho | Descrição |
|--------|---------|-----------|
| GET | `/imovel?car={codigo}` | Consulta a tabela **`imovel`** (PostGIS). Resposta: `codigo_car`, `area_ha`, `municipio`, `situacao`, `dt_inscricao`, `dt_analise`. |

**Validação do CAR:** numérico com **11 a 20 dígitos**, ou formato federal `UF-0000000-{32 hex}` (ex.: `SP-3525300-44AA2FE43D774264B9F18E55658E70FA`).

**HTTP:** `400` formato inválido · `404` não encontrado · `500` erro no banco.

Na primeira subida do serviço, o SQLAlchemy cria a tabela `imovel` se não existir. Para testar com dados reais, é preciso **inserir registos** em `imovel` (ou script de migração/seed).

### Testes unitários (`gerenciamento_banco`)

Com Docker e Postgres a correr:

```powershell
cd backend
docker compose run --rm --entrypoint pytest controller-gerenciamento-banco tests/ -q --cov=app --cov-fail-under=80
```

Para testes locais sem tocar no Postgres, o código usa `SKIP_DB_INIT=1` (definido no `tests/conftest.py`).

---

## Endpoints CAR KML (MVP — memória)

No serviço **Ingestão** (`8001`), além de `/ingestao/propriedades` (PostgreSQL), existem rotas que replicam o protótipo da pasta `/app`:

| Método | Caminho | Descrição |
|--------|---------|-----------|
| GET | `/ingestao/car-kml/health` | Total de propriedades carregadas do KML |
| GET | `/ingestao/car-kml/propriedades` | Lista `cod_car`, `municipio`, `latitude`, `longitude` |
| GET | `/ingestao/car-kml/propriedades/{cod_car}` | Uma propriedade pelo código CAR |

O ficheiro **`services/ingestao/data/car_propriedades.kml`** é lido na **subida** do contentor. Se o KML for só *NetworkLink*, é necessária **internet** nessa fase. Estes dados **não** são persistidos na base.

---

## Documentação automática (Swagger)

Cada serviço expõe documentação interativa via FastAPI:

| Serviço           | Swagger UI                  | ReDoc                        |
|:------------------|:----------------------------|:-----------------------------|
| Ingestão          | http://localhost:8001/docs  | http://localhost:8001/redoc  |
| Cruzamento ASG    | http://localhost:8002/docs  | http://localhost:8002/redoc  |
| Busca Semântica   | http://localhost:8003/docs  | http://localhost:8003/redoc  |
| Gerenc. Banco     | http://localhost:8004/docs  | http://localhost:8004/redoc  |
