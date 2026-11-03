"""Pruebas end-to-end (Fase 9 de la guía): recorren el flujo completo
contexto → planificador → herramientas → registro → estado → memoria."""

from conftest import acciones


def test_flujo_estandar_deriva_a_revision(ejecutar, agente):
    _, servicios = agente
    resultado, _ = ejecutar("Revisa la OP1001")
    assert resultado["estado_final"]["estado"] == "Derivada a revisión"
    assert servicios.almacen.estado_operacion("OP1001")["estado"] == "Derivada a revisión"
    assert servicios.almacen.leer_trazabilidad("OP1001")  # dejó trazabilidad


def test_flujo_critico_escala_sin_comunicar(ejecutar):
    resultado, pausas = ejecutar("Revisa la OP1004")
    assert "escalar" in acciones(resultado)
    assert pausas == []  # no se pide aprobar un correo al cliente


def test_flujo_faltantes_queda_pendiente(ejecutar):
    resultado, pausas = ejecutar("Revisa la OP1002")
    assert resultado["estado_final"]["estado"] == "Pendiente de documentación"
    assert len(pausas) == 1


def test_operacion_inexistente(ejecutar):
    resultado, _ = ejecutar("Revisa la OP9999")
    assert resultado["intencion"] == "inexistente"
    assert "No existe la operación OP9999" in resultado["messages"][-1].text
    assert not resultado.get("plan")


def test_informe_de_revision_generado(ejecutar, agente):
    _, servicios = agente
    ejecutar("Revisa la OP1001")
    informe = servicios.rutas.salidas / "OP1001" / "informe_revision.md"
    assert informe.exists() and "Decisiones del agente" in informe.read_text(encoding="utf-8")
