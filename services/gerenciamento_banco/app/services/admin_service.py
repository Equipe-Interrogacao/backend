import httpx
import asyncio
import xml.etree.ElementTree as ET
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.inpe_models import DesmatamentoProdes, AlertaDeter, FocoQueimada
from app.models.propriedade import Propriedade

class AdminService:
    def __init__(self):
        self.endpoints_externos = {
            "PRODES": "http://terrabrasilis.dpi.inpe.br/geoserver/wfs?service=wfs&version=2.0.0&request=GetFeature&typeNames=prodes-legal-amazon:yearly_deforestation&resultType=hits",
            "DETER": "http://terrabrasilis.dpi.inpe.br/geoserver/wfs?service=wfs&version=2.0.0&request=GetFeature&typeNames=deter-amz:alerts&resultType=hits",
            "SICAR": "https://geoservicos.sede.embrapa.br/geoserver/SICAR/wfs?service=wfs&version=2.0.0&request=GetFeature&typeNames=SICAR:imoveis_sp&resultType=hits"
        }
        self.url_ingestao = "http://localhost:8001"

    async def consultar_hits_wfs(self, url: str):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=10.0)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    return int(root.attrib.get('numberMatched', 0))
        except Exception:
            return 0
        return 0

    def get_fontes_config(self):
        return [
            {"id": "prodes", "nome": "PRODES", "model": DesmatamentoProdes},
            {"id": "deter", "nome": "DETER", "model": AlertaDeter},
            {"id": "queimadas", "nome": "Queimadas", "model": FocoQueimada},
            {"id": "sicar", "nome": "SICAR", "model": Propriedade}
        ]

    async def verificar_fontes(self, db: Session, fonte_id: str = None):
        fontes = self.get_fontes_config()
        
        # Se uma fonte específica for passada, filtra a lista
        if fonte_id:
            fontes = [f for f in fontes if f["id"] == fonte_id.lower()]
            if not fontes: return None

        resultados = []
        for f in fontes:
            total_local = db.query(func.count(f["model"].id)).scalar() or 0
            url_externa = self.endpoints_externos.get(f["nome"])
            total_remoto = await self.consultar_hits_wfs(url_externa) if url_externa else total_local
            
            resultados.append({
                "id": f["id"],
                "fonte": f["nome"],
                "total_local": total_local,
                "total_remoto": total_remoto,
                "ha_novos_dados": total_remoto > total_local
            })
        
        return resultados[0] if fonte_id else resultados

    async def disparar_ingestao_remota(self, fonte: str, estado: str = "SP"):
        rotas = {
            "prodes": f"{self.url_ingestao}/ingestao/inpe/prodes/ingerir?estado={estado}",
            "deter": f"{self.url_ingestao}/ingestao/inpe/deter/ingerir?estado={estado}",
            "queimadas": f"{self.url_ingestao}/ingestao/inpe/queimadas/ingerir?estado={estado}&ano=2024",
            "sicar": f"{self.url_ingestao}/ingestao/sicar/ingerir?estado={estado}"
        }
        
        url = rotas.get(fonte.lower())
        if not url: return {"error": "Rota de ingestão não encontrada"}

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, timeout=None)
                return resp.json()
            except Exception as e:
                return {"error": f"Falha ao conectar no serviço de ingestão: {str(e)}"}

    async def obter_status_paralelo(self):
        """Consulta o status de todos os serviços de uma vez."""
        async with httpx.AsyncClient() as client:
            fontes = ["prodes", "deter", "queimadas", "sicar"]
            tarefas = [client.get(f"{self.url_ingestao}/status/{f}") for f in fontes]
            
            respostas = await asyncio.gather(*tarefas, return_exceptions=True)
            
            status_final = {}
            for i, resp in enumerate(respostas):
                if isinstance(resp, Exception):
                    status_final[fontes[i]] = "Indisponível"
                else:
                    status_final[fontes[i]] = resp.json() if resp.status_code == 200 else "Erro"
            
            return status_final