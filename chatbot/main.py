# main.py
import logging
import os
import re
from typing import List, Dict, Optional

import cohere
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.documents import Document
from pydantic import BaseModel

# ─── Configuração de logging ───────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─── Importações locais ────────────────────────────────────────────────
from cgu_rag.pipeline import CGURecommendationPipeline
from cgu_rag.settings import DATA_DIR, VECTORS_DIR, MODEL_NAME, DEVICE

# ─── Variáveis de ambiente / Cohere ────────────────────────────────────
load_dotenv()
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
if not COHERE_API_KEY:
    raise ValueError("A variável de ambiente COHERE_API_KEY não foi definida.")
cohere_client = cohere.Client(api_key=COHERE_API_KEY)

# ─── Carrega dados e pipeline de embeddings ────────────────────────────
try:
    logger.info("Carregando dados...")
    df_ped = pd.read_parquet(DATA_DIR / "dt_pedidos.parquet")
    logger.info(f"Carregados {len(df_ped)} pedidos")
    df_rec = pd.read_parquet(DATA_DIR / "dt_recursos.parquet")
    logger.info(f"Carregados {len(df_rec)} recursos")

    # Ajustes de colunas / tipos
    if "sentence" not in df_ped.columns:
        df_ped["sentence"] = (
                    df_ped["ResumoSolicitacao"].fillna("") + " <SEP> " + df_ped["DetalhamentoSolicitacao"].fillna(""))
    if "sentence" not in df_rec.columns:
        df_rec["sentence"] = (df_rec["TipoRecurso"].fillna("") + " <SEP> " + df_rec["DescRecurso"].fillna(""))

    df_ped["ProtocoloPedido"] = df_ped["ProtocoloPedido"].astype(str)
    df_rec["ProtocoloPedido"] = df_rec["ProtocoloPedido"].astype(str)
    if "IdRecurso" in df_rec.columns:
        df_rec["IdRecurso"] = df_rec["IdRecurso"].astype(str)
    else:
        df_rec["IdRecurso"] = ""

    logger.info("Otimizando estruturas de dados para lookups rápidos...")
    RECURSO_IDS_SET = set(df_rec["IdRecurso"].unique())
    RECURSOS_POR_PEDIDO = {
        name: group.to_dict('records')
        for name, group in df_rec.groupby("ProtocoloPedido")
    }
    logger.info("Otimizações de lookup concluídas.")

    logger.info("Inicializando pipeline de embeddings...")
    pipe = CGURecommendationPipeline(MODEL_NAME, DEVICE)
    pipe.load_vectorstore(VECTORS_DIR, "pedidos")
    pipe.load_vectorstore(VECTORS_DIR, "recursos")
    logger.info("Pipeline carregado com sucesso!")

except Exception as e:
    logger.error(f"Erro fatal ao carregar dados/pipeline: {e}", exc_info=True)
    raise

# ─── FastAPI init ──────────────────────────────────────────────────────
app = FastAPI(
    title="Chat-CGU com Busca Multi-Etapas",
    version="7.0.0",
    description="Sistema RAG avançado que responde perguntas complexas sobre pedidos e recursos de acesso à informação.",
)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Schemas ───────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    k: int = 5


class ChatResponse(BaseModel):
    answer: str
    sources: Optional[List[Dict]] = None
    error: Optional[str] = None


