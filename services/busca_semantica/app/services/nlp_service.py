import re
import json
import logging
import pathlib
import unicodedata
import numpy as np
from difflib import get_close_matches as _gcm
from typing import Optional, Tuple, Dict, List

logger = logging.getLogger(__name__)

# ── Modelos Word2Vec + MLP (padrão do professor) ──────────────────────────────
_MODEL_DIR = pathlib.Path(__file__).parent.parent.parent / "models"
_w2v_model = None
_intent_clf = None
_tfidf = None

try:
    from gensim.models import Word2Vec as _Word2Vec
    import joblib as _joblib
    _w2v_model  = _Word2Vec.load(str(_MODEL_DIR / "word2vec.model"))
    _intent_clf = _joblib.load(_MODEL_DIR / "intent_clf.joblib")
    _tfidf      = _joblib.load(_MODEL_DIR / "tfidf.joblib")
    logger.info(f"Word2Vec + TF-IDF + MLPClassifier carregados — vocab: {len(_w2v_model.wv)} tokens, "
                f"classes: {list(_intent_clf.classes_)}")
except Exception as _e:
    logger.warning(f"Modelos Word2Vec/MLP não encontrados ({_e}) — usando BoW como fallback.")

def _w2v_representation(tokens: List[str]) -> Optional[np.ndarray]:
    """Mean + Max pooling ponderado por IDF — mesma função do treino."""
    if _w2v_model is None:
        return None
    vecs, weights = [], []
    for t in tokens:
        if t not in _w2v_model.wv:
            continue
        idf = (
            float(_tfidf.idf_[_tfidf.vocabulary_[t]])
            if _tfidf is not None and t in _tfidf.vocabulary_
            else 1.0
        )
        vecs.append(_w2v_model.wv[t] * idf)
        weights.append(idf)
    if not vecs:
        return None
    return np.sum(vecs, axis=0) / max(sum(weights), 1e-8)

# ── spaCy ─────────────────────────────────────────────────────────────────────
try:
    import spacy as _spacy
    _nlp = _spacy.load("pt_core_news_sm")
    _SPACY_OK = True
except Exception:
    _nlp = None
    _SPACY_OK = False
    logger.warning("spaCy pt_core_news_sm não disponível — usando fallback substring para municípios.")

_MUNICIPIOS_FILE = pathlib.Path(__file__).parent / ".." / ".." / "municipios-filtrados-644.json"

