# index_from_docker.py
import os
import pickle
import logging
import pandas as pd
from qdrant_client import QdrantClient, models
from tqdm import tqdm
import docker
import tempfile
import shutil

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Configurações ---
CONTAINER_NAME = "mvp-data"
DOCKER_DATA_PATH = "/data"

# Configs do Qdrant (com suporte a variáveis de ambiente)
QDRANT_HOST = os.getenv("QDRANT_HOST", "127.0.0.1")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_RECURSOS_COLLECTION_NAME = "recursos_cgu_v1"
QDRANT_PEDIDOS_COLLECTION_NAME = "pedidos_cgu_v1"


def copy_data_from_container():
    """Copia dados do container Docker para diretório temporário local."""
    logger.info(f"📦 Copiando dados do container {CONTAINER_NAME}")
    
    # Criar diretório temporário
    temp_dir = tempfile.mkdtemp(prefix="mvp_data_")
    logger.info(f"📁 Diretório temporário: {temp_dir}")
    
    try:
        client = docker.from_env()
        container = client.containers.get(CONTAINER_NAME)
        
        # Verificar se container está rodando
        if container.status != 'running':
            logger.error(f"❌ Container {CONTAINER_NAME} não está rodando!")
            return None
            
        # Copiar dados do container
        logger.info("📋 Copiando arquivos parquet...")
        
        # Copiar dt_recursos.parquet
        bits, _ = container.get_archive(f"{DOCKER_DATA_PATH}/dt_recursos.parquet")
        with open(os.path.join(temp_dir, "dt_recursos.tar"), "wb") as f:
            for chunk in bits:
                f.write(chunk)
        
        # Copiar dt_pedidos.parquet  
        bits, _ = container.get_archive(f"{DOCKER_DATA_PATH}/dt_pedidos.parquet")
        with open(os.path.join(temp_dir, "dt_pedidos.tar"), "wb") as f:
            for chunk in bits:
                f.write(chunk)
                
        # Copiar diretório vetores
        bits, _ = container.get_archive(f"{DOCKER_DATA_PATH}/vetores")
        with open(os.path.join(temp_dir, "vetores.tar"), "wb") as f:
            for chunk in bits:
                f.write(chunk)
        
        # Extrair arquivos tar
        import tarfile
        
        for tar_file in ["dt_recursos.tar", "dt_pedidos.tar", "vetores.tar"]:
            tar_path = os.path.join(temp_dir, tar_file)
            with tarfile.open(tar_path, "r") as tar:
                tar.extractall(temp_dir)
            os.remove(tar_path)
        
        logger.info("✅ Dados copiados com sucesso!")
        return temp_dir
        
    except docker.errors.NotFound:
        logger.error(f"❌ Container {CONTAINER_NAME} não encontrado!")
        return None
    except Exception as e:
        logger.error(f"❌ Erro ao copiar dados: {e}")
        return None


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
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao validar arquivos: {e}")
        return False


def load_data_and_vectors(parquet_path: str, pickle_path: str):
    """Carrega dados do parquet e vetores do pickle."""
    logger.info(f"Carregando metadados de {parquet_path}")
    df = pd.read_parquet(parquet_path)
    logger.info(f"Carregados {len(df)} registros do Parquet")
    
    logger.info(f"Carregando vetores pré-calculados de {pickle_path}")
    with open(pickle_path, 'rb') as f:
        data = pickle.load(f)
    
    embeddings = data['embeddings']
    logger.info(f"Carregados {len(embeddings)} vetores")
    
    # Atribuir vetores ao DataFrame
    logger.info("Atribuindo vetores ao DataFrame")
    # Converter array 2D para lista de arrays 1D
    if len(embeddings.shape) == 2:
        df['embedding'] = [embeddings[i] for i in range(min(len(df), len(embeddings)))]
    else:
        df['embedding'] = embeddings[:len(df)]
    
    # Filtrar apenas registros com embeddings válidos
    df = df.dropna(subset=['embedding'])
    logger.info(f"Total de {len(df)} registros prontos para indexação")
    
    return df


def create_collection(client: QdrantClient, collection_name: str, vector_size: int = 768):
    """Cria ou recria uma coleção no Qdrant."""
    try:
        if client.collection_exists(collection_name):
            logger.info(f"Removendo coleção existente '{collection_name}'")
            client.delete_collection(collection_name)
        
        logger.info(f"Criando coleção '{collection_name}' com vetores de dimensão {vector_size}")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE
            )
        )
        
    except Exception as e:
        logger.error(f"Erro ao criar coleção {collection_name}: {e}")
        raise


