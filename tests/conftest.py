"""Fixtures comunes: cada prueba usa una carpeta de salidas temporal y
servicios simulados (sin Ollama), de modo que las pruebas son reproducibles."""

import pytest
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agente import Rutas, configuracion_hilo, crear_agente


@pytest.fixture
def rutas(tmp_path):
    r = Rutas()
    r.salidas = tmp_path / "salidas"
    return r


@pytest.fixture
def agente(rutas):
    grafo, servicios = crear_agente("simulado", rutas)
    return grafo, servicios


@pytest.fixture
def ejecutar(agente):
    grafo, _ = agente

    def _ejecutar(mensaje, hilo="prueba", respuesta="aprobar"):
        cfg = configuracion_hilo(hilo)
        resultado = grafo.invoke({"messages": [HumanMessage(content=mensaje)]}, cfg)
        pausas = []
        while "__interrupt__" in resultado and respuesta is not None:
            pausas.append(resultado["__interrupt__"][0].value)
            resultado = grafo.invoke(Command(resume=respuesta), cfg)
        return resultado, pausas

    return _ejecutar


def acciones(resultado):
    return [t["accion"] for t in sorted(resultado["plan"], key=lambda t: t.get("orden_ejecucion") or 99)]
