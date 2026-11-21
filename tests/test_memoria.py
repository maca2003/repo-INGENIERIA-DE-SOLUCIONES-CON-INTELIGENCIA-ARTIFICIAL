"""IE3 / IE4: memoria de corto plazo, largo plazo y recuperación semántica."""

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agente import configuracion_hilo
from agente.grafo import construir_grafo
from agente.memoria import crear_checkpointer


def test_memorias_semilla_cargadas(agente):
    _, servicios = agente
    assert servicios.memoria.cantidad() == 3


def test_recuperacion_semantica_filtrada_por_cliente(agente):
    _, servicios = agente
    recuerdos = servicios.memoria.recordar("antecedentes importador observaciones", cliente="Distribuidora Sur SpA")
    assert recuerdos and all(r["cliente"] == "Distribuidora Sur SpA" for r in recuerdos)
    assert recuerdos[0]["clave"] == "importador_inconsistente"


def test_episodio_se_consolida_en_memoria_larga(agente, ejecutar):
    _, servicios = agente
    antes = servicios.memoria.cantidad()
    ejecutar("Revisa la OP1003")
    assert servicios.memoria.cantidad() == antes + 1
    episodio = servicios.memoria.recordar("OP1003 diferencia bultos", cliente="Ferretería Central Ltda")[0]
    assert "diferencia_bultos" in episodio["texto"]


def test_memoria_corta_mantiene_operacion_activa(ejecutar):
    ejecutar("Revisa la OP1003", hilo="h1")
    resultado, _ = ejecutar("¿Qué observaciones quedaron registradas?", hilo="h1")
    assert resultado["operacion_activa"] == "OP1003"
    assert "OP1003" in resultado["messages"][-1].content
    otro_hilo, _ = ejecutar("¿Qué observaciones quedaron registradas?", hilo="h2")
    assert otro_hilo.get("operacion_activa", "") == ""


def test_compactacion_de_hilo_largo(ejecutar):
    for _ in range(8):
        resultado, _ = ejecutar("¿Qué documentos iniciales se requieren?", hilo="largo")
    assert resultado["resumen_conversacion"]
    assert len(resultado["messages"]) <= 12 + 4


def test_flujo_pausado_se_retoma_tras_reiniciar(rutas, agente):
    grafo, _ = agente
    cfg = configuracion_hilo("persistente")
    pausado = grafo.invoke({"messages": [HumanMessage(content="Revisa la OP1003")]}, cfg)
    assert "__interrupt__" in pausado

    # Se crea un grafo nuevo con una nueva conexión al mismo archivo SQLite.
    reiniciado = construir_grafo(crear_checkpointer(rutas.checkpoints))
    assert reiniciado.get_state(cfg).next == ("aprobacion_humana",)
    final = reiniciado.invoke(Command(resume="aprobar"), cfg)
    assert final["estado_final"]["estado"] == "Con observaciones"
    assert final["comunicacion"]["estado"] == "aprobada"


def test_preferencia_guardada_en_conversacion_se_usa_en_otra_sesion(agente, ejecutar):
    _, servicios = agente
    ejecutar("Recuerda que el cliente Ferretería Central Ltda prefiere que las comunicaciones se dirijan a Jorge Díaz",
             hilo="sesion-1")
    _, pausas = ejecutar("Revisa la OP1003", hilo="sesion-2")
    assert "Jorge Díaz" in pausas[0]["borrador"]
