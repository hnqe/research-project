#!/usr/bin/env python3
"""
Script de validação do setup completo do MVP CGU.
Executa verificações pré-deployment e pós-deployment.
"""

import sys
import logging
import argparse
import time
from pathlib import Path
from typing import Dict, List, Optional

# Adiciona o diretório app ao path
sys.path.append(str(Path(__file__).resolve().parent.parent / "app"))

try:
    from config import settings, setup_logging
    import requests
    import pandas as pd
except ImportError as e:
    print(f"❌ Erro ao importar dependências: {e}")
    sys.exit(1)

setup_logging()
logger = logging.getLogger(__name__)

class SetupValidator:
    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or "http://localhost:8000"
        self.results: List[Dict] = []
        self.failures = 0
        
    def test(self, name: str, func, **kwargs):
        """Executa um teste e registra o resultado."""
        try:
            start_time = time.time()
            success = func(**kwargs)
            duration = time.time() - start_time
            
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"{status} {name} ({duration:.2f}s)")
            
            if not success:
                self.failures += 1
                
            self.results.append({
                "name": name,
                "success": success,
                "duration": duration
            })
            
        except Exception as e:
            logger.error(f"💥 ERROR {name}: {e}")
            self.failures += 1
            self.results.append({
                "name": name,
                "success": False,
                "duration": 0,
                "error": str(e)
            })
    
    def validate_data_integrity(self) -> bool:
        """Valida a integridade dos dados."""
        try:
            from config import get_data_paths
            paths = get_data_paths()
            
            # Verifica recursos
            recursos_df = pd.read_parquet(paths["recursos_parquet"])
            required_columns = ["IdRecurso", "DescRecurso", "RespostaRecurso", "TipoResposta", "Instancia"]
            
            for col in required_columns:
                if col not in recursos_df.columns:
                    logger.error(f"Coluna faltando em recursos: {col}")
                    return False
            
            # Verifica se há dados
            if len(recursos_df) == 0:
                logger.error("Arquivo de recursos está vazio")
                return False
                
            logger.info(f"Recursos: {len(recursos_df)} registros válidos")
            
            # Verifica pedidos
            pedidos_df = pd.read_parquet(paths["pedidos_parquet"])
            required_columns = ["IdPedido", "ResumoSolicitacao", "DetalhamentoSolicitacao", "Decisao", "ProtocoloPedido"]
            
            for col in required_columns:
                if col not in pedidos_df.columns:
                    logger.error(f"Coluna faltando em pedidos: {col}")
                    return False
            
            if len(pedidos_df) == 0:
                logger.error("Arquivo de pedidos está vazio")
                return False
                
            logger.info(f"Pedidos: {len(pedidos_df)} registros válidos")
            return True
            
        except Exception as e:
            logger.error(f"Erro na validação de dados: {e}")
            return False
    
    def test_api_health(self) -> bool:
        """Testa o endpoint de health da API."""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    logger.info(f"API saudável: {data.get('recursos_count', 0)} recursos")
                    return True
            
            logger.error(f"Health check falhou: {response.status_code}")
            return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao conectar com API: {e}")
            return False
    
    def test_api_root(self) -> bool:
        """Testa o endpoint raiz da API."""
        try:
            response = requests.get(f"{self.api_url}/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "MVP CGU" in data["message"]:
                    return True
            
            logger.error(f"Endpoint raiz falhou: {response.status_code}")
            return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro no endpoint raiz: {e}")
            return False
    
    def test_analyze_endpoint(self) -> bool:
        """Testa o endpoint principal de análise."""
        try:
            test_data = {
                "text": "Solicito acesso aos contratos firmados pela CGU no exercício de 2023, incluindo valores e fornecedores.",
                "top_k": 3,
                "min_score": 0.5
            }
            
            response = requests.post(
                f"{self.api_url}/analyze-appeal",
                json=test_data,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["likely_decision", "decision_stats", "similar_appeals"]
                
                for field in required_fields:
                    if field not in data:
                        logger.error(f"Campo faltando na resposta: {field}")
                        return False
                
                appeals_count = len(data.get("similar_appeals", []))
                logger.info(f"Análise funcionando: {appeals_count} recursos similares encontrados")
                return True
            else:
                logger.error(f"Endpoint de análise falhou: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro no teste de análise: {e}")
            return False
    
    def test_instances_endpoint(self) -> bool:
        """Testa o endpoint de instâncias."""
        try:
            response = requests.get(f"{self.api_url}/instances", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "instances" in data and len(data["instances"]) > 0:
                    logger.info(f"Instâncias disponíveis: {len(data['instances'])}")
                    return True
            
            logger.error(f"Endpoint de instâncias falhou: {response.status_code}")
            return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro no endpoint de instâncias: {e}")
            return False
    
    def test_groq_functionality(self) -> bool:
        """Testa funcionalidade do Groq (se configurado)."""
        try:
            response = requests.get(f"{self.api_url}/minuta-status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("available"):
                    # Testa geração de minuta
                    test_data = {
                        "text": "Solicito acesso aos dados de contratos públicos da CGU.",
                        "top_k": 2,
                        "min_score": 0.6
                    }
                    
                    response = requests.post(
                        f"{self.api_url}/analyze-appeal-with-draft",
                        json=test_data,
                        timeout=45
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if "draft_response" in result and len(result["draft_response"]) > 50:
                            logger.info("Geração de minutas funcionando")
                            return True
                        else:
                            logger.error("Minuta gerada é muito curta ou vazia")
                            return False
                    else:
                        logger.error(f"Erro na geração de minuta: {response.status_code}")
                        return False
                else:
                    logger.info("Groq não configurado (funcionalidade opcional)")
                    return True
            
            return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro no teste do Groq: {e}")
            return False
    
    def test_api_docs(self) -> bool:
        """Testa se a documentação da API está acessível."""
        try:
            response = requests.get(f"{self.api_url}/docs", timeout=5)
            return response.status_code == 200
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao acessar docs: {e}")
            return False
    
    def run_pre_deployment_tests(self):
        """Executa testes pré-deployment."""
        logger.info("🔍 Executando testes pré-deployment...")
        
        self.test("Integridade dos dados", self.validate_data_integrity)
        
        print(f"\n📋 Pré-deployment: {len(self.results) - self.failures}/{len(self.results)} testes passaram")
        return self.failures == 0
    
    def run_post_deployment_tests(self):
        """Executa testes pós-deployment."""
        logger.info("🚀 Executando testes pós-deployment...")
        
        self.test("Health check da API", self.test_api_health)
        self.test("Endpoint raiz", self.test_api_root)
        self.test("Documentação da API", self.test_api_docs)
        self.test("Endpoint de análise", self.test_analyze_endpoint)
        self.test("Endpoint de instâncias", self.test_instances_endpoint)
        self.test("Funcionalidade Groq", self.test_groq_functionality)
        
        print(f"\n📋 Pós-deployment: {len(self.results) - self.failures}/{len(self.results)} testes passaram")
        return self.failures == 0
    
    def run_load_test(self, requests_count: int = 10):
        """Executa um teste simples de carga."""
        logger.info(f"⚡ Executando teste de carga ({requests_count} requisições)...")
        
        test_data = {
            "text": "Teste de carga - solicito informações sobre contratos.",
            "top_k": 3,
            "min_score": 0.5
        }
        
        successful_requests = 0
        total_time = 0
        
        for i in range(requests_count):
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.api_url}/analyze-appeal",
                    json=test_data,
                    timeout=30
                )
                
                duration = time.time() - start_time
                total_time += duration
                
                if response.status_code == 200:
                    successful_requests += 1
                    
                if i % 5 == 0:
                    logger.info(f"Progresso: {i+1}/{requests_count}")
                    
            except Exception as e:
                logger.error(f"Erro na requisição {i+1}: {e}")
        
        avg_response_time = total_time / requests_count if requests_count > 0 else 0
        success_rate = (successful_requests / requests_count) * 100
        
        logger.info(f"Teste de carga completo:")
        logger.info(f"  - Taxa de sucesso: {success_rate:.1f}%")
        logger.info(f"  - Tempo médio de resposta: {avg_response_time:.2f}s")
        logger.info(f"  - Requisições por segundo: {1/avg_response_time:.2f}" if avg_response_time > 0 else "  - RPS: N/A")
        
        return success_rate >= 90  # 90% success rate threshold
    
    def print_summary(self):
        """Imprime resumo dos resultados."""
        total_tests = len(self.results)
        passed = total_tests - self.failures
        
        print("\n" + "="*60)
        print("📊 RESUMO DA VALIDAÇÃO")
        print("="*60)
        print(f"✅ Testes passaram: {passed}")
        print(f"❌ Testes falharam: {self.failures}")
        print(f"📈 Taxa de sucesso: {(passed/total_tests)*100:.1f}%" if total_tests > 0 else "📈 Taxa de sucesso: N/A")
        
        if self.failures == 0:
            print("\n🎉 Todos os testes passaram! Sistema validado.")
        else:
            print(f"\n⚠️ {self.failures} testes falharam. Verifique os problemas acima.")

def main():
    parser = argparse.ArgumentParser(description="Validador do setup do MVP CGU")
    parser.add_argument("--mode", choices=["pre", "post", "all"], default="all",
                       help="Modo de validação (pre=pré-deployment, post=pós-deployment, all=ambos)")
    parser.add_argument("--api-url", default="http://localhost:8000",
                       help="URL da API para testes pós-deployment")
    parser.add_argument("--load-test", action="store_true",
                       help="Executa teste de carga")
    parser.add_argument("--load-requests", type=int, default=10,
                       help="Número de requisições para teste de carga")
    
    args = parser.parse_args()
    
    print("🔬 MVP CGU - Validador de Setup")
    print(f"🌐 API URL: {args.api_url}")
    print()
    
    validator = SetupValidator(api_url=args.api_url)
    success = True
    
    if args.mode in ["pre", "all"]:
        success &= validator.run_pre_deployment_tests()
    
    if args.mode in ["post", "all"]:
        success &= validator.run_post_deployment_tests()
    
    if args.load_test and success:
        validator.test("Teste de carga", validator.run_load_test, requests_count=args.load_requests)
    
    validator.print_summary()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()