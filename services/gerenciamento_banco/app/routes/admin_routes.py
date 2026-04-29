import os
import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.config.database import get_db
from app.services.admin_service import AdminService

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")

router = APIRouter(prefix="/admin", tags=["Admin"])
security = HTTPBearer()

# --- Middleware de Autenticação ---
def validar_sessao(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")

# --- Rotas ---

@router.post("/login")
async def login(payload: dict):
    # Em produção, consulte o banco de dados aqui
    if payload.get("username") == "admin" and payload.get("password") == "admin123":
        token = jwt.encode({
            "sub": "admin",
            "exp": datetime.utcnow() + timedelta(hours=2)
        }, SECRET_KEY, algorithm="HS256")
        return {"token": token}
    raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")

@router.get("/verificar-tudo")
async def verificar_tudo(db: Session = Depends(get_db), auth=Depends(validar_sessao)):
    service = AdminService()
    return await service.verificar_fontes(db)

@router.get("/verificar-atualizacao/{fonte}")
async def verificar_por_fonte(fonte: str, db: Session = Depends(get_db), auth=Depends(validar_sessao)):
    service = AdminService()
    resultado = await service.verificar_fontes(db, fonte_id=fonte)
    if not resultado:
        raise HTTPException(status_code=404, detail=f"Fonte '{fonte}' não encontrada")
    return resultado

@router.post("/atualizar/{fonte}")
async def atualizar(fonte: str, db: Session = Depends(get_db), auth=Depends(validar_sessao)):
    service = AdminService()
    checagem = await service.verificar_fontes(db, fonte_id=fonte)
    if checagem and not checagem.get("ha_novos_dados"):
        return {"message": "Não há novos dados para ingerir", "fonte": fonte}
    
    return await service.disparar_ingestao_remota(fonte)

@router.get("/status")
async def status_geral(auth=Depends(validar_sessao)):
    service = AdminService()
    return await service.obter_status_paralelo()