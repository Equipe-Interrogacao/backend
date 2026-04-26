import re
import unicodedata
from typing import Optional, Tuple, Dict, List

INTENTS = {
    "desmatamento": {
        "keywords": ["desmatamento", "prodes", "floresta"],
        "service": "cruzamento_asg",
        "endpoint_template": "/asg/analises/{id}",
        "default_params": {},
    },
    "queimada": {
        "keywords": ["queimada", "fogo", "incêndio", "incendio"],
        "service": "cruzamento_asg",
        "endpoint_template": "/asg/analises/{id}",
        "default_params": {},
    },
    "alerta": {
        "keywords": ["alerta", "deter"],
        "service": "cruzamento_asg",
        "endpoint_template": "/asg/analises/{id}",
        "default_params": {},
    },
    "indigena": {
        "keywords": ["indígena", "indigena", "ti", "terra indígena", "terra indigena"],
        "service": "cruzamento_asg",
        "endpoint_template": "/asg/analises/{id}",
        "default_params": {},
    },
    "conservacao": {
        "keywords": ["conservação", "conservacao", "uc", "parque", "unidade de conservação"],
        "service": "cruzamento_asg",
        "endpoint_template": "/asg/analises/{id}",
        "default_params": {},
    },
    "relatorio": {
        "keywords": ["relatório", "relatorio", "asg", "resumo"],
        "service": "relatorio_asg",
        "endpoint_template": "/relatorio/car/{id}/asg",
        "default_params": {},
    },
}

MUNICIPIOS_SP = [
    "São Paulo", "Sao Paulo", "Campinas", "Santos", "Sao José dos Campos", "Ribeirão Preto", "Ribeirao Preto"
]

CAR_REGEX = re.compile(r"([A-Z]{2}-[A-Za-z0-9-]+)", re.IGNORECASE)

STOPWORDS_PT = {
    "a", "o", "e", "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
    "por", "para", "com", "sem", "um", "uma", "uns", "umas", "que", "tem", "essa",
    "esse", "isso", "nesta", "neste", "nessa", "nesse", "sobre", "tem", "há", "ha"
}


def _normalizar_texto(texto: str) -> str:
    texto = texto.lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def _tokenizar(texto: str) -> List[str]:
    normalized = _normalizar_texto(texto)
    tokens = re.findall(r"[a-z0-9]{2,}", normalized)
    return [t for t in tokens if t not in STOPWORDS_PT]


def _vocabulario_intencao(keywords: List[str]) -> set[str]:
    vocab: set[str] = set()
    for kw in keywords:
        vocab.update(_tokenizar(kw))
    return vocab


def extrair_intencao(texto: str) -> Tuple[Optional[str], float, List[str]]:
    texto_tokens = _tokenizar(texto)
    if not texto_tokens:
        return None, 0.0, []

    texto_freq: Dict[str, int] = {}
    for tk in texto_tokens:
        texto_freq[tk] = texto_freq.get(tk, 0) + 1

    best_intent = None
    best_score = 0.0
    best_matches: List[str] = []

    for intent_key, meta in INTENTS.items():
        keywords = meta.get("keywords", [])
        if not keywords:
            continue

        intent_vocab = _vocabulario_intencao(keywords)
        if not intent_vocab:
            continue

        matched_tokens = sorted([t for t in intent_vocab if t in texto_freq])
        if not matched_tokens:
            continue

        # Simple BoW confidence: overlap over intent vocabulary size.
        # Repetition in user text slightly boosts confidence.
        overlap = len(matched_tokens) / len(intent_vocab)
        repetition_boost = sum(texto_freq[t] for t in matched_tokens) / max(len(texto_tokens), 1)
        score = min(1.0, (0.8 * overlap) + (0.2 * repetition_boost))

        if score > best_score:
            best_score = score
            best_intent = intent_key
            best_matches = matched_tokens

    return best_intent, round(best_score, 2), best_matches


def extrair_cod_imovel(texto: str) -> Optional[str]:
    if not texto:
        return None
    m = CAR_REGEX.search(texto)
    if m:
        return m.group(1).upper()
    return None


def extrair_municipio(texto: str) -> Optional[str]:
    if not texto:
        return None
    normalized_text = _normalizar_texto(texto)
    for m in MUNICIPIOS_SP:
        if _normalizar_texto(m) in normalized_text:
            return m
    return None


def obter_intencoes_documentacao() -> Dict[str, Dict]:
    docs = {}
    for k, v in INTENTS.items():
        docs[k] = {
            "palavras_chave": v.get("keywords", []),
            "servico": v.get("service"),
            "endpoint_exemplo": v.get("endpoint_template"),
        }
    return docs
