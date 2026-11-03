"""IE5 / IE7: planificación por prioridades y decisiones ante condiciones cambiantes."""

from conftest import acciones

from agente.memoria import MemoriaLargoPlazo
from agente.planificador import crear_plan, siguiente_tarea
from agente.simulacion import EmbeddingsLexicos


def test_flujo_limpio_deriva_a_revision(ejecutar):
    resultado, pausas = ejecutar("Revisa la OP1001")
    assert resultado["estado_final"]["estado"] == "Derivada a revisión"
    assert resultado["hallazgos"] == [] and pausas == []
    assert "verificar_permisos" not in acciones(resultado)


def test_faltantes_dejan_pendiente_y_usan_preferencia(ejecutar):
    resultado, pausas = ejecutar("Revisa la OP1002")
    assert resultado["estado_final"]["estado"] == "Pendiente de documentación"
    assert "Paula Rojas" in pausas[0]["borrador"] and "48 horas" in pausas[0]["borrador"]
    assert "[URGENTE]" in pausas[0]["borrador"]


def test_critica_se_ejecuta_primero_y_suspende_comunicacion(ejecutar):
    resultado, pausas = ejecutar("Revisa la OP1004")
    orden = acciones(resultado)
    assert orden[0] == "verificar_permisos"
    assert orden.index("escalar") < orden.index("validar_nomenclatura")  # replanificación: escalar antes
    assert "redactar_comunicacion" not in orden and pausas == []
    assert resultado["estado_final"]["estado"] == "Con observaciones"


def test_antecedente_en_memoria_cambia_el_plan(agente, rutas):
    _, servicios = agente
    expediente = servicios.almacen.obtener_expediente("OP1004")
    recuerdos = servicios.memoria.recordar("antecedentes", cliente="Distribuidora Sur SpA")
    con_memoria, _ = crear_plan(expediente, recuerdos, [], None)
    sin_memoria, _ = crear_plan(expediente, [], [], None)
    concordancia = lambda plan: next(t for t in plan if t["accion"] == "validar_concordancia")  # noqa: E731
    assert concordancia(con_memoria)["args"]["reforzada"] is True and concordancia(con_memoria)["prioridad"] == 1
    assert concordancia(sin_memoria)["args"]["reforzada"] is False and concordancia(sin_memoria)["prioridad"] == 2


def test_siguiente_tarea_respeta_prioridad_y_secuencia():
    plan = [
        {"id": "T01", "accion": "a", "prioridad": 2, "secuencia": 0, "estado": "pendiente"},
        {"id": "T02", "accion": "b", "prioridad": 0, "secuencia": 1, "estado": "pendiente"},
        {"id": "T03", "accion": "c", "prioridad": 0, "secuencia": 2, "estado": "pendiente"},
    ]
    assert siguiente_tarea(plan)["id"] == "T02"
    plan[1]["estado"] = "completada"
    assert siguiente_tarea(plan)["id"] == "T03"


def test_mercancia_no_catalogada_sin_evidencia_se_escala(agente, ejecutar):
    _, servicios = agente
    servicios.recuperador = lambda pregunta, k: []  # la base no tiene evidencia
    resultado, _ = ejecutar("Revisa la OP1005")
    tipos = {h["tipo"] for h in resultado["hallazgos"]}
    assert "requisito_no_determinado" in tipos
    assert "escalar" in acciones(resultado)


def test_correccion_cierra_observaciones_y_cambia_estado(agente, ejecutar):
    _, servicios = agente
    primero, _ = ejecutar("Revisa la OP1003", hilo="op3")
    assert primero["estado_final"]["estado"] == "Con observaciones"
    segundo, _ = ejecutar("Llegó la lista de empaque corregida de la OP1003, reprocésala", hilo="op3")
    assert acciones(segundo)[:2] == ["incorporar_correccion", "verificar_resolucion"]
    assert segundo["estado_final"]["estado"] == "Derivada a revisión"
    assert all(o["estado"] == "Cerrada" for o in servicios.almacen.observaciones("OP1003"))


def test_falla_de_herramienta_reintenta_y_escala(agente, ejecutar):
    _, servicios = agente

    def recuperador_caido(pregunta, k):
        raise ConnectionError("Ollama no responde")

    servicios.recuperador = recuperador_caido
    resultado, _ = ejecutar("Revisa la OP1005")
    tarea = next(t for t in resultado["plan"] if t["accion"] == "evaluar_requisitos_especiales")
    assert tarea["estado"] == "fallida" and tarea["intentos"] == 2
    assert any(d["decision"] == "Reintentar la tarea" for d in resultado["decisiones"])
    assert "escalar" in acciones(resultado)


def test_rechazo_humano_no_envia_comunicacion(ejecutar):
    resultado, pausas = ejecutar("Revisa la OP1003", respuesta="rechazar")
    assert pausas and resultado["comunicacion"]["estado"] == "rechazada"
    assert resultado["estado_final"]["estado"] == "Con observaciones"


def test_enrutamiento_por_intencion(ejecutar):
    revision, _ = ejecutar("Revisa la OP1001", hilo="r1")
    cola, _ = ejecutar("Prioriza la cola de trabajo", hilo="r2")
    charla, _ = ejecutar("¿Qué documentos iniciales se requieren?", hilo="r3")
    assert revision["intencion"] == "revision"
    assert cola["intencion"] == "cola" and "Orden recomendado" in cola["messages"][-1].content
    assert charla["intencion"] == "conversacion"
    assert any("consultar_procedimientos" in b["detalle"] for b in charla["bitacora"])
