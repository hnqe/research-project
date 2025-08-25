# models.py
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Union, Optional, Any


# Modelo para a requisição de análise de recurso
class AppealQuery(BaseModel):
    text: str = Field(
        ..., 
        min_length=10, 
        max_length=5000,
        description="Texto do recurso a ser analisado",
        example="Solicito acesso aos contratos firmados pela CGU em 2023..."
    )
    top_k: int = Field(
        10, 
        gt=0, 
        le=50,
        description="Número máximo de casos similares a retornar",
        example=5
    )
    instance_filter: Optional[str] = Field(
        None,
        description="Filtrar por instância específica (ex: CGU, ANATEL)",
        example="CGU"
    )
    min_score: float = Field(
        0.0, 
        ge=0.0, 
        le=1.0,
        description="Score mínimo de similaridade (0.0 a 1.0)",
        example=0.7
    )
    
    @validator('text')
    def validate_text(cls, v):
        if not v or v.isspace():
            raise ValueError('O texto do recurso não pode estar vazio')
        return v.strip()
    
    @validator('instance_filter')
    def validate_instance_filter(cls, v):
        if v:
            return v.strip().upper()
        return v


# Modelo para cada recurso similar retornado
class SimilarAppeal(BaseModel):
    id: int = Field(..., description="ID único do recurso")
    score: float = Field(..., ge=0.0, le=1.0, description="Score de similaridade")
    description: str = Field(..., description="Descrição do recurso")
    response: str = Field(..., description="Resposta oficial ao recurso")
    decision: str = Field(..., description="Decisão final (Deferido, Indeferido, etc.)")
    instance: str = Field(..., description="Instância que analisou o recurso")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 12345,
                "score": 0.85,
                "description": "Solicito acesso aos contratos...",
                "response": "No exercício das atribuições...",
                "decision": "Indeferido",
                "instance": "CGU"
            }
        }


# Modelo para o resultado final da análise de recurso (básico)
class AnalysisResult(BaseModel):
    likely_decision: str = Field(
        ..., 
        description="Predição da decisão mais provável",
        example="Provavelmente Indeferido"
    )
    decision_stats: Dict[str, Dict[str, Union[float, int]]] = Field(
        ...,
        description="Estatísticas das decisões dos casos similares"
    )
    similar_appeals: List[SimilarAppeal] = Field(
        ...,
        description="Lista de recursos similares encontrados"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "likely_decision": "Provavelmente Indeferido",
                "decision_stats": {
                    "Indeferido": {"count": 3, "percentage": 60.0},
                    "Deferido": {"count": 2, "percentage": 40.0}
                },
                "similar_appeals": []
            }
        }


# Modelo para o resultado COM minuta gerada
class AnalysisResultWithDraft(AnalysisResult):
    draft_response: str = Field(
        ..., 
        description="Minuta de resposta gerada automaticamente pela IA",
        min_length=100
    )
    generation_metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="Metadados sobre a geração da minuta (modelo, tokens, etc.)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "likely_decision": "Provavelmente Indeferido",
                "decision_stats": {},
                "similar_appeals": [],
                "draft_response": "DECISÃO\n\nConsiderando o recurso interposto...",
                "generation_metadata": {
                    "model_used": "llama3-70b-8192",
                    "tokens_used": 1500,
                    "generation_time": "~2 segundos"
                }
            }
        }


# Modelo para cada pedido similar retornado
class SimilarRequest(BaseModel):
    id: int = Field(..., description="ID único do pedido")
    protocol: str = Field(..., description="Protocolo do pedido")
    score: float = Field(..., ge=0.0, le=1.0, description="Score de similaridade")
    summary: str = Field(..., description="Resumo da solicitação")
    details: str = Field(..., description="Detalhamento da solicitação")
    decision: str = Field(..., description="Decisão sobre o pedido")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 54321,
                "protocol": "25820.123456/2023-11",
                "score": 0.92,
                "summary": "Acesso a contratos públicos",
                "details": "Solicitação de acesso aos contratos...",
                "decision": "Deferido"
            }
        }


# Modelo para o resultado da busca por protocolo (com protocolo original + similares)
class ProtocolSearchResult(BaseModel):
    original_request: SimilarRequest = Field(..., description="Pedido original buscado")
    similar_requests: List[SimilarRequest] = Field(..., description="Pedidos similares encontrados")
    
    class Config:
        json_schema_extra = {
            "example": {
                "original_request": {
                    "id": 12345,
                    "protocol": "60110003084201855",
                    "score": 1.0,
                    "summary": "Solicitação de contratos",
                    "details": "Prezados, venho solicitar...",
                    "decision": "Acesso Concedido"
                },
                "similar_requests": []
            }
        }