def batch_upsert(client: QdrantClient, collection_name: str, df: pd.DataFrame, batch_size: int = 500):
    """Insere dados em lotes no Qdrant com otimizações."""
    total_records = len(df)
    logger.info(f"Inserindo {total_records} registros em lotes de {batch_size}")
    
    # Processar em chunks maiores para reduzir overhead
    chunk_size = 10000
    total_chunks = (total_records + chunk_size - 1) // chunk_size
    
    processed = 0
    
    for chunk_idx in range(total_chunks):
        start_idx = chunk_idx * chunk_size
        end_idx = min((chunk_idx + 1) * chunk_size, total_records)
        
        chunk_df = df.iloc[start_idx:end_idx]
        logger.info(f"📦 Processando chunk {chunk_idx + 1}/{total_chunks} ({len(chunk_df)} registros)")
        
        # Preparar pontos para este chunk
        points = []
        
        for idx, row in chunk_df.iterrows():
            # Preparar payload (metadados) - mais eficiente
            payload = {}
            for col in chunk_df.columns:
                if col != 'embedding':
                    value = row[col]
                    # Converter valores NaN para None
                    if pd.isna(value):
                        payload[col] = None
                    else:
                        payload[col] = value
            
            # Criar ponto
            point = models.PointStruct(
                id=int(idx),
                vector=row['embedding'].tolist(),
                payload=payload
            )
            points.append(point)
            
            # Inserir em lotes menores
            if len(points) >= batch_size:
                try:
                    client.upsert(
                        collection_name=collection_name,
                        points=points,
                        wait=False  # Não esperar confirmação para ser mais rápido
                    )
                    processed += len(points)
                    points = []
                except Exception as e:
                    logger.warning(f"⚠️ Erro no batch, tentando novamente: {e}")
                    # Tentar com batch menor se der erro
                    for point in points:
                        try:
                            client.upsert(collection_name=collection_name, points=[point], wait=False)
                            processed += 1
                        except Exception as e2:
                            logger.error(f"❌ Erro no ponto individual: {e2}")
                    points = []
        
        # Inserir últimos pontos do chunk
        if points:
            try:
                client.upsert(
                    collection_name=collection_name,
                    points=points,
                    wait=False
                )
                processed += len(points)
            except Exception as e:
                logger.warning(f"⚠️ Erro no último batch: {e}")
                for point in points:
                    try:
                        client.upsert(collection_name=collection_name, points=[point], wait=False)
                        processed += 1
                    except Exception as e2:
                        logger.error(f"❌ Erro no ponto individual: {e2}")
        
        logger.info(f"✅ Chunk {chunk_idx + 1} processado. Total: {processed}/{total_records}")
    
    # Aguardar finalização da indexação
    logger.info("⏳ Aguardando finalização da indexação...")
    import time
    time.sleep(10)  # Dar tempo para o Qdrant processar
    
    logger.info(f"✅ {processed} pontos inseridos na coleção '{collection_name}'")


def index_collection(client: QdrantClient, collection_name: str, parquet_path: str, pickle_path: str):
    """Indexa uma coleção específica."""
    logger.info(f"Iniciando indexação para: {collection_name}")
    
    # Validar arquivos
    if not validate_files(parquet_path, pickle_path):
        logger.error("Falha na validação dos arquivos")
        return False
    
    # Carregar dados
    try:
        df = load_data_and_vectors(parquet_path, pickle_path)
    except Exception as e:
        logger.error(f"Erro ao carregar dados: {e}")
        return False
    
    # Criar coleção
    try:
        create_collection(client, collection_name)
    except Exception as e:
        logger.error(f"Erro ao criar coleção: {e}")
        return False
    
    # Inserir dados
    try:
        batch_upsert(client, collection_name, df)
        return True
    except Exception as e:
        logger.error(f"Erro ao inserir dados: {e}")
        return False


def main():
    """Função principal."""
    logger.info("🚀 Iniciando processo de indexação a partir do container Docker")
    
    # Copiar dados do container
    temp_dir = copy_data_from_container()
    if not temp_dir:
        logger.error("❌ Falha ao copiar dados do container")
        return
    
    try:
        # Conectar ao Qdrant
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        logger.info(f"Conectado ao Qdrant em {QDRANT_HOST}:{QDRANT_PORT}")
        
        # Definir caminhos dos arquivos
        recursos_parquet = os.path.join(temp_dir, "dt_recursos.parquet")
        pedidos_parquet = os.path.join(temp_dir, "dt_pedidos.parquet")
        
        nome_base_arquivo = "intfloat_multilingual-e5-base_ft_False"
        recursos_pickle = os.path.join(temp_dir, "vetores", f"{nome_base_arquivo}_vetores_recursos_2015_2023.pkl")
        pedidos_pickle = os.path.join(temp_dir, "vetores", f"{nome_base_arquivo}_vetores_pedidos_2015_2023.pkl")
        
        # Indexar recursos
        logger.info("=== INDEXANDO RECURSOS ===")
        success_recursos = index_collection(
            client, 
            QDRANT_RECURSOS_COLLECTION_NAME, 
            recursos_parquet, 
            recursos_pickle
        )
        
        if success_recursos:
            logger.info("✅ Indexação de recursos concluída")
        else:
            logger.error("❌ Falha na indexação de recursos")
        
        # Indexar pedidos
        logger.info("=== INDEXANDO PEDIDOS ===")
        success_pedidos = index_collection(
            client, 
            QDRANT_PEDIDOS_COLLECTION_NAME, 
            pedidos_parquet, 
            pedidos_pickle
        )
        
        if success_pedidos:
            logger.info("✅ Indexação de pedidos concluída")
        else:
            logger.error("❌ Falha na indexação de pedidos")
        
        # Resultado final
        if success_recursos and success_pedidos:
            logger.info("🎉 Processo de indexação concluído com sucesso!")
        else:
            logger.error("❌ Processo de indexação concluído com erros")
            
    finally:
        # Limpar diretório temporário
        logger.info(f"🧹 Limpando diretório temporário: {temp_dir}")
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()