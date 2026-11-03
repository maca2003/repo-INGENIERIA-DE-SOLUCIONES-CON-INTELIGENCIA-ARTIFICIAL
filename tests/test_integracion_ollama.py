"""Pruebas de integración con los modelos reales. Se omiten si Ollama no
está disponible o si no existe la base vectorial.

Ejecutar: python -m pytest -m ollama -v
"""

import urllib.request

import pytest
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agente import Rutas, configuracion_hilo, crear_agente


def ollama_disponible() -> bool:
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True
    except Exception:
        return False


pytestmark = [pytest.mark.ollama,
              pytest.mark.skipif(not ollama_disponible(), reason="Ollama no está en ejecución")]


@pytest.fixture
def agente_real(tmp_path):
    rutas = Rutas()
    rutas.salidas = tmp_path / "salidas"
    try:
        return crear_agente("ollama", rutas)
    except RuntimeError as error:
        pytest.skip(str(error))


def test_revision_real_op1003(agente_real):
    grafo, _ = agente_real
    cfg = configuracion_hilo("real")
    resultado = grafo.invoke({"messages": [HumanMessage(content="Revisa la OP1003")]}, cfg)
    assert "__interrupt__" in resultado
    resultado = grafo.invoke(Command(resume="aprobar"), cfg)
    assert resultado["estado_final"]["estado"] == "Con observaciones"
    assert resultado["messages"][-1].content


def test_rag_real_se_abstiene(agente_real):
    from agente.herramientas import POR_NOMBRE
    respuesta = POR_NOMBRE["consultar_procedimientos"].invoke({"pregunta": "¿Cuál es el horario de atención del sábado?"})
    assert respuesta["suficiente"] is False


def test_agente_conversacional_real_usa_herramienta(agente_real):
    grafo, _ = agente_real
    resultado = grafo.invoke({"messages": [HumanMessage(content="¿Qué documentos iniciales deben revisarse?")]},
                             configuracion_hilo("real-chat"))
    detalle = next(b["detalle"] for b in reversed(resultado["bitacora"]) if b["nodo"] == "agente_conversacional")
    assert "ninguna" not in detalle
