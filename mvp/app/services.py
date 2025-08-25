# services.py
from typing import List, Dict, Optional, Any
from app.models import SimilarAppeal

def analyze_decision_stats(search_results: List) -> Dict:
    """Calcula as estatísticas de decisão (Deferido/Indeferido) dos resultados."""
    if not search_results:
        return {}

    decision_counts = {}
    for result in search_results:
        decision = result.payload.get("decision", "N/A")
        decision_counts[decision] = decision_counts.get(decision, 0) + 1

    total_found = len(search_results)
    stats = {
        key: {"count": value, "percentage": round((value / total_found) * 100, 2)}
        for key, value in decision_counts.items()
    }
    return stats


def determine_likely_decision(stats: Dict) -> str:
    """Determina a decisão mais provável com base nas estatísticas."""
    if not stats:
        return "Indeterminado"

    relevant_decisions = {k: v['count'] for k, v in stats.items() if k in ["Deferido", "Indeferido"]}
    if not relevant_decisions:
        return "Indeterminado (nenhum Deferido/Indeferido encontrado nos similares)"

    most_common = max(relevant_decisions, key=relevant_decisions.get)
    return f"Provavelmente {most_common}"


def format_similar_appeals(search_results: List) -> List[SimilarAppeal]:
    """Formata os resultados da busca do Qdrant no modelo Pydantic."""
    appeals_list = []
    for result in search_results:
        payload = result.payload
        appeals_list.append(
            SimilarAppeal(
                id=result.id, score=result.score,
                description=payload.get("description", ""),
                response=payload.get("response", ""),
                decision=payload.get("decision", "N/A"),
                instance=payload.get("instance", "N/A")
            )
        )
    return appeals_list

def get_decision_summary(stats: Dict) -> Optional[Dict[str, Any]]:
    """Gera um sumário das decisões para debugging e monitoramento."""
    if not stats:
        return None
    
    total_cases = sum(data['count'] for data in stats.values())
    summary = {
        "total_cases": total_cases,
        "decision_types": len(stats),
        "most_common": max(stats.items(), key=lambda x: x[1]['count'])[0],
        "distribution": {k: v['percentage'] for k, v in stats.items()}
    }
    
    return summary