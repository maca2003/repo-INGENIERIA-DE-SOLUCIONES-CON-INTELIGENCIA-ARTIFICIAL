"""Pruebas de integración con el modelo REAL configurado en .env
(Ollama o Gemini). Se omiten automáticamente si el proveedor no está
disponible o si no existe la base vectorial.

Ejecutar:  python -m pytest -m real -v
"""

import urllib.request

import pytest
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agente import Rutas, config, configuracion_hilo, crear_agente


def proveedor_disponible() -> tuple[bool, str]:
    proveedor = config.PROVEEDOR.strip().lower()
    if proveedor == "gemini":
        return bool(config.GOOGLE_API_KEY), "Falta GOOGLE_API_KEY en .env"
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True, ""
    except Exception:
        return False, "Ollama no está en ejecución"


DISPONIBLE, MOTIVO = proveedor_disponible()
pytestmark = [pytest.mark.real, pytest.mark.skipif(not DISPONIBLE, reason=MOTIVO)]


@pytest.fixture
def agente_real(tmp_path):
    rutas = Rutas()
    rutas.salidas = tmp_path / "salidas"
    try:
        return crear_agente("real", rutas)
    except RuntimeError as error:
        pytest.skip(str(error))


def test_revision_real_op1003(agente_real):
    grafo, _ = agente_real
    cfg = configuracion_hilo("real")
    resultado = grafo.invoke({"messages": [HumanMessage(content="Revisa la OP1003")]}, cfg)
    assert "__interrupt__" in resultado
    resultado = grafo.invoke(Command(resume="aprobar"), cfg)
    assert resultado["estado_final"]["estado"] == "Con observaciones"
    assert resultado["messages"][-1].text


def test_rag_real_responde_con_fuente(agente_real):
    from agente.herramientas import POR_NOMBRE
    respuesta = POR_NOMBRE["consultar_procedimientos"].invoke(
        {"pregunta": "¿Qué documentos iniciales deben revisarse antes de preparar una operación?"})
    assert respuesta["suficiente"] is True
    assert respuesta["fuentes"]


def test_rag_real_se_abstiene(agente_real):
    from agente.herramientas import POR_NOMBRE
    respuesta = POR_NOMBRE["consultar_procedimientos"].invoke({"pregunta": "¿Cuál es el horario de atención del sábado?"})
    assert respuesta["suficiente"] is False


def test_agente_conversacional_real_usa_herramienta(agente_real):
    grafo, _ = agente_real
    resultado = grafo.invoke({"messages": [HumanMessage(content="¿Qué documentos iniciales deben revisarse?")]},
                             configuracion_hilo("real-chat"))
    # Con AGENTE_OPTIMIZADO la pregunta va por la ruta directa; sin él, por ReAct.
    detalle = next(b["detalle"] for b in reversed(resultado["bitacora"])
                   if b["nodo"] in ("agente_conversacional", "respuesta_directa"))
    assert "ninguna" not in detalle
