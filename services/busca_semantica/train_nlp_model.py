"""
Treina Word2Vec + MLPClassifier para classificação de intenções ASG.
Padrão: chatbot_model_training.ipynb do professor.
Executado durante o docker build — salva modelos em /app/models/.
"""

import sys
import pathlib
import unicodedata
import re
import numpy as np
from gensim.models import Word2Vec
from sklearn.neural_network import MLPClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import cross_val_score
import joblib

# Importa as keywords do nlp_service para usar como dados extras de treino
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from app.services.nlp_service import INTENTS

# ── Diretório de saída ────────────────────────────────────────────────────────
MODEL_DIR = pathlib.Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

# ── Pré-processamento (igual ao nlp_service) ──────────────────────────────────
STOPWORDS = {
    "a", "o", "e", "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
    "por", "para", "com", "sem", "um", "uma", "uns", "umas", "que", "tem", "essa",
    "esse", "isso", "nesta", "neste", "nessa", "nesse", "sobre", "ha", "qual",
    "quais", "como", "onde", "quando", "existe", "existem", "possui", "houve",
    "foi", "foram", "esta", "este", "aqui", "ali", "la", "mais", "menos",
    "algum", "nenhum", "todo", "toda", "todos",
}

def normalizar(texto: str) -> str:
    texto = texto.lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )

def tokenizar(texto: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]{2,}", normalizar(texto))
    return [t for t in tokens if t not in STOPWORDS]

