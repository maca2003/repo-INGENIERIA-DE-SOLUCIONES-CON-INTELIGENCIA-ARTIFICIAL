"""IE1: cada herramienta ejecuta su función específica de forma correcta."""

from agente.herramientas import POR_NOMBRE, TODAS
from agente.herramientas.razonamiento import puntaje_prioridad


def test_catalogo_de_herramientas_por_capacidad(agente):
    nombres = {h.name for h in TODAS}
    assert {"consultar_procedimientos", "obtener_expediente"} <= nombres            # consulta
    assert {"verificar_documentos_requeridos", "validar_concordancia"} <= nombres  # razonamiento
    assert {"registrar_observacion", "redactar_comunicacion_cliente"} <= nombres   # escritura
    assert all(h.description for h in TODAS)


def test_documentos_faltantes_incluye_certificado_por_preferencia(agente):
    resultado = POR_NOMBRE["verificar_documentos_requeridos"].invoke({"operacion_id": "OP1002"})
    assert "Lista de empaque" in resultado["faltantes"]
    assert any("Certificado de origen" in f for f in resultado["faltantes"])
    assert all(h["nivel"] == "corregible" for h in resultado["hallazgos"])


def test_permisos_mercancia_regulada(agente):
    resultado = POR_NOMBRE["verificar_permisos"].invoke({"operacion_id": "OP1004"})
    assert resultado["regulada"] is True
    assert {h["organismo"] for h in resultado["hallazgos"]} == {"Servicio Agrícola y Ganadero", "Autoridad sanitaria"}
    assert all(h["nivel"] == "critica" for h in resultado["hallazgos"])


def test_concordancia_detecta_bultos_y_peso(agente):
    resultado = POR_NOMBRE["validar_concordancia"].invoke({"operacion_id": "OP1003"})
    tipos = {h["tipo"] for h in resultado["hallazgos"]}
    assert tipos == {"diferencia_bultos", "diferencia_peso"}


def test_concordancia_sin_hallazgos_en_expediente_correcto(agente):
    assert POR_NOMBRE["validar_concordancia"].invoke({"operacion_id": "OP1001"})["hallazgos"] == []


def test_nomenclatura_es_informativa(agente):
    resultado = POR_NOMBRE["validar_nomenclatura"].invoke({"operacion_id": "OP1003"})
    assert [h["nivel"] for h in resultado["hallazgos"]] == ["informativa"]


def test_clasificacion_segun_int002(agente):
    clasificar = POR_NOMBRE["clasificar_observacion"]
    assert clasificar.invoke({"tipo_hallazgo": "diferencia_bultos"})["nivel"] == "corregible"
    assert clasificar.invoke({"tipo_hallazgo": "importador_inconsistente"})["nivel"] == "critica"
    assert clasificar.invoke({"tipo_hallazgo": "nomenclatura"})["nivel"] == "informativa"
    # criterio conservador ante un hallazgo desconocido
    assert clasificar.invoke({"tipo_hallazgo": "desconocido"})["nivel"] == "critica"


def test_rag_responde_con_fuente_y_se_abstiene_sin_evidencia(agente):
    consulta = POR_NOMBRE["consultar_procedimientos"]
    con = consulta.invoke({"pregunta": "¿Qué se debe hacer si existen diferencias en cantidades o peso?"})
    assert con["suficiente"] and con["fuentes"]
    sin = consulta.invoke({"pregunta": "¿Cuál es el horario de atención del sábado?"})
    assert sin["suficiente"] is False
    assert sin["respuesta"].startswith("No existe información suficiente")


def test_escritura_registra_trazabilidad_y_no_duplica(agente):
    _, servicios = agente
    registrar = POR_NOMBRE["registrar_observacion"]
    args = {"operacion_id": "OP1003", "tipo": "diferencia_bultos", "documento": "lista_empaque",
            "descripcion": "Bultos distintos"}
    primera = registrar.invoke(args)
    segunda = registrar.invoke(args)
    assert primera["id"] == segunda["id"] and segunda["ya_registrada"]
    traza = servicios.almacen.leer_trazabilidad("OP1003")
    assert traza and {"usuario", "fecha_hora", "operacion", "accion", "documento", "resultado"} <= set(traza[0])


def test_correccion_crea_nueva_version_sin_sobrescribir(agente):
    _, servicios = agente
    resultado = POR_NOMBRE["recibir_documento_corregido"].invoke(
        {"ruta_correccion": "data/operaciones/correcciones/OP1003_lista_empaque_V2.json"})
    assert resultado["version_nueva"] == "LISTAEMPAQUE_OP1003_V2.pdf"
    expediente = servicios.almacen.obtener_expediente("OP1003")
    assert expediente["historial_versiones"][0]["version_reemplazada"]["archivo"] == "lista empaque final.pdf"
    original = (servicios.rutas.operaciones / "OP1003.json").read_text(encoding="utf-8")
    assert "lista empaque final.pdf" in original  # la bandeja de entrada no se modifica


def test_priorizacion_por_urgencia_arribo_y_riesgo(agente):
    cola = POR_NOMBRE["priorizar_operaciones"].invoke({"fecha_referencia": "2026-11-02"})
    assert cola[0]["operacion_id"] == "OP1004"  # urgente + arribo cercano + regulada
    assert [o["orden"] for o in cola] == list(range(1, len(cola) + 1))
    puntaje, motivos = puntaje_prioridad(
        {"urgente": False, "fecha_arribo_estimada": "2026-12-31", "mercancia": {"categoria": "maquinaria"}})
    assert puntaje == 0 and motivos == []
