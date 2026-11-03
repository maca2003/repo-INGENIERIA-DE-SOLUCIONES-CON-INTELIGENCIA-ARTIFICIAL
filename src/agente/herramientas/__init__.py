"""Catálogo de herramientas del agente, agrupadas por capacidad."""

from .consulta import buscar_memoria, consultar_procedimientos, listar_observaciones, obtener_expediente
from .escritura import (
    actualizar_estado_operacion,
    cerrar_observacion,
    escalar_a_responsable,
    guardar_memoria,
    recibir_documento_corregido,
    redactar_comunicacion_cliente,
    registrar_observacion,
)
from .razonamiento import (
    clasificar_observacion,
    evaluar_requisitos_especiales,
    fundamentar_hallazgos,
    priorizar_operaciones,
    validar_concordancia,
    validar_nomenclatura,
    verificar_documentos_requeridos,
    verificar_permisos,
    verificar_resolucion_observaciones,
)

HERRAMIENTAS_CONSULTA = [consultar_procedimientos, obtener_expediente, listar_observaciones, buscar_memoria]
HERRAMIENTAS_RAZONAMIENTO = [
    verificar_documentos_requeridos, verificar_permisos, validar_concordancia, validar_nomenclatura,
    clasificar_observacion, evaluar_requisitos_especiales, fundamentar_hallazgos,
    verificar_resolucion_observaciones, priorizar_operaciones,
]
HERRAMIENTAS_ESCRITURA = [
    registrar_observacion, cerrar_observacion, redactar_comunicacion_cliente, actualizar_estado_operacion,
    escalar_a_responsable, recibir_documento_corregido, guardar_memoria,
]
TODAS = HERRAMIENTAS_CONSULTA + HERRAMIENTAS_RAZONAMIENTO + HERRAMIENTAS_ESCRITURA
POR_NOMBRE = {h.name: h for h in TODAS}

# Subconjunto expuesto al agente conversacional (ReAct). Se limita a
# herramientas seguras para que un modelo pequeño elija con precisión.
HERRAMIENTAS_CONVERSACION = [
    consultar_procedimientos, obtener_expediente, listar_observaciones, buscar_memoria,
    priorizar_operaciones, guardar_memoria,
]
