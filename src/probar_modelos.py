"""Verifica que el LLM y los embeddings del proveedor configurado respondan.

Equivale al paso 0.11 de la guía (scripts/verify_llm.py).
Ejecutar:  python src/probar_modelos.py
"""

import sys

from agente import modelos


def probar_llm():
    print(f"Proveedor: {modelos.describir()}")
    print("Probando modelo de lenguaje...")
    respuesta = modelos.crear_llm(temperatura=0).invoke(
        "Responde únicamente con la frase: CONEXION LLM CORRECTA"
    )
    print(respuesta.text)


def probar_embeddings():
    print("\nProbando modelo de embeddings...")
    vector = modelos.crear_embeddings().embed_query(
        "Procedimiento documental de una agencia de aduanas"
    )
    print(f"EMBEDDING CORRECTO - Dimensiones: {len(vector)}")
    print(f"Primeros cinco valores: {vector[:5]}")


if __name__ == "__main__":
    try:
        probar_llm()
        probar_embeddings()
    except Exception as error:
        print(f"\nERROR: {error}")
        print("Ollama: revisa que esté iniciado y con los modelos descargados (ollama list).")
        print("Gemini: revisa GOOGLE_API_KEY y LLM_MODEL en el archivo .env.")
        sys.exit(1)