ENHANCED_PROMPT = """Você é um assistente especialista na Lei de Acesso à Informação, operando com regras extremamente rígidas.

[REGRAS FUNDAMENTAIS]
1.  **FIDELIDADE ABSOLUTA AO CONTEXTO**: Sua resposta DEVE ser construída USANDO APENAS E SOMENTE AS PALAVRAS E DADOS dos documentos fornecidos na seção [DOCUMENTOS DE CONTEXTO].
2.  **PROIBIDO INVENTAR**: É terminantemente proibido inventar, criar, alucinar ou inferir qualquer informação que não esteja explicitamente escrita no contexto. Isso inclui números de protocolo, IDs de recurso, resumos ou exemplos.
3.  **SE NÃO ESTÁ ESCRITO, NÃO EXISTE**: Se a pergunta não pode ser respondida com o contexto, responda EXATAMENTE: "A informação não está disponível nos documentos fornecidos." Não tente ser prestativo ou adivinhar.
4.  **SEJA LITERAL E PRECISO**: Ao citar um pedido ou recurso, use os dados EXATOS (protocolo, órgão, situação, etc.) como aparecem no contexto.

[DOCUMENTOS DE CONTEXTO]
{context}
[/DOCUMENTOS DE CONTEXTO]

[PERGUNTA DO USUÁRIO]
{question}
[/PERGUNTA DO USUÁRIO]

RESPOSTA:"""


# ─── Funções auxiliares ────────
def detectar_protocolo(texto: str) -> Optional[str]:
    match = re.search(r"\b\d{14,}\b", texto)
    return match.group() if match else None


def detectar_id_recurso(texto: str) -> Optional[str]:
    match = re.search(r"\b(\d{4,8})\b", texto)
    if match and (num := match.group(1)) in RECURSO_IDS_SET:
        return num
    return None


def menciona_recursos(texto: str) -> bool:
    termos = ["recurso", "recursos", "reclamação", "indeferido", "negado", "deferido", "decisão", "recursal",
              "recorrido"]
    # Ativa se menciona um termo de recurso E NÃO é uma busca direta por ID de recurso
    return any(t in texto.lower() for t in termos) and not detectar_id_recurso(texto)


def buscar_recursos_do_pedido(protocolo: str) -> pd.DataFrame:
    recursos_list = RECURSOS_POR_PEDIDO.get(str(protocolo), [])
    return pd.DataFrame(recursos_list)


def formatar_documento_detalhado(doc, idx=1, is_recurso=False):
    meta = doc.metadata
    if is_recurso:
        return (
            f"--- [Documento {idx}: RECURSO] ---\n"
            f"ID do Recurso: {meta.get('IdRecurso', 'N/A')}\n"
            f"Protocolo do Pedido Associado: {meta.get('ProtocoloPedido', 'N/A')}\n"
            f"Decisão do Recurso: {meta.get('TipoResposta', 'Em análise')}\n"
            f"Texto do Recurso: {doc.page_content}"
        )
    else:
        protocolo = meta.get("ProtocoloPedido", "N/A")
        recursos_v = buscar_recursos_do_pedido(str(protocolo))
        recursos_str = "Recursos Vinculados: Não há.\n"
        if not recursos_v.empty:
            recursos_str = f"Recursos Vinculados: SIM ({len(recursos_v)})\n"
            for rec in recursos_v.to_dict('records'):
                recursos_str += f"  - Recurso ID {rec.get('IdRecurso', 'N/A')}: Decisão '{rec.get('TipoResposta', 'N/A')}'\n"
        return (
            f"--- [Documento {idx}: PEDIDO] ---\n"
            f"Protocolo: {protocolo}\n"
            f"Órgão: {meta.get('OrgaoDestinatario', 'N/A')}\n"
            f"Situação do Pedido: {meta.get('Situacao', 'N/A')}\n"
            f"{recursos_str}"
            f"Conteúdo do Pedido: {doc.page_content}"
        )


# ─── LÓGICA DE RECUPERAÇÃO DE CONTEXTO ─────────────────────────────────
def get_enhanced_context(query: str, k: int):
    try:
        # Rota 1: Busca direta por ID de protocolo
        if protocolo := detectar_protocolo(query):
            return _contexto_por_protocolo(protocolo)

        # Rota 2: Busca direta por ID de recurso
        if id_recurso := detectar_id_recurso(query):
            return _contexto_por_id_recurso(id_recurso)

        # Rota 3: Pergunta complexa que cruza pedidos e recursos
        if menciona_recursos(query):
            contexto, sources = _contexto_busca_pedidos_com_recursos(query, k)
            if sources:  # Se a busca multi-etapas encontrou algo, use-a.
                return contexto, sources

        # Rota 4: Busca genérica por recursos (se a Rota 3 não funcionou)
        if menciona_recursos(query) and pipe.vectorstore_recursos:
            return _contexto_busca_recursos(query, k)

        # Rota 5 (Padrão): Busca genérica por pedidos
        return _contexto_busca_pedidos(query, k)

    except Exception as e:
        logger.error(f"Erro ao obter contexto para query '{query[:50]}...': {e}", exc_info=True)
        return f"Erro interno ao buscar informações: {e}", []


