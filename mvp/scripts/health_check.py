#!/usr/bin/env python3
"""
Script de verificação de saúde do sistema MVP CGU.
Verifica conexões, dependências e estado geral da aplicação.
"""

import sys
import logging
import time
from pathlib import Path

# Adiciona o diretório app ao path para importar módulos
sys.path.append(str(Path(__file__).resolve().parent.parent / "app"))

try:
    from config import settings, setup_logging, validate_environment, get_data_paths
    from qdrant_client import QdrantClient
    from sentence_transformers import SentenceTransformer
    import pandas as pd
    import pickle
    import requests
except ImportError as e:
    print(f"❌ Erro ao importar dependências: {e}")
    sys.exit(1)

# Configura logging
setup_logging()
logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self):
        self.results = []
        self.critical_failures = 0
        self.warnings = 0
        
    def check(self, name: str, func, critical: bool = True):
        """Executa uma verificação e registra o resultado."""
        try:
            start_time = time.time()
            result = func()
            duration = time.time() - start_time
            
            if result:
                status = "✅ PASS"
                logger.info(f"{status} {name} ({duration:.2f}s)")
            else:
                status = "❌ FAIL" if critical else "⚠️ WARN"
                logger.error(f"{status} {name}")
                if critical:
                    self.critical_failures += 1
                else:
                    self.warnings += 1
            
            self.results.append({
                "name": name,
                "status": "PASS" if result else ("FAIL" if critical else "WARN"),
                "duration": duration,
                "critical": critical
            })
            
        except Exception as e:
            status = "💥 ERROR"
            logger.error(f"{status} {name}: {e}")
            if critical:
                self.critical_failures += 1
            else:
                self.warnings += 1
                
            self.results.append({
                "name": name,
                "status": "ERROR",
                "duration": 0,
                "critical": critical,
                "error": str(e)
            })
    
    def check_environment_variables(self) -> bool:
        """Verifica variáveis de ambiente essenciais."""
        try:
            # Testa a configuração
            _ = settings.model_name
            _ = settings.qdrant_host
            _ = settings.qdrant_port
            return True
        except Exception as e:
            logger.error(f"Erro nas configurações: {e}")
            return False
    
    def check_data_files(self) -> bool:
        """Verifica se os arquivos de dados existem."""
        paths = get_data_paths()
        
        required_files = [
            paths["recursos_parquet"],
            paths["pedidos_parquet"],
        ]
        
        all_exist = True
        for file_path in required_files:
            if not file_path.exists():
                logger.error(f"Arquivo não encontrado: {file_path}")
                all_exist = False
            else:
                # Testa se pode ler o arquivo
                try:
                    df = pd.read_parquet(file_path, nrows=1)
                    logger.debug(f"Arquivo válido: {file_path}")
                except Exception as e:
                    logger.error(f"Erro ao ler {file_path}: {e}")
                    all_exist = False
        
        return all_exist
    
    def check_vector_files(self) -> bool:
        """Verifica se os arquivos de vetores existem."""
        paths = get_data_paths()
        vetores_dir = paths["vetores_dir"]
        
        if not vetores_dir.exists():
            logger.error(f"Diretório de vetores não encontrado: {vetores_dir}")
            return False
        
        # Procura por arquivos .pkl
        pickle_files = list(vetores_dir.glob("*.pkl"))
        
        if len(pickle_files) < 2:
            logger.error(f"Poucos arquivos de vetores encontrados: {len(pickle_files)}")
            return False
        
        # Testa um arquivo
        for pkl_file in pickle_files[:1]:
            try:
                with open(pkl_file, 'rb') as f:
                    data = pickle.load(f)
                    if 'embeddings' not in data:
                        logger.error(f"Arquivo {pkl_file} não contém 'embeddings'")
                        return False
                    logger.debug(f"Arquivo de vetores válido: {pkl_file}")
            except Exception as e:
                logger.error(f"Erro ao ler {pkl_file}: {e}")
                return False
        
        return True
    
    def check_qdrant_connection(self) -> bool:
        """Verifica conexão com Qdrant."""
        try:
            client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                timeout=10
            )
            
            # Testa conexão básica
            collections = client.get_collections()
            logger.debug(f"Qdrant conectado. Coleções: {len(collections.collections)}")
            
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar com Qdrant: {e}")
            return False
    
    def check_qdrant_collections(self) -> bool:
        """Verifica se as coleções necessárias existem no Qdrant."""
        try:
            client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                timeout=10
            )
            
            required_collections = [
                settings.qdrant_recursos_collection,
                settings.qdrant_pedidos_collection
            ]
            
            for collection_name in required_collections:
                if not client.collection_exists(collection_name):
                    logger.error(f"Coleção não existe: {collection_name}")
                    return False
                    
                info = client.get_collection(collection_name)
                if info.points_count == 0:
                    logger.warning(f"Coleção {collection_name} está vazia")
                else:
                    logger.debug(f"Coleção {collection_name}: {info.points_count} pontos")
            
            return True
        except Exception as e:
            logger.error(f"Erro ao verificar coleções: {e}")
            return False
    
    def check_embedding_model(self) -> bool:
        """Verifica se o modelo de embedding pode ser carregado."""
        try:
            # Tenta carregar o modelo (pode ser lento na primeira vez)
            model = SentenceTransformer(settings.model_name)
            
            # Testa uma embedding simples
            test_text = "Este é um teste de embedding."
            embedding = model.encode(test_text)
            
            if len(embedding) > 0:
                logger.debug(f"Modelo carregado. Dimensão do embedding: {len(embedding)}")
                return True
            else:
                logger.error("Embedding vazio gerado")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao carregar modelo de embedding: {e}")
            return False
    
    def check_groq_api(self) -> bool:
        """Verifica se a API do Groq está acessível."""
        if not settings.groq_api_key:
            logger.info("API Groq não configurada (opcional)")
            return True
        
        try:
            from groq import Groq
            client = Groq(api_key=settings.groq_api_key)
            
            # Teste simples
            response = client.chat.completions.create(
                model=settings.groq_model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            
            if response.choices:
                logger.debug("API Groq funcionando")
                return True
            else:
                logger.error("Resposta vazia da API Groq")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao testar API Groq: {e}")
            return False
    
    def check_fastapi_dependencies(self) -> bool:
        """Verifica se as dependências do FastAPI estão disponíveis."""
        try:
            import fastapi
            import uvicorn
            import pydantic
            logger.debug("Dependências do FastAPI OK")
            return True
        except ImportError as e:
            logger.error(f"Dependência faltando: {e}")
            return False
    
    def run_all_checks(self):
        """Executa todas as verificações."""
        logger.info("🔍 Iniciando verificações de saúde do sistema...")
        
        # Verificações críticas
        self.check("Variáveis de ambiente", self.check_environment_variables, critical=True)
        self.check("Dependências FastAPI", self.check_fastapi_dependencies, critical=True)
        self.check("Arquivos de dados", self.check_data_files, critical=True)
        self.check("Conexão Qdrant", self.check_qdrant_connection, critical=True)
        self.check("Coleções Qdrant", self.check_qdrant_collections, critical=True)
        
        # Verificações importantes mas não críticas
        self.check("Arquivos de vetores", self.check_vector_files, critical=False)
        self.check("Modelo de embedding", self.check_embedding_model, critical=False)
        self.check("API Groq", self.check_groq_api, critical=False)
        
        # Relatório final
        self.print_summary()
        
        return self.critical_failures == 0
    
    def print_summary(self):
        """Imprime um resumo dos resultados."""
        total_checks = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        errors = sum(1 for r in self.results if r["status"] == "ERROR")
        warnings = sum(1 for r in self.results if r["status"] == "WARN")
        
        print("\n" + "="*50)
        print("📋 RESUMO DAS VERIFICAÇÕES")
        print("="*50)
        print(f"✅ Passou: {passed}")
        print(f"❌ Falhou: {failed}")
        print(f"💥 Erro: {errors}")
        print(f"⚠️ Aviso: {warnings}")
        print(f"📊 Total: {total_checks}")
        
        if self.critical_failures == 0:
            print("\n🎉 Sistema está saudável e pronto para uso!")
        else:
            print(f"\n⚠️ {self.critical_failures} falhas críticas encontradas!")
            print("🔧 Corrija os problemas antes de executar a aplicação.")
        
        # Detalhes dos problemas
        problems = [r for r in self.results if r["status"] in ["FAIL", "ERROR"]]
        if problems:
            print("\n🔍 PROBLEMAS ENCONTRADOS:")
            for problem in problems:
                status_icon = "💥" if problem["status"] == "ERROR" else "❌"
                print(f"{status_icon} {problem['name']}")
                if "error" in problem:
                    print(f"   └─ {problem['error']}")

def main():
    """Função principal do health check."""
    print("🏥 MVP CGU - Health Check")
    print(f"📍 Verificando sistema em: {Path.cwd()}")
    print()
    
    checker = HealthChecker()
    success = checker.run_all_checks()
    
    # Exit code baseado no resultado
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()