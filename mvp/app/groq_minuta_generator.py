# groq_minuta_generator.py
import os
import time
from typing import List, Dict, Optional, Any

from groq import Groq


class GroqMinutaGenerator:
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa o gerador com a API key do Groq

        API Key gratuita: https://console.groq.com/keys
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY não encontrada. Defina a variável de ambiente ou passe como parâmetro.")

        self.client = Groq(api_key=self.api_key)
        # Modelo recomendado: rápido e de qualidade
        self.model = "llama3-70b-8192"
        
        # Rate limiting
        self.max_requests_per_minute = 30
        self.request_timestamps = []

    def format_similar_cases(self, similar_cases: List[Dict]) -> str:
        """Formata casos similares para o prompt"""
        if not similar_cases:
            return "Nenhum precedente similar encontrado."

        formatted = ""
        for i, case in enumerate(similar_cases[:3], 1):  # Top 3 casos
            formatted += f"""
        PRECEDENTE {i} (Score: {case.get('score', 0):.2f}):
        - ID: {case.get('id')}
        - Recurso: "{case.get('description', '')[:300]}..."
        - Decisão Final: {case.get('decision')}
        - Instância: {case.get('instance')}
        - Resposta da CGU: "{case.get('response', '')[:400]}..."
        
        """
        return formatted

    def format_decision_stats(self, decision_stats: Dict) -> str:
        """Formata estatísticas de decisão"""
        if not decision_stats:
            return "Nenhuma estatística disponível."

        stats_text = "📊 ESTATÍSTICAS DE DECISÕES SIMILARES:\n"
        total_cases = sum(data['count'] for data in decision_stats.values())

        for decision, data in sorted(decision_stats.items(),
                                     key=lambda x: x[1]['percentage'], reverse=True):
            stats_text += f"• {decision}: {data['count']} casos ({data['percentage']}%)\n"

        stats_text += f"\nTotal de precedentes analisados: {total_cases} casos"
        return stats_text

    def generate_minuta(self, appeal_text: str, similar_cases: List[Dict],
                        prediction: str, decision_stats: Dict) -> Dict[str, str]:
        """
        Gera minuta oficial usando Groq

        Returns:
            Dict com 'minuta' e 'metadata'
        """

        # Preparar dados contextuais
        similar_cases_text = self.format_similar_cases(similar_cases)
        stats_text = self.format_decision_stats(decision_stats)

        # Prompt otimizado para qualidade jurídica
        system_prompt = """Você é um servidor sênior da CGU (Controladoria-Geral da União) com 15 anos de experiência em Lei de Acesso à Informação (LAI). 

        Sua expertise inclui:
        - Lei 12.527/2011 (LAI)
        - Decreto 7.724/2012
        - Jurisprudência consolidada da CGU
        - Redação técnica oficial
        
        RESPONSABILIDADE: Gerar minutas de alta qualidade técnica que servirão como base para decisões oficiais da CGU."""

        user_prompt = f"""TAREFA: Gere uma minuta de resposta oficial para o recurso LAI apresentado.

        📋 RECURSO INTERPOSTO:
        {appeal_text}
        
        {similar_cases_text}
        
        {stats_text}
        
        🤖 PREDIÇÃO IA: {prediction}
        
        📝 INSTRUÇÕES PARA A MINUTA:
        
        1. **ESTRUTURA OBRIGATÓRIA:**
           - Cabeçalho "DECISÃO"
           - Seção "CONSIDERANDO" (fundamentação)
           - Seção "DECIDO" (dispositivo)
           - Identificação de prazos recursais
        
        2. **FUNDAMENTAÇÃO JURÍDICA:**
           - Cite artigos específicos da Lei 12.527/2011
           - Referencie o Decreto 7.724/2012
           - Use precedentes similares quando relevante
           - Mantenha consistência com a jurisprudência
        
        3. **QUALIDADE TÉCNICA:**
           - Linguagem formal e jurídica apropriada
           - Argumentação clara e objetiva
           - Conclusão coerente com os precedentes
           - Praticidade para o servidor revisar
        
        4. **DECISÃO BASEADA EM DADOS:**
           - Considere as estatísticas apresentadas
           - Justifique com base nos precedentes
           - Se divergir da predição, explique os motivos
        
        IMPORTANTE: Esta minuta será revisada por um servidor antes da publicação oficial. Foque na qualidade técnica e consistência jurídica.
        
        MINUTA:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Baixa criatividade para consistência
                max_tokens=1500,
                top_p=0.9
            )

            minuta = response.choices[0].message.content.strip()

            return {
                "minuta": minuta,
                "metadata": {
                    "model_used": self.model,
                    "tokens_used": response.usage.total_tokens,
                    "generation_time": "~2 segundos",
                    "similar_cases_count": len(similar_cases),
                    "prediction_confidence": prediction
                }
            }

        except Exception as e:
            return {
                "minuta": self.generate_fallback_minuta(appeal_text, prediction),
                "metadata": {
                    "error": str(e),
                    "fallback_used": True
                }
            }

    def generate_fallback_minuta(self, appeal_text: str, prediction: str) -> str:
        """Minuta básica caso a API falhe"""
        return f"""DECISÃO

        Em análise ao recurso interposto, com fundamento no art. 21 do Decreto nº 7.724/2012, que regulamenta a Lei nº 12.527/2011 (Lei de Acesso à Informação), apresento a seguinte análise:
        
        CONSIDERANDO o recurso apresentado pelo cidadão, que solicita revisão da decisão de primeira instância;
        
        CONSIDERANDO que a análise automatizada baseada em precedentes similares indica: {prediction};
        
        CONSIDERANDO as disposições da Lei nº 12.527/2011, especialmente os artigos 3º, 5º e 7º, que estabelecem o direito fundamental de acesso à informação;
        
        CONSIDERANDO o Decreto nº 7.724/2012, que regulamenta os procedimentos para garantia do direito de acesso à informação;
        
        [DECISÃO ESPECÍFICA A SER COMPLETADA PELO SERVIDOR RESPONSÁVEL COM BASE NA ANÁLISE DETALHADA DO CASO]
        
        Prazo para recurso à instância superior: 10 (dez) dias, conforme art. 21 do Decreto nº 7.724/2012.
        
        [NOME DO SERVIDOR RESPONSÁVEL]
        [CARGO/FUNÇÃO]
        [DATA]
        
        ---
        OBSERVAÇÃO TÉCNICA: Minuta gerada automaticamente com base em análise de precedentes. Deve ser revisada e personalizada pelo servidor competente antes da publicação oficial."""

    def test_api_connection(self) -> bool:
        """Testa se a API está funcionando"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Teste: responda apenas 'OK'"}],
                max_tokens=10
            )
            print("Resposta da API:", response)
            return "OK" in response.choices[0].message.content
        except Exception as e:
            print("Erro ao testar conexão com a Groq:", e)
            return False
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de uso do gerador."""
        now = time.time()
        recent_requests = [ts for ts in self.request_timestamps if now - ts < 60]
        
        return {
            "requests_last_minute": len(recent_requests),
            "max_requests_per_minute": self.max_requests_per_minute,
            "rate_limit_remaining": max(0, self.max_requests_per_minute - len(recent_requests)),
            "model": self.model,
            "api_key_configured": bool(self.api_key)
        }