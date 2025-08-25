# index_to_qdrant.py
import os
import pickle
import logging
import pandas as pd
from qdrant_client import QdrantClient, models
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Configurações ---
# Garante que o script encontre a pasta 'data' no diretório raiz do projeto.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data")
VETORES_PATH = os.path.join(DATA_PATH, "vetores")

# Caminhos para os arquivos de dados brutos
RECURSOS_PARQUET_PATH = os.path.join(DATA_PATH, "dt_recursos.parquet")
PEDIDOS_PARQUET_PATH = os.path.join(DATA_PATH, "dt_pedidos.parquet")

# Caminhos para os vetores pré-gerados
NOME_BASE_ARQUIVO = "intfloat_multilingual-e5-base_ft_False"
RECURSOS_PICKLE_PATH = os.path.join(VETORES_PATH, f"{NOME_BASE_ARQUIVO}_vetores_recursos_2015_2023.pkl")
PEDIDOS_PICKLE_PATH = os.path.join(VETORES_PATH, f"{NOME_BASE_ARQUIVO}_vetores_pedidos_2015_2023.pkl")

# Configs do Qdrant (com suporte a variáveis de ambiente)
QDRANT_HOST = os.getenv("QDRANT_HOST", "127.0.0.1")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_RECURSOS_COLLECTION_NAME = "recursos_cgu_v1"
QDRANT_PEDIDOS_COLLECTION_NAME = "pedidos_cgu_v1"


def validate_files(parquet_path: str, pickle_path: str) -> bool:
    """Valida se os arquivos existem e são válidos."""
    if not os.path.exists(parquet_path):
        logger.error(f"Arquivo Parquet não encontrado: {parquet_path}")
        return False
        
    if not os.path.exists(pickle_path):
        logger.error(f"Arquivo Pickle não encontrado: {pickle_path}")
        return False
        
    try:
        # Testa leitura dos arquivos
        df_test = pd.read_parquet(parquet_path)
        logger.info(f"Arquivo Parquet válido: {len(df_test)} registros")
        
        with open(pickle_path, 'rb') as f:
            data = pickle.load(f)
            if 'embeddings' not in data:
                logger.error("Arquivo pickle não contém chave 'embeddings'")
                return False
            logger.info(f"Arquivo Pickle válido: {len(data['embeddings'])} embeddings")
            
    except Exception as e:
        logger.error(f"Erro ao validar arquivos: {e}")
        return False
        
    return True

