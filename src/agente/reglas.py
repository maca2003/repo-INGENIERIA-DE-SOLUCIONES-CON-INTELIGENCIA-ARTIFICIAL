"""Reglas de negocio derivadas de los procedimientos internos simulados.

Cada regla indica el documento de la base de conocimiento que la respalda
(INT-001, INT-002, INT-003 o EXT-001), para que toda decisión del agente
sea trazable a una fuente.
"""

# Documentos exigidos siempre (INT-001, "Documentos iniciales requeridos").
DOCUMENTOS_OBLIGATORIOS = {
    "factura_comercial": "Factura comercial",
    "documento_transporte": "Documento de transporte",
    "lista_empaque": "Lista de empaque",
    "mandato": "Mandato o autorización vigente",
}

NOMBRES_DOCUMENTOS = {
    **DOCUMENTOS_OBLIGATORIOS,
    "certificado_origen": "Certificado de origen",
    "permiso": "Permiso o visto bueno",
}

# Prefijo esperado en el nombre de archivo (INT-003, "Convención de nombres").
PREFIJOS_ARCHIVO = {
    "factura_comercial": "FACTURA",
    "documento_transporte": "TRANSPORTE",
    "lista_empaque": "LISTAEMPAQUE",
    "mandato": "MANDATO",
    "certificado_origen": "CERTIFICADOORIGEN",
}

# Mercancías sujetas a control previo (EXT-001) y organismo competente.
CATEGORIAS_REGULADAS = {
    "alimentos": ["Autoridad sanitaria"],
    "alimentos_origen_vegetal": ["Servicio Agrícola y Ganadero", "Autoridad sanitaria"],
    "origen_animal": ["Servicio Agrícola y Ganadero"],
    "origen_vegetal": ["Servicio Agrícola y Ganadero"],
    "farmaceuticos": ["Instituto de Salud Pública"],
    "cosmeticos": ["Instituto de Salud Pública"],
    "sustancias_peligrosas": ["Autoridad sanitaria"],
    "radiocomunicaciones": ["Subsecretaría de Telecomunicaciones"],
    "recursos_hidrobiologicos": ["Servicio Nacional de Pesca"],
    "materiales_radiactivos": ["Comisión Chilena de Energía Nuclear"],
    "especies_protegidas": ["Servicio Agrícola y Ganadero"],
}

# Categorías que el agente conoce y sabe que NO requieren control previo.
CATEGORIAS_SIN_CONTROL = {"maquinaria", "textiles", "herramientas", "mobiliario", "repuestos"}

NIVELES = ("informativa", "corregible", "critica")

