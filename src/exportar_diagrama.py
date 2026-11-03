"""Exporta el diagrama Mermaid generado desde el grafo LangGraph compilado.

Ejecutar: python src/exportar_diagrama.py
Genera documentacion/diagramas/grafo_langgraph.mmd, que corresponde
exactamente a los nodos y aristas implementados en src/agente/grafo.py.
"""

from pathlib import Path

from agente.grafo import construir_grafo

RAIZ = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    destino = RAIZ / "documentacion" / "diagramas" / "grafo_langgraph.mmd"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(construir_grafo().get_graph().draw_mermaid(), encoding="utf-8")
    print(f"Diagrama exportado en {destino}")