def _carregar_municipios() -> List[str]:
    try:
        data = json.loads(_MUNICIPIOS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return v
        if isinstance(data, list):
            return data
    except Exception as exc:
        logger.warning(f"Não foi possível carregar municípios SP: {exc}")
    return []

_MUNICIPIOS_SP: List[str] = _carregar_municipios()

# ── Regex de coordenadas geográficas ──────────────────────────────────────────
_COORD_RE = re.compile(
    r"(-?\d{1,3}[.,]\d+)\s*[,;/]\s*(-?\d{1,3}[.,]\d+)"
)

# ── Regex de código CAR ───────────────────────────────────────────────────────
CAR_REGEX = re.compile(r"([A-Z]{2}-[A-Za-z0-9]{7}-[A-Za-z0-9]+)", re.IGNORECASE)

# ── Stopwords PT-BR ──────────────────────────────────────────────────────────
STOPWORDS_PT = {
    "a", "o", "e", "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
    "por", "para", "com", "sem", "um", "uma", "uns", "umas", "que", "tem", "essa",
    "esse", "isso", "nesta", "neste", "nessa", "nesse", "sobre", "tem", "há", "ha",
    "qual", "quais", "como", "onde", "quando", "existe", "existem", "possui", "possuem",
    "houve", "teve", "teve", "foi", "foram", "esta", "este", "aqui", "ali", "la",
    "mais", "menos", "muito", "pouco", "algum", "nenhum", "todo", "toda", "todos",
}

# ── Mapa de intenções ─────────────────────────────────────────────────────────
INTENTS: Dict[str, Dict] = {

    "desmatamento": {
        "keywords": [
            "desmatamento", "desmatado", "desmatados", "desmatar", "desmate",
            "prodes", "deforestation",
            "floresta", "florestas", "florestal", "florestais",
            "vegetacao nativa", "vegetação nativa", "cobertura vegetal",
            "supressao vegetal", "supressão vegetal",
            "corte de arvore", "corte de árvore", "corte raso",
            "area desmatada", "área desmatada", "perda florestal",
            "degradacao florestal", "degradação florestal",
            "mata nativa", "mata ciliar", "mata atlantica", "mata atlântica",
            "reserva legal", "reserva legal insuficiente", "deficit reserva",
            "app insuficiente", "area de preservacao permanente",
            "bioma", "cerrado", "amazonia", "amazônia",
            "remoção de vegetação", "remocao de vegetacao",
        ],
        "service": "cruzamento_asg",
        "endpoint_template": "/cruzamento/car/{id}/passivos-ambientais",
        "default_params": {"fonte": "prodes"},
    },

    "queimada": {
        "keywords": [
            "queimada", "queimadas", "queimar", "queimou", "queimaram",
            "fogo", "fogos", "incendio", "incêndio", "incendios", "incêndios",
            "foco de calor", "focos de calor", "foco de queimada", "focos de queimada",
            "bdqueimadas", "bd queimadas", "queima de palhada",
            "fumaça", "fumaca", "fumacas", "fumaca de queimada",
            "area queimada", "área queimada", "cicatriz de queimada",
            "satellite", "satelite", "aqua", "terra", "modis",
            "risco de fogo", "risco de incendio", "risco de incêndio",
            "plano de queimada", "queima controlada",
        ],
        "service": "cruzamento_asg",
        "endpoint_template": "/cruzamento/car/{id}/passivos-ambientais",
        "default_params": {"fonte": "queimadas"},
    },

    "alerta": {
        "keywords": [
            "alerta", "alertas", "deter", "alerta deter",
            "monitoramento", "monitoramento florestal",
            "degradacao recente", "degradação recente",
            "desmatamento recente", "corte recente",
            "cicatriz recente", "anomalia florestal",
            "deteccao", "detecção", "varredura", "imageamento",
            "prodes deter", "alerta inpe", "inpe alerta",
        ],
        "service": "cruzamento_asg",
        "endpoint_template": "/cruzamento/car/{id}/passivos-ambientais",
        "default_params": {"fonte": "deter"},
    },

    "indigena": {
        "keywords": [
            "indigena", "indígena", "indigenas", "indígenas",
            "terra indigena", "terra indígena", "terras indigenas", "terras indígenas",
            "ti ", "funai", "aldeia", "aldeias", "povo indigena", "povo indígena",
            "comunidade indigena", "comunidade indígena",
            "territorio indigena", "território indígena",
            "sobreposicao indigena", "sobreposição indígena",
            "reserva indigena", "reserva indígena",
            "etnias", "etnia", "demarcacao", "demarcação",
            "demarcacao terra", "demarcação terra",
        ],
        "service": "cruzamento_asg",
        "endpoint_template": "/asg/relatorio/{id}",
        "default_params": {},
    },

    "conservacao": {
        "keywords": [
            "conservacao", "conservação", "unidade de conservacao", "unidade de conservação",
            "uc ", "ucs ", "parque", "parque nacional", "parque estadual",
            "parque municipal", "parque natural",
            "area de protecao ambiental", "área de proteção ambiental", "apa",
            "reserva biologica", "reserva biológica", "rebio",
            "reserva extrativista", "resex",
            "floresta nacional", "flona",
            "estacao ecologica", "estação ecológica", "esec",
            "monumento natural", "mona",
            "refugio de vida silvestre", "revis",
            "rppn", "reserva particular patrimonio natural",
            "icmbio", "ibama", "snuc",
            "sobreposicao uc", "sobreposição uc",
            "sobreposicao com uc", "sobreposição com uc",
            "area protegida", "área protegida", "areas protegidas", "áreas protegidas",
            "biodiversidade", "fauna", "flora",
        ],
        "service": "cruzamento_asg",
        "endpoint_template": "/asg/relatorio/{id}",
        "default_params": {},
    },

    "governanca": {
        "keywords": [
            "status car", "status do car", "situacao cadastral", "situação cadastral",
            "regularidade sicar", "regularidade car", "regularidade cadastral",
            "pendencia car", "pendência car", "pendencia sicar", "pendência sicar",
            "car ativo", "car pendente", "car suspenso", "car cancelado",
            "sicar", "sfb", "servico florestal", "serviço florestal",
            "cadastro ambiental rural", "car rural",
            "inscricao car", "inscrição car", "numero car", "número car",
            "validacao car", "validação car", "analise car", "análise car",
            "governanca", "governança", "compliance ambiental",
            "regularizacao ambiental", "regularização ambiental",
            "programa regularizacao ambiental", "pra",
            "termo de compromisso", "adequacao ambiental", "adequação ambiental",
            "passivo ambiental", "passivos ambientais",
        ],
        "service": "cruzamento_asg",
        "endpoint_template": "/asg/relatorio/{id}",
        "default_params": {},
    },

    "fundiario": {
        "keywords": [
            "fundiario", "fundiária", "fundiarios", "fundiárias",
            "escritura", "escritura rural", "escritura publica",
            "modulo fiscal", "módulo fiscal", "modulos fiscais",
            "georreferenciamento", "georeferenciamento", "georreferenciado",
            "itr", "imposto territorial rural",
            "ccir", "certificado cadastro imovel rural", "certificado de cadastro",
            "nirf", "numero imovel receita", "número imóvel receita",
            "titulacao", "titulação", "titulo de propriedade",
            "posse", "posse de terra", "posse rural",
            "usucapiao", "usucapião",
            "area total", "área total do imovel", "tamanho da propriedade",
            "hectares totais", "ha totais",
            "matricula", "matrícula", "matricula do imovel",
            "registro de imoveis", "cartorio", "cartório",
            "incra sigef", "sigef", "certificacao incra", "certificação incra",
            "limites da propriedade", "confrontantes",
        ],
        "service": "cruzamento_asg",
        "endpoint_template": "/asg/relatorio/{id}",
        "default_params": {},
    },

    "comunidades": {
        "keywords": [
            "assentamento", "assentamentos", "assentamento rural", "assentamento incra",
            "assentado", "assentados", "lote de reforma agraria", "lote de reforma agrária",
            "reforma agraria", "reforma agrária",
            "incra", "sipra", "ccra",
            "quilombola", "quilombolas", "territorio quilombola", "território quilombola",
            "comunidade quilombola", "comunidades quilombolas",
            "fundacao palmares", "fundação palmares",
            "beneficiario de reforma agraria", "beneficiário de reforma agrária",
            "trabalhador rural sem terra",
            "projeto de assentamento", "pa incra",
            "sobreposicao assentamento", "sobreposição assentamento",
            "sobreposicao quilombola", "sobreposição quilombola",
        ],
        "service": "cruzamento_asg",
        "endpoint_template": "/asg/relatorio/{id}",
        "default_params": {},
    },

    "relatorio": {
        "keywords": [
            "relatorio", "relatório", "relatorio asg", "relatório asg",
            "resumo", "resumo asg", "consolidado", "asg completo",
            "analise completa", "análise completa",
            "visao geral", "visão geral", "panorama geral",
            "indicadores asg", "indices asg", "índices asg",
            "score asg", "nota asg", "pontuacao asg", "pontuação asg",
            "risco asg", "nivel de risco", "nível de risco",
            "avaliacao asg", "avaliação asg",
            "ambiental social governanca", "ambiental social governança",
            "esg", "criterios esg",
        ],
        "service": "relatorio_asg",
        "endpoint_template": "/relatorio/car/{id}/asg",
        "default_params": {},
    },
}

# ── Fontes por intenção (US 10) ───────────────────────────────────────────────
INTENT_FONTES: Dict[str, str] = {
    "desmatamento": "PRODES/INPE (2016–2024)",
    "queimada":     "BDQueimadas/INPE (2016–2025)",
    "alerta":       "DETER/INPE",
    "indigena":     "FUNAI",
    "conservacao":  "ICMBio / MMA",
    "governanca":   "SICAR / SFB",
    "fundiario":    "SICAR / SFB / INCRA-SIGEF",
    "comunidades":  "INCRA / Fundação Palmares",
    "relatorio":    "SICAR + INPE + FUNAI + ICMBio + INCRA",
}

# ── Helpers de normalização ───────────────────────────────────────────────────

def _normalizar(texto: str) -> str:
    texto = texto.lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def _tokenizar(texto: str) -> List[str]:
    normalized = _normalizar(texto)
    tokens = re.findall(r"[a-z0-9]{2,}", normalized)
    return [t for t in tokens if t not in STOPWORDS_PT]


def _vocab_intent(keywords: List[str]) -> set:
    vocab: set = set()
    for kw in keywords:
        vocab.update(_tokenizar(kw))
    return vocab


# Cache lazy de todos os tokens de keywords (para fuzzy intent matching)
_ALL_KW_TOKENS_CACHE: Optional[set] = None

def _all_kw_tokens() -> set:
    global _ALL_KW_TOKENS_CACHE
    if _ALL_KW_TOKENS_CACHE is None:
        _ALL_KW_TOKENS_CACHE = set()
        for meta in INTENTS.values():
            _ALL_KW_TOKENS_CACHE.update(_vocab_intent(meta.get("keywords", [])))
    return _ALL_KW_TOKENS_CACHE


# Cache normalizado de municípios (para fuzzy municipality matching)
_NORM_MUN_MAP_CACHE: Optional[Dict[str, str]] = None

def _norm_mun_map() -> Dict[str, str]:
    global _NORM_MUN_MAP_CACHE
    if _NORM_MUN_MAP_CACHE is None:
        _NORM_MUN_MAP_CACHE = {_normalizar(m): m for m in _MUNICIPIOS_SP}
    return _NORM_MUN_MAP_CACHE


# ── Extração de intenção (BoW melhorado) ──────────────────────────────────────

def extrair_intencao(texto: str) -> Tuple[Optional[str], float, List[str], Optional[Tuple[str, str]]]:
    """Returns (intent, confidence, matches, correction) — correction is (typo, corrected) or None."""
    texto_tokens = _tokenizar(texto)
    if not texto_tokens:
        return None, 0.0, [], None

    freq: Dict[str, int] = {}
    for tk in texto_tokens:
        freq[tk] = freq.get(tk, 0) + 1

    # Fast-path: siglas e termos técnicos únicos → retorno imediato com alta confiança
    _SIGLAS: Dict[str, str] = {  # type: ignore[annotation-unchecked]
        "prodes": "desmatamento", "deforestation": "desmatamento",
        "deter": "alerta",
        "ti": "indigena", "tis": "indigena", "funai": "indigena",
        "uc": "conservacao", "ucs": "conservacao", "icmbio": "conservacao",
        "rppn": "conservacao", "rebio": "conservacao", "resex": "conservacao",
        "incra": "comunidades", "sipra": "comunidades", "quilombola": "comunidades",
        "sicar": "governanca", "sfb": "governanca", "ccir": "fundiario",
        "nirf": "fundiario", "itr": "fundiario", "sigef": "fundiario",
        # Relatório ASG
        "relatorio": "relatorio", "report": "relatorio", "reports": "relatorio",
        "reportasg": "relatorio", "asg": "relatorio", "esg": "relatorio",
        "risco": "relatorio",
    }
    tokens_set = set(texto_tokens)
    for sigla, intent_sigla in _SIGLAS.items():
        if sigla in tokens_set:
            return intent_sigla, 0.9, [sigla], None

    # ── Word2Vec + MLP (padrão bot_model.py do professor) ────────────────────
    # Tenta corrigir tokens OOV antes de vetorizar (potencializa o W2V)
    if _w2v_model is not None and _intent_clf is not None:
        all_kw = _all_kw_tokens()
        corrected_tokens = list(texto_tokens)
        w2v_corr: Optional[Tuple[str, str]] = None
        for i, tk in enumerate(corrected_tokens):
            if tk not in _w2v_model.wv and len(tk) >= 5:
                m = _gcm(tk, all_kw, n=1, cutoff=0.82)
                if m and m[0] != tk:
                    if w2v_corr is None:
                        w2v_corr = (tk, m[0])
                    corrected_tokens[i] = m[0]

        vec = _w2v_representation(corrected_tokens)
        if vec is not None:
            proba = _intent_clf.predict_proba([vec])[0]
            best_idx = int(np.argmax(proba))
            conf    = float(proba[best_idx])
            # Threshold mínimo — abaixo de 0.35 cai para BoW (mais seguro)
            if conf >= 0.35:
                intent = _intent_clf.classes_[best_idx]
                return intent, round(conf, 2), corrected_tokens, w2v_corr

    # ── Fallback BoW (quando modelos não estão carregados) ────────────────────
    # Busca por frases completas (bigrams/trigrams) para keywords compostas
    texto_norm = _normalizar(texto)

    best_intent = None
    best_score = 0.0
    best_matches: List[str] = []

    for intent_key, meta in INTENTS.items():
        keywords = meta.get("keywords", [])
        if not keywords:
            continue

        matched_tokens: List[str] = []
        phrase_bonus = 0.0

        # Verifica frases exatas primeiro (maior peso)
        for kw in keywords:
            kw_norm = _normalizar(kw)
            if len(kw.split()) > 1 and kw_norm in texto_norm:
                phrase_bonus += 0.15
                matched_tokens.extend(_tokenizar(kw))

        # Depois tokens individuais
        vocab = _vocab_intent(keywords)
        token_matches = sorted([t for t in vocab if t in freq])
        matched_tokens = list(set(matched_tokens + token_matches))

        if not matched_tokens:
            continue

        overlap = len(set(matched_tokens)) / max(len(vocab), 1)
        repetition = sum(freq.get(t, 0) for t in matched_tokens) / max(len(texto_tokens), 1)
        score = min(1.0, (0.75 * overlap) + (0.15 * repetition) + phrase_bonus)

        if score > best_score:
            best_score = score
            best_intent = intent_key
            best_matches = matched_tokens

    # ── Fuzzy pass: nenhum intent encontrado → tenta correção ortográfica ────
    correction: Optional[Tuple[str, str]] = None
    if best_score == 0.0 and texto_tokens:
        all_kw = _all_kw_tokens()
        corrected = list(texto_tokens)
        first_corr: Optional[Tuple[str, str]] = None
        for i, tk in enumerate(corrected):
            if len(tk) < 5:
                continue
            m = _gcm(tk, all_kw, n=1, cutoff=0.82)
            if m and m[0] != tk:
                if first_corr is None:
                    first_corr = (tk, m[0])
                corrected[i] = m[0]

        if first_corr:
            freq2: Dict[str, int] = {}
            for tk in corrected:
                freq2[tk] = freq2.get(tk, 0) + 1
            for intent_key, meta in INTENTS.items():
                vocab = _vocab_intent(meta.get("keywords", []))
                matched = [t for t in vocab if t in freq2]
                if not matched:
                    continue
                overlap = len(set(matched)) / max(len(vocab), 1)
                rep = sum(freq2.get(t, 0) for t in matched) / max(len(corrected), 1)
                score = min(1.0, 0.75 * overlap + 0.15 * rep) * 0.9  # penalidade leve por fuzzy
                if score > best_score:
                    best_score = score
                    best_intent = intent_key
                    best_matches = matched
                    correction = first_corr

    return best_intent, round(best_score, 2), best_matches, correction

# ── Extração de CAR ───────────────────────────────────────────────────────────

def extrair_cod_imovel(texto: str) -> Optional[str]:
    if not texto:
        return None
    m = CAR_REGEX.search(texto)
    return m.group(1).upper() if m else None

# ── Extração de município (spaCy + fallback substring) ────────────────────────

def extrair_municipio(texto: str) -> Tuple[Optional[str], Optional[Tuple[str, str]]]:
    """Returns (municipio, correction) — correction is (typo, corrected) or None."""
    if not texto or not _MUNICIPIOS_SP:
        return None, None

    texto_norm = _normalizar(texto)

    # 1. spaCy NER — entidades LOC/GPE
    if _SPACY_OK and _nlp is not None:
        try:
            doc = _nlp(texto)
            for ent in doc.ents:
                if ent.label_ in ("LOC", "GPE"):
                    ent_norm = _normalizar(ent.text)
                    for municipio in _MUNICIPIOS_SP:
                        if _normalizar(municipio) == ent_norm:
                            return municipio, None
                    for municipio in _MUNICIPIOS_SP:
                        mun_norm = _normalizar(municipio)
                        if ent_norm in mun_norm or mun_norm in ent_norm:
                            return municipio, None
        except Exception as exc:
            logger.warning(f"spaCy NER falhou: {exc}")

    # 2. Substring exata na lista completa
    for municipio in sorted(_MUNICIPIOS_SP, key=len, reverse=True):
        if _normalizar(municipio) in texto_norm:
            return municipio, None

    # 3. Fuzzy fallback — permite 1-2 caracteres errados no nome do município
    words = re.findall(r"[a-z]{3,}", texto_norm)
    nm_map = _norm_mun_map()
    norm_list = list(nm_map.keys())
    for n in (3, 2, 1):
        for i in range(len(words) - n + 1):
            candidate = " ".join(words[i : i + n])
            if len(candidate) < 4:
                continue
            matches = _gcm(candidate, norm_list, n=1, cutoff=0.82)
            if matches:
                mun = nm_map[matches[0]]
                typo = candidate if candidate != matches[0] else None
                return mun, (typo, mun) if typo else None

    return None, None

# ── Extração de coordenadas ───────────────────────────────────────────────────

def extrair_coordenadas(texto: str) -> Optional[Tuple[float, float]]:
    """Extrai par lat/lon do texto. Valida range do Brasil."""
    if not texto:
        return None
    m = _COORD_RE.search(texto)
    if not m:
        return None
    try:
        v1 = float(m.group(1).replace(",", "."))
        v2 = float(m.group(2).replace(",", "."))

        def _brasil(lat: float, lon: float) -> bool:
            return -35.0 <= lat <= 5.0 and -74.0 <= lon <= -28.0

        if _brasil(v1, v2):
            return v1, v2
        # Ordem invertida (lon, lat)
        if _brasil(v2, v1):
            return v2, v1
        # Latitude positiva — usuário esqueceu o sinal negativo (comum no Brasil)
        if v1 > 0 and _brasil(-v1, v2):
            return -v1, v2
        if v2 > 0 and _brasil(v1, -v2):
            return v1, -v2
        # Ambos positivos
        if v1 > 0 and v2 > 0 and _brasil(-v1, -v2):
            return -v1, -v2
    except (ValueError, TypeError):
        pass
    return None

# ── Documentação de intenções ─────────────────────────────────────────────────

def obter_intencoes_documentacao() -> Dict[str, Dict]:
    return {
        k: {
            "palavras_chave": v.get("keywords", [])[:10],
            "servico": v.get("service"),
            "endpoint_exemplo": v.get("endpoint_template"),
            "fonte_dados": INTENT_FONTES.get(k, "N/D"),
        }
        for k, v in INTENTS.items()
    }
