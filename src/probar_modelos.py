from langchain_ollama import ChatOllama, OllamaEmbeddings


def probar_llm():
    print("Probando modelo de lenguaje...")

    modelo = ChatOllama(
        model="llama3.2:3b",
        temperature=0,
    )

    respuesta = modelo.invoke(
        "Responde únicamente con la frase: CONEXION LLM CORRECTA"
    )

    print(respuesta.content)


def probar_embeddings():
    print("\nProbando modelo de embeddings...")

    embeddings = OllamaEmbeddings(
        model="qwen3-embedding:0.6b"
    )

    vector = embeddings.embed_query(
        "Procedimiento documental de una agencia de aduanas"
    )

    print(f"EMBEDDING CORRECTO - Dimensiones: {len(vector)}")
    print(f"Primeros cinco valores: {vector[:5]}")


if __name__ == "__main__":
    probar_llm()
    probar_embeddings()