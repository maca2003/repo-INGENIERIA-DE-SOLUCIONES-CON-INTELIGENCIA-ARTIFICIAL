"""AduanaAgent: agente funcional de revisión documental aduanera (EP2 + observabilidad EP3)."""

from . import config, observabilidad
from .config import Rutas
from .grafo import construir_grafo
from .memoria import crear_checkpointer
from .servicios import crear_servicios_reales, crear_servicios_simulados


def crear_agente(modo: str = "real", rutas: Rutas | None = None, persistente: bool = True):
    """Construye servicios + grafo compilado con su checkpointer.

    modo: "real" (proveedor del .env: Ollama o Gemini) o "simulado" (sin LLM).
    persistente: True guarda la memoria de corto plazo en SQLite.
    """
    if rutas is None:
        rutas = Rutas()
        if modo == "simulado":  # no mezclar registros simulados con los reales
            rutas.salidas = rutas.salidas / "simulado"
    observabilidad.configurar(rutas.salidas / "observabilidad")
    servicios = crear_servicios_simulados(rutas) if modo == "simulado" else crear_servicios_reales(rutas)
    checkpointer = crear_checkpointer(rutas.checkpoints if persistente else None)
    return construir_grafo(checkpointer), servicios


def configuracion_hilo(hilo: str, aprobacion_automatica: bool = False) -> dict:
    cfg = {"configurable": {"thread_id": hilo, "aprobacion_automatica": aprobacion_automatica},
           "recursion_limit": 120, "metadata": {"thread_id": hilo}}
    observador = observabilidad.obtener_observador()
    if observador is not None:
        cfg["callbacks"] = [observador]
    return cfg
