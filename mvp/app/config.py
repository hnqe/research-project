import os
import logging
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Configurações centralizadas da aplicação."""
    
    # Configurações do Modelo de Embedding
    model_name: str = Field(
        default="intfloat/multilingual-e5-base",
        description="Nome do modelo de embedding do HuggingFace"
    )
    
    # Configurações do Qdrant
    qdrant_host: str = Field(
        default="127.0.0.1",
        description="Host do servidor Qdrant"
    )
    qdrant_port: int = Field(
        default=6333,
        description="Porta do servidor Qdrant"
    )
    qdrant_timeout: int = Field(
        default=30,
        description="Timeout para conexões Qdrant em segundos"
    )
    qdrant_recursos_collection: str = Field(
        default="recursos_cgu_v1",
        description="Nome da coleção de recursos no Qdrant"
    )
    qdrant_pedidos_collection: str = Field(
        default="pedidos_cgu_v1",
        description="Nome da coleção de pedidos no Qdrant"
    )
    
    # Configurações do Groq
    groq_api_key: Optional[str] = Field(
        default=None,
        description="API Key do Groq para geração de minutas"
    )
    groq_model: str = Field(
        default="llama3-70b-8192",
        description="Modelo do Groq para geração de minutas"
    )
    groq_max_requests_per_minute: int = Field(
        default=30,
        description="Limite de requisições por minuto para o Groq"
    )
    groq_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Temperatura para geração de texto no Groq"
    )
    groq_max_tokens: int = Field(
        default=1500,
        gt=0,
        description="Máximo de tokens para resposta do Groq"
    )
    
    # Configurações da Aplicação
    app_title: str = Field(
        default="MVP CGU - Análise de Recursos LAI",
        description="Título da aplicação FastAPI"
    )
    app_version: str = Field(
        default="1.0",
        description="Versão da aplicação"
    )
    log_level: str = Field(
        default="INFO",
        description="Nível de log da aplicação"
    )
    
    # Configurações de Performance
    max_search_results: int = Field(
        default=50,
        gt=0,
        le=100,
        description="Número máximo de resultados de busca"
    )
    default_top_k: int = Field(
        default=10,
        gt=0,
        le=50,
        description="Número padrão de casos similares a retornar"
    )
    min_score_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score mínimo padrão para similaridade"
    )
    
    @validator('groq_api_key', pre=True)
    def get_groq_api_key(cls, v):
        """Obtém a API key do Groq da variável de ambiente se não fornecida."""
        if v is None:
            v = os.getenv('GROQ_API_KEY')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Valida o nível de log."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level deve ser um dos: {valid_levels}')
        return v.upper()
    
    class Config:
        env_prefix = "CGU_"  # Prefixo para variáveis de ambiente
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Instância global das configurações
settings = Settings()

def setup_logging():
    """Configura o sistema de logging baseado nas configurações."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Reduz verbosidade de bibliotecas externas
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    logging.getLogger('transformers').setLevel(logging.WARNING)
    logging.getLogger('torch').setLevel(logging.WARNING)
    
    logger.info(f"Logging configurado para nível {settings.log_level}")

def validate_environment():
    """Valida se o ambiente está corretamente configurado."""
    errors = []
    warnings = []
    
    # Verificações críticas
    if not settings.groq_api_key:
        warnings.append("GROQ_API_KEY não configurada - Geração de minutas será desativada")
    
    # Verificações de rede
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((settings.qdrant_host, settings.qdrant_port))
        sock.close()
        if result != 0:
            errors.append(f"Não foi possível conectar ao Qdrant em {settings.qdrant_host}:{settings.qdrant_port}")
    except Exception as e:
        warnings.append(f"Erro ao verificar conexão Qdrant: {e}")
    
    # Log dos resultados
    if errors:
        logger.error("Erros críticos na validação do ambiente:")
        for error in errors:
            logger.error(f"  - {error}")
    
    if warnings:
        logger.warning("Avisos na validação do ambiente:")
        for warning in warnings:
            logger.warning(f"  - {warning}")
    
    if not errors and not warnings:
        logger.info("Ambiente validado com sucesso")
    
    return len(errors) == 0

def get_data_paths():
    """Retorna os caminhos para os arquivos de dados."""
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    
    return {
        "base_dir": base_dir,
        "data_dir": data_dir,
        "recursos_parquet": data_dir / "dt_recursos.parquet",
        "pedidos_parquet": data_dir / "dt_pedidos.parquet",
        "vetores_dir": data_dir / "vetores",
    }

def print_startup_info():
    """Imprime informações de inicialização da aplicação."""
    info = f"""
🚀 {settings.app_title} v{settings.app_version}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Configurações:
  • Modelo Embedding: {settings.model_name}
  • Qdrant: {settings.qdrant_host}:{settings.qdrant_port}
  • Log Level: {settings.log_level}
  • Max Results: {settings.max_search_results}

🤖 Groq Integration:
  • Status: {'✅ Configurado' if settings.groq_api_key else '❌ Não configurado'}
  • Modelo: {settings.groq_model}
  • Rate Limit: {settings.groq_max_requests_per_minute}/min

📁 Coleções Qdrant:
  • Recursos: {settings.qdrant_recursos_collection}
  • Pedidos: {settings.qdrant_pedidos_collection}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    logger.info(info)