# ------------------------ HELPER DE CONTEXTO: BUSCA MULTI-ETAPAS -------------------------
def _contexto_busca_pedidos_com_recursos(query: str, k: int):
    logger.info(f"Executando busca multi-etapas para: '{query}'")
    # ETAPA 1: Busca um número maior de pedidos sobre o tema para ter mais chances de encontrar um com recurso
    docs_pedidos, results_df = pipe.find_similar_pedidos(query, df_pedidos=df_ped, k=k * 5)

    # ETAPA 2: Filtra os resultados para manter apenas os que têm recursos
    pedidos_com_recursos_indices = results_df['ProtocoloPedido'].isin(RECURSOS_POR_PEDIDO.keys())
    resultados_filtrados = results_df[pedidos_com_recursos_indices]

    if resultados_filtrados.empty:
        logger.info("Nenhum pedido com recurso encontrado na busca multi-etapas.")
        return "Nenhum pedido com recursos sobre este tópico foi encontrado.", []

    # ETAPA 3: Monta o contexto e as fontes com os resultados filtrados
    resultados_finais = resultados_filtrados.head(k)
    docs_finais = [doc for doc in docs_pedidos if
                   doc.metadata['ProtocoloPedido'] in resultados_finais['ProtocoloPedido'].values]

    context = "[PEDIDOS COM RECURSOS VINCULADOS ENCONTRADOS NA BUSCA]\n"
    for i, doc in enumerate(docs_finais, 1):
        context += formatar_documento_detalhado(doc, i) + "\n\n"

    sources = []
    for _, row in resultados_finais.iterrows():
        protocolo = str(row.get("ProtocoloPedido"))
        sources.append({
            "protocolo": protocolo,
            "orgao": row.get("OrgaoDestinatario", "N/A"),
            "data": row.get("DataRegistro", "N/A"),
            "situacao": row.get("Situacao", "N/A"),
            "score": float(row.get("score", 0)),
            "resumo": (row.get("page_content") or "")[:200] + "...",
            "num_recursos": len(RECURSOS_POR_PEDIDO.get(protocolo, [])),
        })
    return context, sources


# ------------------------ HELPERS DE CONTEXTO: BUSCAS DIRETAS E SIMPLES -------------------------
def _contexto_por_protocolo(protocolo: str):
    pedido_espec = df_ped[df_ped["ProtocoloPedido"] == protocolo]
    if pedido_espec.empty: return f"Não foi encontrado nenhum pedido com o protocolo {protocolo}.", []
    pedido = pedido_espec.iloc[0].to_dict()
    contexto_doc = Document(page_content=pedido.get('sentence', ''), metadata=pedido)
    context = "[PEDIDO ESPECÍFICO ENCONTRADO]\n" + formatar_documento_detalhado(contexto_doc)
    sources = [{
        "protocolo": pedido.get("ProtocoloPedido"), "orgao": pedido.get("OrgaoDestinatario"),
        "data": pedido.get("DataRegistro"),
        "situacao": pedido.get("Situacao"), "score": 1.0,
        "resumo": (pedido.get("ResumoSolicitacao") or "")[:200] + "...",
        "num_recursos": len(RECURSOS_POR_PEDIDO.get(protocolo, [])),
    }]
    return context, sources


