"""Mecanismos de memoria del agente.

Memoria de corto plazo
    * Estado del grafo (mensajes, operación activa, plan, hallazgos) que
      LangGraph guarda en un checkpointer SQLite por cada hilo (thread_id).
      Permite retomar un flujo interrumpido (por ejemplo, a la espera de una
      aprobación humana) incluso después de cerrar el programa.
    * Compactación: cuando el hilo supera MAX_MENSAJES_HILO, los mensajes
      antiguos se resumen y se eliminan del estado para respetar la ventana
      de contexto del modelo local.

Memoria de largo plazo
    * Colección ChromaDB "memoria_agente" con antecedentes de clientes,
      preferencias y episodios de revisiones anteriores.
    * Se recupera por similitud semántica (embeddings) filtrando por cliente,
      de modo que el agente recuerda experiencias de otras sesiones.
"""

import json
import sqlite3
import uuid
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from . import config
from .almacen import ahora


# --------------------------------------------------------------------------
# Memoria de corto plazo
# --------------------------------------------------------------------------
def crear_checkpointer(ruta: Path | None):
    """SqliteSaver persistente; InMemorySaver si no se indica ruta."""
    if ruta is None:
        return InMemorySaver()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(str(ruta), check_same_thread=False)
    return SqliteSaver(conexion)


# --------------------------------------------------------------------------
# Memoria de largo plazo
# --------------------------------------------------------------------------
class MemoriaLargoPlazo:
    TIPOS = ("preferencia", "antecedente", "episodio")

    def __init__(self, embeddings: Embeddings, carpeta: Path, coleccion: str = config.COLECCION_MEMORIA):
        self.almacen = Chroma(
            collection_name=coleccion,
            embedding_function=embeddings,
            persist_directory=str(carpeta),
        )

    def cantidad(self) -> int:
        return self.almacen._collection.count()

    def guardar(self, texto: str, tipo: str, cliente: str = "", operacion_id: str = "", clave: str = "", valor: str = "") -> str:
        if tipo not in self.TIPOS:
            raise ValueError(f"Tipo de memoria no válido: {tipo}")
        identificador = f"mem-{uuid.uuid4().hex[:12]}"
        self.almacen.add_documents(
            [
                Document(
                    page_content=texto,
                    metadata={
                        "tipo": tipo,
                        "cliente": cliente,
                        "operacion_id": operacion_id,
                        "clave": clave,
                        "valor": valor,
                        "fecha": ahora(),
                    },
                )
            ],
            ids=[identificador],
        )
        return identificador

    def recordar(self, consulta: str, cliente: str = "", k: int = config.RECUERDOS_POR_CONSULTA,
                 umbral: float = config.UMBRAL_DISTANCIA_MEMORIA) -> list[dict]:
        """Recupera recuerdos semánticamente cercanos a la consulta."""
        if self.cantidad() == 0:
            return []
        filtro = {"cliente": cliente} if cliente else None
        resultados = self.almacen.similarity_search_with_score(consulta, k=k, filter=filtro)
        recuerdos = []
        for documento, distancia in resultados:
            if distancia > umbral:
                continue
            recuerdos.append({**documento.metadata, "texto": documento.page_content, "distancia": round(float(distancia), 4)})
        return recuerdos

    def inicializar_desde_semillas(self, ruta: Path) -> int:
        """Carga memorias iniciales si la colección está vacía."""
        if self.cantidad() > 0 or not ruta.exists():
            return 0
        semillas = json.loads(ruta.read_text(encoding="utf-8"))
        for semilla in semillas:
            self.guardar(**semilla)
        return len(semillas)

    def exportar(self) -> list[dict]:
        datos = self.almacen.get()
        return [
            {"id": i, "texto": t, **m}
            for i, t, m in zip(datos["ids"], datos["documents"], datos["metadatas"])
        ]
