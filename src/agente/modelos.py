"""Fábrica de modelos: un solo lugar decide qué LLM y qué embeddings se usan.

El proveedor se elige en el archivo .env con AGENTE_PROVEEDOR:

* ollama (por defecto): modelos locales llama3.2:3b y qwen3-embedding:0.6b.
  Los documentos no salen del computador (INT-003).
* gemini: Gemini Flash vía API (nivel gratuito, requiere GOOGLE_API_KEY).
  Opción recomendada por la guía EVA02 cuando el equipo no puede ejecutar
  Ollama con fluidez.

Cada proveedor usa su propia carpeta de ChromaDB, porque los vectores de
modelos de embeddings distintos no son comparables entre sí.
"""

from pathlib import Path

from . import config


def proveedor() -> str:
    valor = config.PROVEEDOR.strip().lower()
    if valor not in ("ollama", "gemini"):
        raise ValueError(f"AGENTE_PROVEEDOR debe ser 'ollama' o 'gemini' (valor actual: {valor!r})")
    return valor


def _exigir_api_key() -> str:
    if not config.GOOGLE_API_KEY:
        raise RuntimeError(
            "Falta GOOGLE_API_KEY en el archivo .env (obténla en https://aistudio.google.com/apikey)."
        )
    return config.GOOGLE_API_KEY


def crear_llm(temperatura: float | None = None):
    """Modelo de chat del proveedor configurado."""
    temperatura = config.TEMPERATURA if temperatura is None else temperatura
    if proveedor() == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=config.MODELO_LLM_GEMINI, google_api_key=_exigir_api_key(), temperature=temperatura
        )
    from langchain_ollama import ChatOllama

    if config.OPTIMIZADO:
        # keep_alive evita que Ollama descargue el modelo tras 5 minutos sin uso
        # (arranque en frío); num_predict acota la longitud de cada respuesta.
        return ChatOllama(model=config.MODELO_LLM, temperature=temperatura, keep_alive=config.KEEP_ALIVE,
                          num_predict=config.NUM_PREDICT, num_ctx=config.NUM_CTX)
    return ChatOllama(model=config.MODELO_LLM, temperature=temperatura)


def crear_embeddings():
    """Modelo de embeddings del proveedor configurado."""
    if proveedor() == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model=config.MODELO_EMBEDDINGS_GEMINI, google_api_key=_exigir_api_key()
        )
    from langchain_ollama import OllamaEmbeddings

    if config.OPTIMIZADO:
        return OllamaEmbeddings(model=config.MODELO_EMBEDDINGS, keep_alive=config.KEEP_ALIVE)
    return OllamaEmbeddings(model=config.MODELO_EMBEDDINGS)


def precalentar(llm, embeddings) -> float:
    """Carga ambos modelos en memoria antes de la primera consulta del usuario.

    Devuelve los segundos que tardó. Si falla, no detiene el agente.
    """
    import time

    inicio = time.perf_counter()
    try:
        embeddings.embed_query("precalentamiento")
        llm.invoke("Responde solo: ok")
    except Exception:
        pass
    return round(time.perf_counter() - inicio, 2)


def carpeta_chroma(raiz: Path = config.RAIZ_PROYECTO) -> Path:
    """chroma_db/ para Ollama y chroma_db_gemini/ para Gemini."""
    return raiz / ("chroma_db_gemini" if proveedor() == "gemini" else "chroma_db")


def describir() -> str:
    if proveedor() == "gemini":
        return f"gemini · {config.MODELO_LLM_GEMINI} · {config.MODELO_EMBEDDINGS_GEMINI}"
    return f"ollama · {config.MODELO_LLM} · {config.MODELO_EMBEDDINGS}"
