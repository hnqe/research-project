# build_vectors.py
"""
Recria (ou cria) embeddings e o índice FAISS a partir dos arquivos Parquet.

Este script pode operar em dois modos:
1.  GERAÇÃO COMPLETA (USE_PRECOMPUTED_EMBEDDINGS = False):
    - Ideal para rodar em um ambiente com GPU (como o Google Colab).
    - Gera os embeddings do zero e salva um arquivo .pkl.
    - Constrói o índice FAISS a partir dos embeddings recém-gerados.

2.  CONSTRUÇÃO A PARTIR DE PRÉ-CALCULADOS (USE_PRECOMPUTED_EMBEDDINGS = True):
    - Ideal para rodar em uma máquina local sem GPU.
    - Pula a geração de embeddings.
    - Carrega um arquivo .pkl de embeddings (gerado no Colab).
    - Constrói o índice FAISS rapidamente a partir desses embeddings.
"""

import pandas as pd

from cgu_rag.pipeline import CGURecommendationPipeline
from cgu_rag.settings import DATA_DIR, VECTORS_DIR, MODEL_NAME, DEVICE

# Mude para True se você já gerou os .pkl no Colab e quer apenas construir
# o índice .faiss localmente (muito mais rápido e não precisa de GPU).
USE_PRECOMPUTED_EMBEDDINGS = False

BATCH_SIZE = 128
RECRIAR_RECURSOS = True

def ensure_sentence(df: pd.DataFrame, is_pedidos=True) -> pd.DataFrame:
    """Garante que a coluna 'sentence' exista."""
    if "sentence" not in df.columns:
        if is_pedidos:
            df["sentence"] = (df["ResumoSolicitacao"].fillna("") + " <SEP> " + df["DetalhamentoSolicitacao"].fillna(""))
        else:
            df["sentence"] = (df["TipoRecurso"].fillna("") + " <SEP> " + df["DescRecurso"].fillna(""))
    return df


def main() -> None:
    VECTORS_DIR.mkdir(parents=True, exist_ok=True)
    pipe = CGURecommendationPipeline(MODEL_NAME, DEVICE)

    # --- PROCESSAMENTO DE PEDIDOS ---
    print("\n--- INICIANDO PROCESSAMENTO DE PEDIDOS ---")
    df_ped = pd.read_parquet(DATA_DIR / "dt_pedidos.parquet")
    df_ped = ensure_sentence(df_ped, is_pedidos=True)
    pedidos_pkl_path = VECTORS_DIR / "pedidos.pkl"

    if not USE_PRECOMPUTED_EMBEDDINGS:
        print(f"Gerando embeddings para {len(df_ped)} pedidos (BATCH_SIZE={BATCH_SIZE})...")
        pipe.generate_and_save_embeddings(
            df=df_ped,
            id_column="ProtocoloPedido",
            output_path=pedidos_pkl_path,
            batch_size=BATCH_SIZE,
        )

    print(f"Carregando embeddings de '{pedidos_pkl_path}' para construir o índice FAISS...")
    ids_ped, emb_ped, _ = pipe.load_embeddings_from_pickle(pedidos_pkl_path)
    if ids_ped:
        pipe.build_vectorstore_from_embeddings(
            ids=ids_ped,
            embeddings=emb_ped,
            store_type='pedidos',
            persist_directory=VECTORS_DIR
        )
        print("✅ Índice 'pedidos.faiss' construído com sucesso!\n")
    else:
        print(f"❌ Falha ao carregar embeddings de '{pedidos_pkl_path}'. Pulando construção do índice.")

    # --- PROCESSAMENTO DE RECURSOS (opcional) ---
    if RECRIAR_RECURSOS:
        print("\n--- INICIANDO PROCESSAMENTO DE RECURSOS ---")
        df_rec = pd.read_parquet(DATA_DIR / "dt_recursos.parquet")
        df_rec = ensure_sentence(df_rec, is_pedidos=False)
        recursos_pkl_path = VECTORS_DIR / "recursos.pkl"

        if not USE_PRECOMPUTED_EMBEDDINGS:
            print(f"Gerando embeddings para {len(df_rec)} recursos (BATCH_SIZE={BATCH_SIZE})...")
            pipe.generate_and_save_embeddings(
                df=df_rec,
                id_column="IdRecurso",
                output_path=recursos_pkl_path,
                batch_size=BATCH_SIZE,
            )

        print(f"Carregando embeddings de '{recursos_pkl_path}' para construir o índice FAISS...")
        ids_rec, emb_rec, _ = pipe.load_embeddings_from_pickle(recursos_pkl_path)
        if ids_rec:
            pipe.build_vectorstore_from_embeddings(
                ids=ids_rec,
                embeddings=emb_rec,
                store_type='recursos',
                persist_directory=VECTORS_DIR
            )
            print("✅ Índice 'recursos.faiss' construído com sucesso!\n")
        else:
            print(f"❌ Falha ao carregar embeddings de '{recursos_pkl_path}'. Pulando construção do índice.")
    else:
        print("\n• Geração de RECURSOS pulada (RECRIAR_RECURSOS=False)")


if __name__ == "__main__":
    main()