def index_from_precomputed(
        collection_name: str,
        parquet_path: str,
        pickle_path: str,
        id_column: str,
        payload_columns: dict,
        client: QdrantClient,
        is_recurso: bool = False
):
    """
    Indexa dados no Qdrant usando metadados de um Parquet e vetores pré-calculados de um Pickle.
    A função confia que a ordem dos registros no Parquet e no Pickle é a mesma.
    """
    logger.info(f"Iniciando indexação para: {collection_name}")
    
    # Validação dos arquivos
    if not validate_files(parquet_path, pickle_path):
        logger.error("Falha na validação dos arquivos")
        return False

    try:
        # 1. Carregar metadados do Parquet
        logger.info(f"Carregando metadados de {parquet_path}")
        df_full = pd.read_parquet(parquet_path)
        df_full[id_column] = df_full[id_column].astype(str)
        logger.info(f"Carregados {len(df_full)} registros do Parquet")

        # 2. Carregar vetores pré-calculados do Pickle
        logger.info(f"Carregando vetores pré-calculados de {pickle_path}")

        with open(pickle_path, 'rb') as f:
            data = pickle.load(f)

        if not isinstance(data, dict) or 'embeddings' not in data:
            logger.error(f"Arquivo .pkl não contém a chave 'embeddings'")
            return False

        vetores = data['embeddings']
        logger.info(f"Carregados {len(vetores)} vetores")

        # 3. Validação e Atribuição dos Vetores
        if len(df_full) != len(vetores):
            logger.error(f"Incompatibilidade de tamanho! Parquet: {len(df_full)}, Pickle: {len(vetores)}")
            return False

        logger.info("Atribuindo vetores ao DataFrame")
        df_full['vector'] = list(vetores)
        logger.info(f"Total de {len(df_full)} registros prontos para indexação")

        # 4. Preparação da Coleção no Qdrant
        if client.collection_exists(collection_name=collection_name):
            logger.warning(f"Coleção '{collection_name}' já existe. Recriando...")
            client.delete_collection(collection_name=collection_name)

        vector_size = len(df_full['vector'].iloc[0])
        logger.info(f"Criando coleção '{collection_name}' com vetores de dimensão {vector_size}")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )

        # 5. Preparação dos Pontos para Upload
        points_to_upload = []
        failed_points = 0
        
        for _, row in tqdm(df_full.iterrows(), total=df_full.shape[0], desc="Preparando pontos"):
            try:
                payload = {new_key: row.get(original_key) for new_key, original_key in payload_columns.items()}

                # Adiciona a etiqueta de 'contexto' para os recursos
                if is_recurso:
                    instance = payload.get("instance")
                    if instance and instance != "CGU":
                        payload["context"] = "orgao_julgador"
                    elif instance == "CGU":
                        payload["context"] = "orgao_demandado"
                    else:
                        payload["context"] = "indefinido"

                points_to_upload.append(
                    models.PointStruct(id=int(row[id_column]), vector=row['vector'], payload=payload)
                )
            except Exception as e:
                logger.error(f"Erro ao processar linha {row.get(id_column, 'unknown')}: {e}")
                failed_points += 1
                continue
                
        if failed_points > 0:
            logger.warning(f"{failed_points} pontos falharam na preparação")

        # 6. Upload para o Qdrant em Lotes
        logger.info(f"Enviando {len(points_to_upload)} pontos para o Qdrant em lotes")
        BATCH_SIZE = 512
        failed_batches = 0

        for i in tqdm(range(0, len(points_to_upload), BATCH_SIZE), desc="Enviando lotes"):
            try:
                batch = points_to_upload[i:i + BATCH_SIZE]
                client.upsert(
                    collection_name=collection_name,
                    points=batch,
                    wait=True
                )
            except Exception as e:
                logger.error(f"Erro ao enviar lote {i//BATCH_SIZE + 1}: {e}")
                failed_batches += 1
                continue
        
        if failed_batches == 0:
            logger.info(f"✅ Indexação de {collection_name} concluída com sucesso!")
        else:
            logger.warning(f"Indexação concluída com {failed_batches} lotes falharam")
            
        return failed_batches == 0
        
    except Exception as e:
        logger.error(f"Erro crítico durante indexação: {e}")
        return False


def main():
    """Função principal para executar a indexação."""
    logger.info("Iniciando processo de indexação")
    
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=60)
        logger.info(f"Conectado ao Qdrant em {QDRANT_HOST}:{QDRANT_PORT}")
    except Exception as e:
        logger.error(f"Erro ao conectar com Qdrant: {e}")
        return False
    
    success = True

    # --- Indexar RECURSOS ---
    logger.info("=== INDEXANDO RECURSOS ===")
    recursos_success = index_from_precomputed(
        collection_name=QDRANT_RECURSOS_COLLECTION_NAME,
        parquet_path=RECURSOS_PARQUET_PATH,
        pickle_path=RECURSOS_PICKLE_PATH,
        id_column="IdRecurso",
        payload_columns={
            "description": "DescRecurso",
            "response": "RespostaRecurso",
            "decision": "TipoResposta",
            "instance": "Instancia"
        },
        client=client,
        is_recurso=True
    )
    
    if not recursos_success:
        logger.error("Falha na indexação de recursos")
        success = False

    # --- Indexar PEDIDOS ---
    logger.info("=== INDEXANDO PEDIDOS ===")
    pedidos_success = index_from_precomputed(
        collection_name=QDRANT_PEDIDOS_COLLECTION_NAME,
        parquet_path=PEDIDOS_PARQUET_PATH,
        pickle_path=PEDIDOS_PICKLE_PATH,
        id_column="IdPedido",
        payload_columns={
            "summary": "ResumoSolicitacao",
            "details": "DetalhamentoSolicitacao",
            "decision": "Decisao",
            "protocol": "ProtocoloPedido"
        },
        client=client
    )
    
    if not pedidos_success:
        logger.error("Falha na indexação de pedidos")
        success = False
    
    if success:
        logger.info("✅ Processo de indexação concluído com sucesso!")
    else:
        logger.error("❌ Processo de indexação concluído com erros")
        
    return success


if __name__ == "__main__":
    main()