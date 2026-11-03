"""AduanaAgent: agente funcional de revisión documental aduanera (EP2)."""

from .config import Rutas
from .grafo import construir_grafo
from .memoria import crear_checkpointer
from .servicios import crear_servicios_ollama, crear_servicios_simulados


def crear_agente(modo: str = "ollama", rutas: Rutas | None = None, persistente: bool = True):
    """Construye servicios + grafo compilado con su checkpointer.

    modo: "ollama" (modelos locales reales) o "simulado" (sin Ollama).
    persistente: True guarda la memoria de corto plazo en SQLite.
    """
    if rutas is None:
        rutas = Rutas()
        if modo == "simulado":  # no mezclar registros simulados con los reales
            rutas.salidas = rutas.salidas / "simulado"
    servicios = crear_servicios_simulados(rutas) if modo == "simulado" else crear_servicios_ollama(rutas)
    checkpointer = crear_checkpointer(rutas.checkpoints if persistente else None)
    return construir_grafo(checkpointer), servicios


def configuracion_hilo(hilo: str, aprobacion_automatica: bool = False) -> dict:
    return {"configurable": {"thread_id": hilo, "aprobacion_automatica": aprobacion_automatica},
            "recursion_limit": 120}
