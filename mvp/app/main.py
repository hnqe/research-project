import os
import logging
from pathlib import Path
from dotenv import load_dotenv

dotenv_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from qdrant_client import QdrantClient, models
from langchain_huggingface import HuggingFaceEmbeddings
from typing import List

from app.models import AppealQuery, AnalysisResult, SimilarRequest, AnalysisResultWithDraft, ProtocolSearchResult
from datetime import datetime
import app.services as services
from app.groq_minuta_generator import GroqMinutaGenerator
from app.config import settings, setup_logging, validate_environment, print_startup_info

# Configura logging antes de criar a aplicação
setup_logging()

app = FastAPI(
    title=settings.app_title,
    description="API para análise de recursos e busca de contexto em pedidos da LAI com geração automática de minutas.",
    version=settings.app_version,
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

embedding_model = None
qdrant_client = None
minuta_generator = None


@app.on_event("startup")
def startup_event():
    global embedding_model, qdrant_client, minuta_generator
    try:
        # Valida ambiente antes de inicializar
        if not validate_environment():
            logger.error("❌ Falha na validação do ambiente")
            raise Exception("Ambiente não está corretamente configurado")
        
        logger.info("Carregando modelo de embedding...")
        embedding_model = HuggingFaceEmbeddings(model_name=settings.model_name)
        logger.info("✅ Modelo de embedding carregado")

        logger.info("Conectando ao Qdrant...")
        qdrant_client = QdrantClient(
            host=settings.qdrant_host, 
            port=settings.qdrant_port,
            timeout=settings.qdrant_timeout
        )

        recursos_info = qdrant_client.get_collection(settings.qdrant_recursos_collection)
        pedidos_info = qdrant_client.get_collection(settings.qdrant_pedidos_collection)
        logger.info("✅ Conectado ao Qdrant")
        logger.info(f"  - Coleção de Recursos: {recursos_info.points_count} pontos")
        logger.info(f"  - Coleção de Pedidos: {pedidos_info.points_count} pontos")

        logger.info("Inicializando gerador de minutas...")
        if settings.groq_api_key:
            minuta_generator = GroqMinutaGenerator(
                api_key=settings.groq_api_key
            )
            logger.info("✅ Gerador de minutas com Groq API inicializado")
        else:
            logger.warning("⚠️ GROQ_API_KEY não configurada - Geração de minutas desativada")

        # Exibe informações de inicialização
        print_startup_info()

    except Exception as e:
        logger.error(f"❌ Erro crítico na inicialização: {e}")
        raise


@app.get("/", tags=["Status"])
def root():
    """Endpoint raiz com informações básicas."""
    return {
        "message": "MVP CGU - Análise de Recursos LAI",
        "version": settings.app_version,
        "features": {
            "analise_preditiva": True,
            "casos_similares": True,
            "geracao_minutas": minuta_generator is not None
        },
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["Status"])
def health_check():
    """Verifica a saúde do serviço e a conexão com o Qdrant."""
    try:
        recursos_info = qdrant_client.get_collection(collection_name=settings.qdrant_recursos_collection)
        pedidos_info = qdrant_client.get_collection(collection_name=settings.qdrant_pedidos_collection)
        
        health_data = {
            "status": "ok", 
            "qdrant_connection": True, 
            "recursos_count": recursos_info.points_count,
            "pedidos_count": pedidos_info.points_count,
            "config": {
                "model_name": settings.model_name,
                "groq_enabled": bool(settings.groq_api_key),
                "version": settings.app_version
            }
        }
        
        if minuta_generator:
            health_data["groq_stats"] = minuta_generator.get_usage_stats()
        
        return health_data
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Erro ao conectar com o Qdrant: {e}")


@app.post("/analyze-appeal", response_model=AnalysisResult, tags=["Análise de Recursos"])
def analyze_appeal(query: AppealQuery):
    """
    Analisa um recurso, aplicando filtros inteligentes, e retorna predição + casos similares.
    Este é o endpoint principal de busca.
    """
    try:
        query_vector = embedding_model.embed_query(query.text)

        # --- LÓGICA DE FILTRO INTELIGENTE ---
        filter_conditions = []
        if query.instance_filter:
            filter_conditions.append(
                models.FieldCondition(key="instance", match=models.MatchValue(value=query.instance_filter))
            )

            if query.instance_filter.upper() == "CGU":
                filter_conditions.append(
                    models.FieldCondition(key="context", match=models.MatchValue(value="orgao_demandado"))
                )

        # Monta o filtro final somente se houver condições
        query_filter = models.Filter(must=filter_conditions) if filter_conditions else None

        logger.debug(f"Filtro Qdrant aplicado: {query_filter}")

        search_results = qdrant_client.search(
            collection_name=settings.qdrant_recursos_collection,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=min(query.top_k, settings.max_search_results),
            with_payload=True,
            score_threshold=query.min_score
        )

        if not search_results:
            # Se não encontrou NADA, vamos dar uma mensagem de erro específica
            if query_filter:
                raise HTTPException(
                    status_code=404,
                    detail=f"Nenhum recurso similar encontrado que satisfaça os filtros aplicados: {query_filter}"
                )
            else:
                raise HTTPException(
                    status_code=404,
                    detail="Nenhum recurso similar encontrado com os critérios especificados."
                )

        decision_stats = services.analyze_decision_stats(search_results)

        return AnalysisResult(
            likely_decision=services.determine_likely_decision(decision_stats),
            decision_stats=decision_stats,
            similar_appeals=services.format_similar_appeals(search_results),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado em analyze_appeal: {e}")
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro interno: {e}")


@app.post("/analyze-appeal-with-draft", response_model=AnalysisResultWithDraft, tags=["Análise de Recursos"])
def analyze_appeal_with_draft(query: AppealQuery):
    """
    Analisa um recurso (usando a mesma lógica de /analyze-appeal) e adiciona uma minuta gerada por IA.
    """
    if not minuta_generator:
        raise HTTPException(
            status_code=501,
            detail="Funcionalidade de geração de minutas não está disponível. Configure GROQ_API_KEY."
        )

    try:
        # 1. Reutiliza o endpoint de análise principal para obter os dados
        analysis_result = analyze_appeal(query)

        # 2. Gera a minuta com base nos resultados da análise
        result = minuta_generator.generate_minuta(
            appeal_text=query.text,
            similar_cases=[case.dict() for case in analysis_result.similar_appeals],
            prediction=analysis_result.likely_decision,
            decision_stats=analysis_result.decision_stats
        )
        draft_response = result.get("minuta", "Erro ao gerar minuta.")
        generation_metadata = result.get("metadata", {})

        # 3. Combina os resultados e retorna
        return AnalysisResultWithDraft(
            likely_decision=analysis_result.likely_decision,
            decision_stats=analysis_result.decision_stats,
            similar_appeals=analysis_result.similar_appeals,
            draft_response=draft_response,
            generation_metadata=generation_metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na geração da minuta: {e}")
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro na geração da minuta: {e}")


# ... (O resto dos endpoints, como /context-by-protocol, /instances, etc. podem continuar os mesmos) ...

@app.get("/similar-appeals/{appeal_id}", tags=["Contexto de Recursos"])
def find_similar_appeals(appeal_id: str, top_k: int = 5):
    """
    Encontra um recurso pelo seu ID e busca outros recursos com conteúdo similar.
    """
    try:
        # Converter appeal_id para inteiro
        try:
            appeal_as_int = int(appeal_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"ID do recurso '{appeal_id}' deve ser um número válido."
            )
            
        # Buscar pelo ID do ponto diretamente
        try:
            logger.info(f"Buscando recurso com ID: {appeal_as_int}")
            found_point = qdrant_client.retrieve(
                collection_name=settings.qdrant_recursos_collection,
                ids=[appeal_as_int],
                with_vectors=True
            )
            
            logger.info(f"Resultado da busca: {len(found_point) if found_point else 0} pontos encontrados")
            
            if not found_point:
                logger.warning(f"Nenhum ponto encontrado para ID {appeal_as_int}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Recurso com ID '{appeal_id}' não encontrado."
                )
            
            original_point = found_point[0]
            logger.info(f"Ponto encontrado: ID {original_point.id}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao buscar recurso ID {appeal_as_int}: {e}")
            raise HTTPException(
                status_code=404,
                detail=f"Recurso com ID '{appeal_id}' não encontrado."
            )

        search_results = qdrant_client.search(
            collection_name=settings.qdrant_recursos_collection,
            query_vector=original_point.vector,
            query_filter=models.Filter(
                must_not=[models.HasIdCondition(has_id=[original_point.id])]
            ),
            limit=top_k,
            with_payload=True
        )

        # Criar objeto para o recurso original encontrado
        original_appeal = {
            "id": original_point.id,
            "score": 1.0,  # Score perfeito para o original
            "description": original_point.payload.get("description", ""),
            "response": original_point.payload.get("response", ""),
            "decision": original_point.payload.get("decision", "N/A"),
            "instance": original_point.payload.get("instance", "N/A")
        }
        
        # Criar lista de recursos similares
        similar_appeals = []
        for r in search_results:
            similar_appeals.append({
                "id": r.id,
                "score": r.score,
                "description": r.payload.get("description", ""),
                "response": r.payload.get("response", ""),
                "decision": r.payload.get("decision", "N/A"),
                "instance": r.payload.get("instance", "N/A")
            })
        
        return {
            "original_appeal": original_appeal,
            "similar_appeals": similar_appeals
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro em find_similar_appeals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/context-by-protocol/{protocol_id}", response_model=ProtocolSearchResult, tags=["Contexto de Pedidos"])
def find_similar_requests(protocol_id: str, top_k: int = 5):
    """
    Encontra um pedido pelo seu protocolo e busca outros pedidos com conteúdo similar.
    """
    try:
        # Converter protocol_id para inteiro, pois está armazenado como número no Qdrant
        try:
            protocol_as_int = int(protocol_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Protocolo '{protocol_id}' deve ser um número válido."
            )
            
        found_points, _ = qdrant_client.scroll(
            collection_name=settings.qdrant_pedidos_collection,
            scroll_filter=models.Filter(must=[
                models.FieldCondition(key="protocol", match=models.MatchValue(value=protocol_as_int))
            ]),
            limit=1, with_vectors=True
        )

        if not found_points:
            raise HTTPException(
                status_code=404,
                detail=f"Pedido com protocolo '{protocol_id}' não encontrado."
            )

        original_point = found_points[0]

        search_results = qdrant_client.search(
            collection_name=settings.qdrant_pedidos_collection,
            query_vector=original_point.vector,
            query_filter=models.Filter(
                must_not=[models.HasIdCondition(has_id=[original_point.id])]
            ),
            limit=top_k,
            with_payload=True
        )

        # Criar objeto para o pedido original encontrado
        original_request = SimilarRequest(
            id=original_point.id,
            protocol=str(original_point.payload.get("protocol", "")),
            score=1.0,  # Score perfeito para o original
            summary=original_point.payload.get("summary", ""),
            details=original_point.payload.get("details", ""),
            decision=original_point.payload.get("decision", "N/A")
        )
        
        # Criar lista de pedidos similares
        similar_requests = [
            SimilarRequest(
                id=r.id,
                protocol=str(r.payload.get("protocol", "")),
                score=r.score,
                summary=r.payload.get("summary", ""),
                details=r.payload.get("details", ""),
                decision=r.payload.get("decision", "N/A")
            ) for r in search_results
        ]
        
        return ProtocolSearchResult(
            original_request=original_request,
            similar_requests=similar_requests
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro em find_similar_requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/instances", tags=["Utilitários"])
def get_available_instances():
    """
    Retorna as instâncias disponíveis para filtro.
    """
    try:
        points, _ = qdrant_client.scroll(
            collection_name=settings.qdrant_recursos_collection,
            limit=1000,
            with_payload=True
        )

        instances = set()
        for point in points:
            instance = point.payload.get("instance")
            if instance and instance != "N/A":
                instances.add(instance)

        return {"instances": sorted(list(instances))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/minuta-status", tags=["Geração de Minutas"])
def get_minuta_generation_status():
    """Verifica status da funcionalidade de geração de minutas."""
    if minuta_generator:
        stats = minuta_generator.get_usage_stats()
        return {
            "available": True,
            "status": "operational",
            "model": minuta_generator.model,
            "provider": "Groq",
            "usage_stats": stats
        }
    else:
        return {
            "available": False,
            "status": "not_configured",
            "message": "Configure GROQ_API_KEY para ativar geração de minutas",
            "config_help": "Defina a variável de ambiente CGU_GROQ_API_KEY ou GROQ_API_KEY"
        }


@app.post("/download-minuta", tags=["Geração de Minutas"])
def download_minuta(data: dict):
    """
    Endpoint para download de minuta formatada.
    Recebe os dados da análise e retorna um arquivo de texto para download.
    """
    try:
        # Extrair dados necessários
        appeal_text = data.get('appeal_text', '')
        draft_response = data.get('draft_response', '')
        likely_decision = data.get('likely_decision', '')
        decision_stats = data.get('decision_stats', {})
        generation_metadata = data.get('generation_metadata', {})
        similar_appeals_count = data.get('similar_appeals_count', 0)
        
        if not draft_response:
            raise HTTPException(status_code=400, detail="Minuta não disponível para download")
        
        # Criar conteúdo formatado
        now = datetime.now()
        content = f"""MINUTA DE DECISÃO - CGU LAI
===============================================

Data de Geração: {now.strftime('%d/%m/%Y')} às {now.strftime('%H:%M:%S')}

RECURSO ANALISADO:
{appeal_text}

DECISÃO PROPOSTA:
{likely_decision}

MINUTA GERADA PELA IA:
=====================

{draft_response}

===============================================
INFORMAÇÕES TÉCNICAS:

{chr(10).join([f"{key.replace('_', ' ').upper()}: {value}" for key, value in generation_metadata.items()]) if generation_metadata else 'Metadados não disponíveis'}

CASOS SIMILARES ANALISADOS: {similar_appeals_count}

ESTATÍSTICAS DE DECISÃO:
{chr(10).join([f"{decision}: {stats['count']} casos ({stats['percentage']:.1f}%)" for decision, stats in decision_stats.items()]) if decision_stats else 'Estatísticas não disponíveis'}

===============================================
⚠️  ATENÇÃO: Esta minuta foi gerada automaticamente por IA e REQUER REVISÃO MANUAL antes de ser utilizada oficialmente.
==============================================="""
        
        # Nome do arquivo com data/hora
        filename = f"Minuta_CGU_LAI_{now.strftime('%d-%m-%Y_%H-%M')}.txt"
        
        # Retornar como resposta de download
        return Response(
            content=content.encode('utf-8'),
            media_type='text/plain; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'text/plain; charset=utf-8'
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar download da minuta: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao preparar download: {e}")