import httpx
import asyncio
import xml.etree.ElementTree as ET
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.inpe_models import DesmatamentoProdes, AlertaDeter, FocoQueimada
from app.models.propriedade import Propriedade
from app.models.areas_protegidas_models import UnidadeConservacao, TerraIndigena, Assentamento, Quilombola 

class AdminService:
    def __init__(self):
        self.endpoints_externos = {
            "SICAR": {
                "url": "https://geoservicos.sede.embrapa.br/geoserver/SICAR/wfs?service=wfs&version=2.0.0&request=GetFeature&typeNames=SICAR:imoveis_sp&resultType=hits", 
                "tipo": "WFS"
            },
            "PRODES": {
                "url": "http://terrabrasilis.dpi.inpe.br/geoserver/wfs?service=wfs&version=2.0.0&request=GetFeature&typeNames=prodes-cerrado:yearly_deforestation&resultType=hits&CQL_FILTER=uf='SP'", 
                "tipo": "WFS"
            },
            "DETER": {
                "url": "http://terrabrasilis.dpi.inpe.br/geoserver/wfs?service=wfs&version=2.0.0&request=GetFeature&typeNames=deter-cerrado:alerts&resultType=hits&CQL_FILTER=uf='SP'", 
                "tipo": "WFS"
            },
            "Unidades de Conservação": {
                "url": "https://www.icmbio.gov.br/geoserver/SMCUC/ows?service=wfs&version=2.0.0&request=GetFeature&typeNames=SMCUC:ucstodas&resultType=hits&CQL_FILTER=siglaUF%20like%20'%25SP%25'", 
                "tipo": "WFS"
            },
            "Terras Indígenas": {
                "url": "https://geoserver.funai.gov.br/geoserver/Funai/ows?service=wfs&version=2.0.0&request=GetFeature&typeNames=Funai:tis_poligonais&resultType=hits&CQL_FILTER=uf_sigla%20like%20'%25SP%25'", 
                "tipo": "WFS"
            },
            "Queimadas": {
                "url": "https://queimadas.dgi.inpe.br/api/focos/?estado_id=35&data_min=2016-01-01T00:00:00Z", 
                "tipo": "REST"
            },
            "Assentamentos": {
                "url": "https://acervofundiario.incra.gov.br/i3geo/ogc.php?service=wfs&version=1.0.0&request=GetFeature&typeName=assentamentos", 
                "tipo": "WFS_LENTO"
            },
            "Quilombolas": {
                "url": "https://acervofundiario.incra.gov.br/i3geo/ogc.php?service=wfs&version=1.0.0&request=GetFeature&typeName=quilombolas", 
                "tipo": "WFS_LENTO"
            }
        }
        
        self.url_ingestao = "http://controller-ingestao:8000"

    async def consultar_contagem_remota(self, config: dict):
        if not config: return 0
        
        url = config["url"]
        tipo = config["tipo"]
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=30.0)
                if resp.status_code != 200:
                    return 0
                if tipo == "WFS":
                    root = ET.fromstring(resp.text)
                    return int(root.attrib.get('numberMatched', 0))
                elif tipo == "REST":
                    dados = resp.json()
                    return len(dados) if isinstance(dados, list) else 0
                elif tipo == "WFS_LENTO":
                    return resp.text.count("gml:featureMember")
                    
        except Exception:
            return 0
        return 0

    def get_fontes_config(self):
        return [
            {"id": "sicar", "nome": "SICAR", "model": Propriedade},
            {"id": "prodes", "nome": "PRODES", "model": DesmatamentoProdes},
            {"id": "deter", "nome": "DETER", "model": AlertaDeter},
            {"id": "queimadas", "nome": "Queimadas", "model": FocoQueimada},
            {"id": "ucs", "nome": "Unidades de Conservação", "model": UnidadeConservacao},
            {"id": "tis", "nome": "Terras Indígenas", "model": TerraIndigena},
            {"id": "assentamentos", "nome": "Assentamentos", "model": Assentamento},
            {"id": "quilombolas", "nome": "Quilombolas", "model": Quilombola}
        ]

    async def verificar_fontes(self, db: Session, fonte_id: str = None):
        fontes = self.get_fontes_config()
        if fonte_id:
            fontes = [f for f in fontes if f["id"] == fonte_id.lower()]
            if not fontes: return None

        resultados = []
        for f in fontes:
            total_local = db.query(func.count(f["model"].id)).scalar() or 0
            config_remoto = self.endpoints_externos.get(f["nome"])
            total_remoto = await self.consultar_contagem_remota(config_remoto) if config_remoto else total_local
            if total_remoto < total_local:
                total_remoto = total_local
            
            resultados.append({
                "id": f["id"],
                "fonte": f["nome"],
                "total_local": total_local,
                "total_remoto": total_remoto,
                "ha_novos_dados": total_remoto > total_local
            })
        
        return resultados[0] if fonte_id else resultados

    async def disparar_ingestao_remota(self, fonte: str, estado: str = "SP"):
        rotas_post = {
            "sicar": f"{self.url_ingestao}/ingestao/sicar/ingerir?estado={estado}",
            "prodes": f"{self.url_ingestao}/ingestao/inpe/prodes/ingerir?estado={estado}",
            "deter": f"{self.url_ingestao}/ingestao/inpe/deter/ingerir?estado={estado}",
            "queimadas": f"{self.url_ingestao}/ingestao/inpe/queimadas/ingerir?estado={estado}&ano_inicio=2016&ano_fim=2026",
            "ucs": f"{self.url_ingestao}/ingestao/areas-protegidas/uc/ingerir?uf={estado}",
            "tis": f"{self.url_ingestao}/ingestao/areas-protegidas/ti/ingerir?uf={estado}",
            "assentamentos": f"{self.url_ingestao}/ingestao/areas-protegidas/assentamento/ingerir?uf={estado}",
            "quilombolas": f"{self.url_ingestao}/ingestao/areas-protegidas/quilombola/ingerir?uf={estado}"
        }
        
        url = rotas_post.get(fonte.lower())
        if not url: return {"error": f"Fonte {fonte} não mapeada"}

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, timeout=30.0)
                if resp.status_code == 404:
                    return {"error": f"Rota não encontrada: {url}"}
                return resp.json()
            except Exception as e:
                return {"error": f"Falha na comunicação inter-containers: {str(e)}"}

    async def obter_status_paralelo(self):
        rotas_status = {
            "sicar": f"{self.url_ingestao}/ingestao/sicar/status",
            "prodes": f"{self.url_ingestao}/ingestao/inpe/prodes/status",
            "deter": f"{self.url_ingestao}/ingestao/inpe/deter/status",
            "queimadas": f"{self.url_ingestao}/ingestao/inpe/queimadas/status",
            "ucs": f"{self.url_ingestao}/ingestao/areas-protegidas/uc/status",
            "tis": f"{self.url_ingestao}/ingestao/areas-protegidas/ti/status",
            "assentamentos": f"{self.url_ingestao}/ingestao/areas-protegidas/assentamento/status",
            "quilombolas": f"{self.url_ingestao}/ingestao/areas-protegidas/quilombola/status"
        }

        async with httpx.AsyncClient() as client:
            fontes = [f["id"] for f in self.get_fontes_config()]
            tarefas = [client.get(rotas_status[f], timeout=5.0) for f in fontes if f in rotas_status]
            respostas = await asyncio.gather(*tarefas, return_exceptions=True)
            
            status_final = {}
            for i, f in enumerate(fontes):
                resp = respostas[i]
                
                if isinstance(resp, Exception) or resp.status_code != 200:
                    status_final[f] = {"status": "erro", "progresso": 0}
                    continue
                
                data = resp.json()
                
                fonte_data = data.get(f) if f in data else data
                is_running = fonte_data.get("rodando", False)
                has_error = fonte_data.get("erro") is not None
                
                if has_error:
                    status_final[f] = {"status": "erro", "progresso": 0}
                elif is_running:
                    status_final[f] = {"status": "updating", "progresso": 50} 
                else:
                    status_final[f] = {"status": "concluido", "progresso": 100}
            
            return status_final