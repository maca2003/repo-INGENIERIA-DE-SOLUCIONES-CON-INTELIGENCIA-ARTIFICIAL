"""Inyección de dependencias del agente.

Las herramientas y nodos obtienen el modelo, el recuperador, la memoria y el
almacén desde un único objeto Servicios. Así el mismo agente se ejecuta con
Ollama o Gemini (modo real) o con componentes simulados (pruebas automáticas y CI),
sin modificar la lógica del flujo.
"""

from dataclasses import dataclass
from typing import Callable

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel

from . import config
from .almacen import Almacen
from .config import Rutas
from .memoria import MemoriaLargoPlazo

Recuperador = Callable[[str, int], list[tuple[Document, float]]]


@dataclass
class Servicios:
    llm: BaseChatModel
    recuperador: Recuperador
    memoria: MemoriaLargoPlazo
    almacen: Almacen
    rutas: Rutas
    modo: str = "ollama"


_SERVICIOS: Servicios | None = None


def configurar_servicios(servicios: Servicios) -> Servicios:
    global _SERVICIOS
    _SERVICIOS = servicios
    return servicios


def obtener_servicios() -> Servicios:
    if _SERVICIOS is None:
        raise RuntimeError("Servicios no configurados. Llama a crear_servicios_reales() o crear_servicios_simulados().")
    return _SERVICIOS


def crear_servicios_reales(rutas: Rutas | None = None) -> Servicios:
    """Servicios reales con el proveedor del .env (Ollama o Gemini)."""
    from langchain_chroma import Chroma

    from . import modelos

    rutas = rutas or Rutas()
    rutas.chroma = modelos.carpeta_chroma(rutas.raiz)
    embeddings = modelos.crear_embeddings()
    base_conocimiento = Chroma(
        collection_name=config.COLECCION_CONOCIMIENTO,
        embedding_function=embeddings,
        persist_directory=str(rutas.chroma),
    )
    if base_conocimiento._collection.count() == 0:
        raise RuntimeError(
            "La base vectorial está vacía. Ejecuta primero: python src/crear_base_vectorial.py"
        )

    def recuperador(pregunta: str, k: int) -> list[tuple[Document, float]]:
        return base_conocimiento.similarity_search_with_score(pregunta, k=k)

    memoria = MemoriaLargoPlazo(embeddings, rutas.memoria_larga)
    memoria.inicializar_desde_semillas(rutas.memoria_inicial)
    return configurar_servicios(
        Servicios(llm=modelos.crear_llm(), recuperador=recuperador, memoria=memoria,
                  almacen=Almacen(rutas), rutas=rutas, modo=modelos.proveedor())
    )


# Nombre anterior, se mantiene por compatibilidad.
crear_servicios_ollama = crear_servicios_reales


def crear_servicios_simulados(rutas: Rutas | None = None) -> Servicios:
    """Servicios sin Ollama: modelo y embeddings deterministas para pruebas."""
    from .simulacion import EmbeddingsLexicos, ModeloSimulado, RecuperadorLexico

    rutas = rutas or Rutas()
    recuperador = RecuperadorLexico(rutas.raiz / "data")
    memoria = MemoriaLargoPlazo(EmbeddingsLexicos(), rutas.memoria_larga)
    memoria.inicializar_desde_semillas(rutas.memoria_inicial)
    return configurar_servicios(
        Servicios(llm=ModeloSimulado(), recuperador=recuperador, memoria=memoria,
                  almacen=Almacen(rutas), rutas=rutas, modo="simulado")
    )
