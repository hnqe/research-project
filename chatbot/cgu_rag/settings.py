#settings.py
from pathlib import Path          # manipulação de caminhos de forma portátil
from dotenv import load_dotenv    # lê variáveis do arquivo .env
import os                         # acesso às variáveis de ambiente

load_dotenv()                     # procura e carrega o arquivo .env (se existir)

BASE_DIR   = Path(__file__).resolve().parent.parent   # raiz do projeto (pasta chat-cgu/)
DATA_DIR   = BASE_DIR / "data"                        # onde ficam parquet, .pkl etc.
VECTORS_DIR = DATA_DIR / "vetores"                    # subpasta específica p/ vetores
MODEL_NAME  = os.getenv("EMBEDDING_MODEL",            # modelo de embedding a usar
                        "intfloat/multilingual-e5-base")
DEVICE      = "cuda" if os.getenv("USE_CUDA", "false").lower() == "true" else "cpu"