# Catálogo de hallazgos: nivel (INT-002), acción y pregunta para buscar el
# fundamento en la base de conocimiento.
CATALOGO_HALLAZGOS = {
    "documento_faltante": {
        "nivel": "corregible",
        "accion": "Solicitar al cliente el antecedente pendiente.",
        "regla": "INT-001: si falta información, se comunica al cliente y la operación queda Pendiente de documentación.",
        "pregunta": "¿Qué se debe hacer si falta información o documentación en la recepción de antecedentes?",
        "fuente_esperada": "procedimiento_recepcion_documentos.md",
    },
    "permiso_faltante": {
        "nivel": "critica",
        "accion": "Escalar al responsable de revisión; no continuar la preparación.",
        "regla": "INT-002: la ausencia de un permiso obligatorio es una observación crítica.",
        "pregunta": "¿Cómo se clasifica la ausencia de un permiso obligatorio?",
        "fuente_esperada": "gestion_observaciones_operacion.md",
    },
    "diferencia_bultos": {
        "nivel": "corregible",
        "accion": "Solicitar aclaración o documento corregido.",
        "regla": "INT-002: la diferencia de bultos entre factura y lista de empaque es corregible.",
        "pregunta": "¿Qué se debe hacer si existen diferencias en cantidades o bultos entre la factura y la lista de empaque?",
        "fuente_esperada": "gestion_observaciones_operacion.md",
    },
    "diferencia_peso": {
        "nivel": "corregible",
        "accion": "Solicitar aclaración o documento corregido.",
        "regla": "INT-001: ante diferencias de peso no se completa la preparación hasta obtener aclaración.",
        "pregunta": "¿Qué se debe hacer si existen diferencias de peso entre los documentos?",
        "fuente_esperada": "procedimiento_recepcion_documentos.md",
    },
    "diferencia_descripcion": {
        "nivel": "corregible",
        "accion": "Solicitar descripción completa y concordante de las mercancías.",
        "regla": "INT-002: la descripción incompleta de las mercancías es corregible.",
        "pregunta": "¿Cómo se clasifica una descripción incompleta de las mercancías?",
        "fuente_esperada": "gestion_observaciones_operacion.md",
    },
    "diferencia_valor": {
        "nivel": "critica",
        "accion": "Escalar al responsable de revisión.",
        "regla": "INT-002: las inconsistencias importantes en el valor declarado son críticas.",
        "pregunta": "¿Cómo se clasifican las inconsistencias importantes en el valor declarado?",
        "fuente_esperada": "gestion_observaciones_operacion.md",
    },
    "importador_inconsistente": {
        "nivel": "critica",
        "accion": "Escalar al responsable de revisión; no completar datos por cuenta propia.",
        "regla": "INT-002: la identificación incorrecta del importador es una observación crítica.",
        "pregunta": "¿Cómo se clasifica la identificación incorrecta del importador o exportador?",
        "fuente_esperada": "gestion_observaciones_operacion.md",
    },
    "operacion_distinta": {
        "nivel": "critica",
        "accion": "Escalar al responsable de revisión.",
        "regla": "INT-002: documentos que corresponden a operaciones diferentes son una observación crítica.",
        "pregunta": "¿Qué ocurre si los documentos corresponden a operaciones diferentes?",
        "fuente_esperada": "gestion_observaciones_operacion.md",
    },
    "documento_ilegible": {
        "nivel": "corregible",
        "accion": "Solicitar una copia legible del documento.",
        "regla": "INT-002: un documento ilegible es una observación corregible.",
        "pregunta": "¿Cómo se clasifica un documento ilegible?",
        "fuente_esperada": "gestion_observaciones_operacion.md",
    },
    "dato_faltante": {
        "nivel": "corregible",
        "accion": "Solicitar el número, fecha o referencia ausente.",
        "regla": "INT-002: la ausencia de una fecha, número o referencia necesaria es corregible.",
        "pregunta": "¿Cómo se clasifica la ausencia de una fecha, número o referencia necesaria?",
        "fuente_esperada": "gestion_observaciones_operacion.md",
    },
    "nomenclatura": {
        "nivel": "informativa",
        "accion": "Registrar la aclaración y renombrar según la convención interna.",
        "regla": "INT-003: los archivos usan la convención TIPO_DOCUMENTO_NUMERO_OPERACION_VERSION.",
        "pregunta": "¿Cuál es la convención de nombres para los documentos de una operación?",
        "fuente_esperada": "trazabilidad_seguridad_documental.md",
    },
    "requisito_no_determinado": {
        "nivel": "critica",
        "accion": "Escalar al responsable para confirmar requisitos de control previo en la fuente oficial.",
        "regla": "INT-003: ante información insuficiente se recomienda revisar la fuente oficial o consultar a una persona responsable.",
        "pregunta": "¿Qué debe hacer el asistente si no existe información suficiente en las fuentes?",
        "fuente_esperada": "trazabilidad_seguridad_documental.md",
    },
    "requisito_por_confirmar": {
        "nivel": "corregible",
        "accion": "Confirmar con el cliente y la fuente oficial si la mercancía requiere control previo.",
        "regla": "EXT-001: algunas mercancías pueden requerir autorización o control previo del organismo competente.",
        "pregunta": "¿Qué mercancías pueden requerir control previo o autorización especial?",
        "fuente_esperada": "aduanas_chile_requisitos_importacion.md",
    },
}

# Estados de operación (INT-001) y de observación (INT-002).
ESTADO_PENDIENTE = "Pendiente de documentación"
ESTADO_CON_OBSERVACIONES = "Con observaciones"
ESTADO_COMPLETA = "Documentación completa"
ESTADO_DERIVADA = "Derivada a revisión"

OBS_ABIERTA = "Abierta"
OBS_ESCALADA = "Escalada"
OBS_CERRADA = "Cerrada"


def clasificar(tipo_hallazgo: str) -> dict:
    """Devuelve nivel, acción y regla para un tipo de hallazgo."""
    regla = CATALOGO_HALLAZGOS.get(tipo_hallazgo)
    if regla is None:
        # Ante un hallazgo desconocido se aplica el criterio conservador:
        # no se resuelve por suposición y se deriva a un responsable.
        return {
            "nivel": "critica",
            "accion": "Escalar al responsable: hallazgo no catalogado.",
            "regla": "INT-002: el ejecutivo no debe resolver por suposiciones.",
        }
    return {k: regla[k] for k in ("nivel", "accion", "regla")}
