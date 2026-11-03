"""Calibra el umbral de distancia del RAG con preguntas con y sin respuesta.

Ejecuta: python src/calibrar_umbral.py
Muestra la distancia del mejor fragmento para cada pregunta de
tests/preguntas_evaluacion.json y sugiere un umbral que separa ambos grupos.
Luego puede fijarse en .env:  AGENTE_UMBRAL_DISTANCIA_RAG=<valor>
"""

import json
from pathlib import Path

from crear_base_vectorial import obtener_base_vectorial

RAIZ = Path(__file__).resolve().parent.parent

PREGUNTAS_EXTRA_SIN_RESPUESTA = [
    "¿La importación de drones de uso recreativo requiere autorización, permiso o control previo?",
    "¿Cuál es el precio del dólar hoy?",
]


def main() -> None:
    base = obtener_base_vectorial()
    casos = json.loads((RAIZ / "tests" / "preguntas_evaluacion.json").read_text(encoding="utf-8"))
    con, sin = [], []
    print(f"{'Categoría':<15} {'Distancia':>9}  Pregunta")
    for caso in casos:
        documento, distancia = base.similarity_search_with_score(caso["pregunta"], k=1)[0]
        (sin if caso["categoria"] == "sin_respuesta" else con).append(distancia)
        print(f"{caso['categoria']:<15} {distancia:>9.4f}  {caso['pregunta'][:70]}")
    for pregunta in PREGUNTAS_EXTRA_SIN_RESPUESTA:
        distancia = base.similarity_search_with_score(pregunta, k=1)[0][1]
        sin.append(distancia)
        print(f"{'sin_respuesta*':<15} {distancia:>9.4f}  {pregunta[:70]}")
    print(f"\nMáxima distancia con respuesta: {max(con):.4f}")
    print(f"Mínima distancia sin respuesta: {min(sin):.4f}")
    if max(con) < min(sin):
        print(f"Umbral sugerido: {(max(con) + min(sin)) / 2:.3f}")
    else:
        print("Los grupos se superponen: el umbral solo filtra casos extremos; la abstención la decide el LLM.")


if __name__ == "__main__":
    main()