# ── Dataset de treino ─────────────────────────────────────────────────────────
DADOS = [
    # ── desmatamento ──────────────────────────────────────────────────────────
    ("desmatamento", "Tem desmatamento registrado nessa propriedade?"),
    ("desmatamento", "Qual a área desmatada no CAR?"),
    ("desmatamento", "Houve supressão vegetal recente aqui?"),
    ("desmatamento", "Essa fazenda tem déficit de reserva legal?"),
    ("desmatamento", "Mostre perda florestal do PRODES"),
    ("desmatamento", "mostra o desmatamento da propriedade"),
    ("desmatamento", "tem PRODES nessa fazenda"),
    ("desmatamento", "area desmatada em hectares"),
    ("desmatamento", "supressao de mata nativa detectada"),
    ("desmatamento", "corte raso flagrado pelo satellite"),
    ("desmatamento", "deficit de APP aqui"),
    ("desmatamento", "vegetacao nativa removida na propriedade"),
    ("desmatamento", "bioma degradado nessa area"),
    ("desmatamento", "reserva legal irregular"),
    ("desmatamento", "perda de cobertura florestal"),
    ("desmatamento", "floresta desmatada nessa regiao"),
    ("desmatamento", "mata ciliar suprimida"),
    ("desmatamento", "desflorestamento registrado pelo INPE"),
    ("desmatamento", "corte de arvore detectado"),
    ("desmatamento", "area de preservacao permanente comprometida"),

    # ── queimada ──────────────────────────────────────────────────────────────
    ("queimada", "Teve fogo nessa area?"),
    ("queimada", "Quais focos de calor foram detectados?"),
    ("queimada", "Tem registro de queimadas no BDQueimadas?"),
    ("queimada", "Houve incendio nessa propriedade nos ultimos anos?"),
    ("queimada", "Mostra cicatriz de queimada no imovel"),
    ("queimada", "queimada nessa area rural"),
    ("queimada", "foco de calor detectado pelo satellite"),
    ("queimada", "historico de incendios na fazenda"),
    ("queimada", "queima de palhada registrada"),
    ("queimada", "area queimada identificada no satellite"),
    ("queimada", "risco de fogo na propriedade"),
    ("queimada", "fumaca detectada nos arredores"),
    ("queimada", "cicatriz de fogo identificada"),
    ("queimada", "queimou nessa fazenda recentemente"),
    ("queimada", "incendio florestal registrado"),
    ("queimada", "focos de incendio proximos"),
    ("queimada", "BDQueimadas INPE registro"),
    ("queimada", "fogo na vegetacao"),
    ("queimada", "queimada ativa detectada"),
    ("queimada", "historico de fogo nessa regiao"),

    # ── alerta ────────────────────────────────────────────────────────────────
    ("alerta", "Tem alerta DETER ativo aqui?"),
    ("alerta", "Houve algum alerta de desmatamento recente?"),
    ("alerta", "Mostre os alertas de monitoramento florestal"),
    ("alerta", "degradacao recente detectada"),
    ("alerta", "alerta de supressao vegetal"),
    ("alerta", "deteccao DETER nessa propriedade"),
    ("alerta", "monitoramento florestal com alerta"),
    ("alerta", "anomalia florestal detectada pelo INPE"),
    ("alerta", "varredura DETER encontrou algo"),
    ("alerta", "desmatamento recente no DETER"),
    ("alerta", "corte recente flagrado pelo sistema"),
    ("alerta", "imageamento INPE com alerta"),
    ("alerta", "alerta INPE ativo"),
    ("alerta", "degradacao florestal recente"),
    ("alerta", "sistema de alerta DETER"),
    ("alerta", "monitoramento ativo com alertas"),
    ("alerta", "sinalizacao de desmatamento"),
    ("alerta", "alerta de degradacao ativa"),
    ("alerta", "DETER identificou problema"),
    ("alerta", "deteccao recente de supressao"),

    # ── indigena ──────────────────────────────────────────────────────────────
    ("indigena", "Essa fazenda sobrepoe terra indigena?"),
    ("indigena", "Tem area da FUNAI nos arredores?"),
    ("indigena", "terra indigena sobreposta a propriedade"),
    ("indigena", "aldeia indigena proxima"),
    ("indigena", "FUNAI demarcacao nessa regiao"),
    ("indigena", "territorio indigena aqui"),
    ("indigena", "sobreposicao com TI"),
    ("indigena", "povo indigena nos arredores"),
    ("indigena", "reserva indigena proxima"),
    ("indigena", "demarcacao FUNAI nessa area"),
    ("indigena", "etnia indigena na regiao"),
    ("indigena", "TI identificada proxima"),
    ("indigena", "comunidade indigena sobreposta"),
    ("indigena", "area com demarcacao indigena"),
    ("indigena", "sobreposicao indigena risco"),
    ("indigena", "terras indigenas FUNAI"),
    ("indigena", "territorio tradicional indigena"),
    ("indigena", "aldeia nos limites da propriedade"),
    ("indigena", "povo originario na regiao"),
    ("indigena", "conflito indigena fundiario"),

    # ── conservacao ───────────────────────────────────────────────────────────
    ("conservacao", "Existe sobreposicao com unidade de conservacao?"),
    ("conservacao", "Essa propriedade esta dentro de algum parque?"),
    ("conservacao", "unidade de conservacao sobreposta"),
    ("conservacao", "parque estadual nos arredores"),
    ("conservacao", "APA nessa area"),
    ("conservacao", "ICMBio parque nacional"),
    ("conservacao", "reserva biologica proxima"),
    ("conservacao", "area protegida por lei"),
    ("conservacao", "RPPN proxima"),
    ("conservacao", "floresta nacional aqui"),
    ("conservacao", "UC detectada na propriedade"),
    ("conservacao", "estacao ecologica sobreposta"),
    ("conservacao", "area de protecao ambiental"),
    ("conservacao", "sobreposicao com UC"),
    ("conservacao", "biodiversidade protegida"),
    ("conservacao", "parque natural nos limites"),
    ("conservacao", "reserva extrativista proxima"),
    ("conservacao", "monumento natural aqui"),
    ("conservacao", "SNUC sobreposicao"),
    ("conservacao", "area de conservacao ambiental"),

    # ── governanca ────────────────────────────────────────────────────────────
    ("governanca", "Qual o status do CAR no SICAR?"),
    ("governanca", "Esse CAR esta ativo ou pendente?"),
    ("governanca", "situacao do cadastro ambiental rural"),
    ("governanca", "regularidade do CAR"),
    ("governanca", "inscricao CAR ativa"),
    ("governanca", "pendencia no SICAR"),
    ("governanca", "CAR cancelado ou suspenso"),
    ("governanca", "compliance ambiental da propriedade"),
    ("governanca", "regularizacao ambiental do imovel"),
    ("governanca", "validacao do cadastro ambiental"),
    ("governanca", "CAR com pendencia"),
    ("governanca", "situacao cadastral SICAR"),
    ("governanca", "SFB cadastro florestal"),
    ("governanca", "programa de regularizacao ambiental"),
    ("governanca", "termo de compromisso ambiental"),
    ("governanca", "analise do CAR"),
    ("governanca", "numero do cadastro ambiental rural"),
    ("governanca", "SICAR verificar situacao"),
    ("governanca", "status da inscricao ambiental"),
    ("governanca", "conformidade CAR fazenda"),

    # ── fundiario ─────────────────────────────────────────────────────────────
    ("fundiario", "Qual o tamanho total do imovel em hectares?"),
    ("fundiario", "Tem certificacao no INCRA SIGEF?"),
    ("fundiario", "modulo fiscal da propriedade"),
    ("fundiario", "tamanho em hectares da fazenda"),
    ("fundiario", "georreferenciamento SIGEF"),
    ("fundiario", "certificacao INCRA do imovel"),
    ("fundiario", "ITR da fazenda"),
    ("fundiario", "CCIR do imovel rural"),
    ("fundiario", "area total declarada"),
    ("fundiario", "tipo de imovel rural"),
    ("fundiario", "escritura rural do imovel"),
    ("fundiario", "NIRF cadastrado"),
    ("fundiario", "imposto territorial rural"),
    ("fundiario", "certificado de cadastro de imovel rural"),
    ("fundiario", "hectares declarados no CAR"),
    ("fundiario", "dimensao da propriedade"),
    ("fundiario", "area georreferenciada SIGEF"),
    ("fundiario", "modulos fiscais do imovel"),
    ("fundiario", "dados fundiarios da propriedade"),
    ("fundiario", "regularidade fundiaria"),

    # ── comunidades ───────────────────────────────────────────────────────────
    ("comunidades", "Essa area sobrepoe assentamento do INCRA?"),
    ("comunidades", "Tem territorio quilombola proximo?"),
    ("comunidades", "assentamento INCRA proximo"),
    ("comunidades", "quilombola aqui"),
    ("comunidades", "comunidade tradicional sobreposta"),
    ("comunidades", "territorio quilombola nos limites"),
    ("comunidades", "assentamento rural do INCRA"),
    ("comunidades", "SIPRA nessa area"),
    ("comunidades", "comunidade quilombola identificada"),
    ("comunidades", "reforma agraria assentamento"),
    ("comunidades", "assentados INCRA na regiao"),
    ("comunidades", "comunidade tradicional proxima"),
    ("comunidades", "sobreposicao com assentamento"),
    ("comunidades", "quilombola territorio"),
    ("comunidades", "familiares assentados"),
    ("comunidades", "area de assentamento rural"),
    ("comunidades", "territorio de comunidade remanescente"),
    ("comunidades", "certificacao quilombola"),
    ("comunidades", "assentamento de reforma agraria"),
    ("comunidades", "comunidades tradicionais sobrepostas"),

    # ── relatorio ─────────────────────────────────────────────────────────────
    ("relatorio", "Gera um relatorio ASG completo"),
    ("relatorio", "Quero o resumo dos indicadores ESG da propriedade"),
    ("relatorio", "relatorio ASG da fazenda"),
    ("relatorio", "indice de risco ambiental"),
    ("relatorio", "score ASG da propriedade"),
    ("relatorio", "analise completa ASG"),
    ("relatorio", "indicadores ESG rurais"),
    ("relatorio", "pontuacao de risco ASG"),
    ("relatorio", "risco ASG da propriedade"),
    ("relatorio", "avaliacao ambiental completa"),
    ("relatorio", "panorama ambiental da fazenda"),
    ("relatorio", "resumo ASG do imovel"),
    ("relatorio", "visao geral dos indicadores"),
    ("relatorio", "relatorio completo de sustentabilidade"),
    ("relatorio", "nivel de risco da propriedade"),
    ("relatorio", "indice ESG rural"),
    ("relatorio", "analise de risco socioambiental"),
    ("relatorio", "relatorio de conformidade ambiental"),
    ("relatorio", "diagnostico ASG completo"),
    ("relatorio", "avaliacao de risco fundiario ambiental"),

    # ── variações naturais de linguagem (aumenta vocabulário Word2Vec) ────────
    ("desmatamento", "a mata foi derrubada nessa fazenda"),
    ("desmatamento", "florestas removidas no imovel"),
    ("desmatamento", "vegetacao cortada recentemente"),
    ("desmatamento", "dano florestal identificado"),
    ("desmatamento", "cobertura vegetal reduzida"),
    ("queimada", "chamas detectadas pelo satellite"),
    ("queimada", "fogo ativo na regiao"),
    ("queimada", "rastro de queimada identificado"),
    ("queimada", "vegetacao queimada detectada"),
    ("queimada", "ponto de calor registrado"),
    ("alerta", "sistema de monitoramento disparou alerta"),
    ("alerta", "anomalia detectada pelo INPE"),
    ("alerta", "sinal de alerta florestal"),
    ("alerta", "mudanca de cobertura detectada"),
    ("alerta", "deteccao automatica de supressao"),
    ("indigena", "area com restricao indigena"),
    ("indigena", "populacao indigena no entorno"),
    ("indigena", "limite de terra indigena sobreposto"),
    ("conservacao", "area com restricao ambiental"),
    ("conservacao", "imovel em zona de conservacao"),
    ("conservacao", "limite de parque atingido"),
    ("governanca", "documentacao ambiental do imovel"),
    ("governanca", "regularidade do registro ambiental"),
    ("governanca", "inscricao ambiental verificada"),
    ("fundiario", "registro de propriedade rural"),
    ("fundiario", "dimensoes do terreno declaradas"),
    ("fundiario", "documentacao fundiaria do imovel"),
    ("comunidades", "conflito com comunidade local"),
    ("comunidades", "populacao rural assentada"),
    ("comunidades", "territorio de uso tradicional"),
    ("relatorio", "resultado completo da analise ASG"),
    ("relatorio", "todos os indicadores da propriedade"),
    ("relatorio", "visao consolidada dos riscos"),

    # ── discriminativos para pares confundíveis ────────────────────────────────
    # desmatamento: histórico acumulado, área perdida, PRODES série histórica
    ("desmatamento", "quanto de mata foi perdido historicamente"),
    ("desmatamento", "acumulo de perda florestal ao longo dos anos"),
    ("desmatamento", "debito de vegetacao nativa acumulado"),
    ("desmatamento", "area total suprimida desde 2010"),
    ("desmatamento", "historico de supressao florestal no PRODES"),
    ("desmatamento", "deficit acumulado de reserva legal"),
    ("desmatamento", "area bruta desmatada no imovel"),
    ("desmatamento", "serie historica de perda florestal"),
    ("desmatamento", "quanto de floresta foi retirada no total"),
    ("desmatamento", "desflorestamento acumulado no poligono"),

    # alerta: notificação/aviso recente do sistema de monitoramento, não histórico
    ("alerta", "notificacao do sistema DETER para essa area"),
    ("alerta", "alerta recente emitido pelo INPE"),
    ("alerta", "sinal de atencao emitido pelo DETER recentemente"),
    ("alerta", "aviso de supressao gerado pelo sistema"),
    ("alerta", "alerta ativo no mapa de monitoramento"),
    ("alerta", "DETER disparou notificacao para este poligono"),
    ("alerta", "warning de cobertura gerado automaticamente"),
    ("alerta", "deteccao de mudanca brusca de cobertura recente"),
    ("alerta", "alarme de desmatamento recente emitido"),
    ("alerta", "novo alerta registrado no sistema INPE"),

    # indigena: FUNAI, aldeia, TI, povos originários — território tradicional
    ("indigena", "aldeia no entorno da propriedade"),
    ("indigena", "demarcacao de TI afeta esse imovel"),
    ("indigena", "FUNAI tem interesse nessa area"),
    ("indigena", "povos originarios reivindicam essa terra"),
    ("indigena", "sobreposicao com aldeia oficialmente demarcada"),
    ("indigena", "etnia indigena com territorio nessa regiao"),
    ("indigena", "area de usufruto exclusivo de indigenas"),
    ("indigena", "conflito com povo indigena por essa terra"),
    ("indigena", "grupo etnico indigena nos arredores"),
    ("indigena", "terra oficialmente demarcada pela FUNAI"),

    # comunidades: INCRA, assentamento, quilombola, reforma agrária
    ("comunidades", "projeto de assentamento federal vizinho"),
    ("comunidades", "INCRA tem assentamento nessa area"),
    ("comunidades", "lote de assentado rural sobreposto"),
    ("comunidades", "comunidade remanescente de quilombo"),
    ("comunidades", "territorio de remanescentes quilombolas"),
    ("comunidades", "Palmares certificou quilombola nessa area"),
    ("comunidades", "familias assentadas pela reforma agraria"),
    ("comunidades", "assentamento PA proximo ao imovel"),
    ("comunidades", "lote do INCRA dentro da propriedade"),
    ("comunidades", "beneficiarios da reforma agraria aqui"),

    # conservacao: UC, parque, APA, ICMBio — área protegida por lei ambiental
    ("conservacao", "parque estadual abrange essa area"),
    ("conservacao", "sobreposicao com area de protecao integral"),
    ("conservacao", "APA cobre parte da propriedade"),
    ("conservacao", "ICMBio fiscaliza essa regiao"),
    ("conservacao", "area de amortecimento de unidade de conservacao"),
    ("conservacao", "zona de uso restrito por lei ambiental"),
    ("conservacao", "MMA cadastrou essa area como protegida"),
    ("conservacao", "IBAMA identificou sobreposicao com UC"),
    ("conservacao", "restricao de uso por ser dentro de parque"),
    ("conservacao", "reserva legal sobreposta com area de parque"),

    # relatorio: relatório completo, score, índice, diagnóstico integrado
    ("relatorio", "preciso de um relatorio detalhado dessa fazenda"),
    ("relatorio", "gerar documento completo de analise ASG"),
    ("relatorio", "compilar todos os riscos da propriedade"),
    ("relatorio", "qual o score ambiental desse imovel"),
    ("relatorio", "exportar relatorio de conformidade da fazenda"),

    # governanca: CAR, SICAR, status, compliance, regularidade cadastral
    ("governanca", "verificar se o CAR esta em situacao regular"),
    ("governanca", "conferir pendencias no SICAR"),
    ("governanca", "imovel com CAR ativo ou cancelado"),
    ("governanca", "status de conformidade ambiental do cadastro"),
    ("governanca", "situacao atual do registro no SICAR"),

    # fundiario: tamanho, SIGEF, INCRA, hectares, certidão fundiária
    ("fundiario", "qual a area total registrada no SIGEF"),
    ("fundiario", "certidao de georreferenciamento INCRA"),
    ("fundiario", "quantos hectares tem essa propriedade"),
    ("fundiario", "modulo fiscal equivalente da fazenda"),
    ("fundiario", "numero do NIRF do imovel"),
]