def _contexto_por_id_recurso(id_recurso: str):
    rec_df = df_rec[df_rec["IdRecurso"] == id_recurso]
    if rec_df.empty: return f"Não foi encontrado nenhum recurso com o ID {id_recurso}.", []
    rec = rec_df.iloc[0].to_dict()
    contexto_doc = Document(page_content=rec.get('sentence', ''), metadata=rec)
    context = "[RECURSO ESPECÍFICO ENCONTRADO]\n" + formatar_documento_detalhado(contexto_doc, is_recurso=True)
    sources = [{
        "protocolo": rec.get("ProtocoloPedido"), "orgao": rec.get("OrgaoPedido"), "data": "N/A",
        "situacao": f"Recurso ID {id_recurso} - Decisão: {rec.get('TipoResposta', 'Em análise')}",
        "score": 1.0, "resumo": (rec.get("DescRecurso") or "")[:200] + "..."
    }]
    return context, sources


def _contexto_busca_recursos(query: str, k: int):
    docs, results = pipe.find_similar_recursos(query, df_recursos=df_rec, k=k)
    if not docs: return "Nenhum recurso relevante foi encontrado.", []
    context = "[RECURSOS ENCONTRADOS NA BUSCA POR SIMILARIDADE]\n"
    for i, doc in enumerate(docs, 1): context += formatar_documento_detalhado(doc, i, is_recurso=True) + "\n"
    sources = [{"protocolo": row.get("ProtocoloPedido"), "orgao": row.get("OrgaoPedido"), "data": "N/A",
                "situacao": f"Recurso ID {row.get('IdRecurso')} - {row.get('TipoResposta', 'N/A')}",
                "score": float(row.get("score", 0)), "resumo": (row.get("page_content") or "")[:200] + "..."}
               for _, row in results.iterrows()]
    return context, sources


def _contexto_busca_pedidos(query: str, k: int):
    docs, results = pipe.find_similar_pedidos(query, df_pedidos=df_ped, k=k)
    if not docs: return "Nenhum pedido relevante foi encontrado.", []
    context = "[PEDIDOS ENCONTRADOS NA BUSCA POR SIMILARIDADE]\n"
    for i, doc in enumerate(docs, 1): context += formatar_documento_detalhado(doc, i) + "\n"
    sources = []
    for _, row in results.iterrows():
        protocolo = str(row.get("ProtocoloPedido"))
        sources.append({"protocolo": protocolo, "orgao": row.get("OrgaoDestinatario"), "data": row.get("DataRegistro"),
                        "situacao": row.get("Situacao"), "score": float(row.get("score", 0)),
                        "resumo": (row.get("page_content") or "")[:200] + "...",
                        "num_recursos": len(RECURSOS_POR_PEDIDO.get(protocolo, []))})
    return context, sources


# ─── Endpoint de Chat ──────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
async def chat_enhanced(req: ChatRequest):
    try:
        logger.info(f"Pergunta recebida: '{req.message[:60]}...' (k={req.k})")
        context, sources = get_enhanced_context(req.message, req.k)
        if not sources: return ChatResponse(answer=context or "Não encontrei informações sobre isso.", sources=[])
        prompt = ENHANCED_PROMPT.format(context=context, question=req.message)
        response = cohere_client.chat(model="command-r-plus", message=prompt, temperature=0.1, p=0.9)
        answer = response.text.strip()
        if "RESPOSTA:" in answer: answer = answer.split("RESPOSTA:")[-1].strip()
        logger.info(f"Resposta gerada: '{answer[:80]}...'")
        return ChatResponse(answer=answer, sources=sources)
    except Exception as e:
        logger.error(f"Erro no endpoint /chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro interno: {e}")


# ─── Endpoints de Apoio ────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root(): return FileResponse("static/index.html")


@app.get("/stats")
async def stats():
    return {"total_pedidos": len(df_ped), "total_recursos": len(df_rec), "embedding_model": MODEL_NAME,
            "llm_provider": "Cohere (command-r-plus)",
            "retrieval_strategy": "Hybrid (ID/Keyword Detection + Multi-Step Similarity Search)",
            "status": "operacional"}


# ─── Execução ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)