# ── Aumenta corpus com keywords do INTENTS ────────────────────────────────────
DADOS_EXTRA: list[tuple[str, str]] = []
for intent_key, meta in INTENTS.items():
    for kw in meta.get("keywords", []):
        DADOS_EXTRA.append((intent_key, kw))

# ── Geração automática de frases via templates (data augmentation) ────────────
# Cada keyword ≥ 5 chars gera frases completas → vocabulário Word2Vec mais rico
_TEMPLATES = [
    "tem {kw} nessa propriedade",
    "existe {kw} na fazenda",
    "verificar {kw} no imovel",
    "mostrar {kw} da area",
    "informacoes sobre {kw}",
    "historico de {kw} aqui",
    "dados de {kw} da propriedade",
    "consultar {kw} no sistema",
    "quero saber sobre {kw}",
    "ha registro de {kw}",
]
DADOS_TEMPLATES: list[tuple[str, str]] = []
for intent_key, meta in INTENTS.items():
    for kw in meta.get("keywords", []):
        if len(kw) < 5:
            continue
        for tpl in _TEMPLATES:
            DADOS_TEMPLATES.append((intent_key, tpl.format(kw=kw)))

TODOS = DADOS + DADOS_EXTRA + DADOS_TEMPLATES

# ── Tokenização do corpus ─────────────────────────────────────────────────────
sentences = [tokenizar(frase) for _, frase in TODOS]
labels    = [intencao for intencao, _ in TODOS]

print(f"Exemplos de treino: {len(TODOS)} ({len(set(labels))} classes) "
      f"[{len(DADOS)} manuais + {len(DADOS_EXTRA)} keywords + {len(DADOS_TEMPLATES)} templates]")

# ── Treino Word2Vec (padrão do professor: 32 dims, janela 3) ──────────────────
w2v = Word2Vec(
    sentences=sentences,
    vector_size=150,
    window=5,
    min_count=1,
    workers=4,
    epochs=200,
    seed=42,
)
w2v.save(str(MODEL_DIR / "word2vec.model"))
print(f"Word2Vec salvo — vocabulário: {len(w2v.wv)} tokens")

# ── TF-IDF para ponderar os vetores (palavras raras/discriminativas > peso) ───
corpus_texts = [" ".join(s) for s in sentences]
tfidf = TfidfVectorizer()
tfidf.fit(corpus_texts)
joblib.dump(tfidf, MODEL_DIR / "tfidf.joblib")

def representation(tokens: list[str]) -> np.ndarray:
    """Média ponderada por IDF: palavras mais discriminativas têm maior peso."""
    vecs, weights = [], []
    for t in tokens:
        if t in w2v.wv:
            idf = tfidf.idf_[tfidf.vocabulary_[t]] if t in tfidf.vocabulary_ else 1.0
            vecs.append(w2v.wv[t] * idf)
            weights.append(idf)
    if not vecs:
        return np.zeros(w2v.vector_size)
    return np.sum(vecs, axis=0) / max(sum(weights), 1e-8)

X = np.array([representation(s) for s in sentences])
y = np.array(labels)

# ── Treino MLPClassifier ──────────────────────────────────────────────────────
clf = MLPClassifier(
    hidden_layer_sizes=(256, 128, 64),
    activation="relu",
    max_iter=3000,
    learning_rate="adaptive",
    learning_rate_init=0.003,
    alpha=0.0001,
    random_state=42,
)
clf.fit(X, y)

scores = cross_val_score(clf, X, y, cv=5, scoring="accuracy")
print(f"Acurácia (cross-val 5-fold): {scores.mean():.2%} ± {scores.std():.2%}")

joblib.dump(clf, MODEL_DIR / "intent_clf.joblib")
print("MLPClassifier salvo.")
print(f"Classes: {list(clf.classes_)}")
