"""Planificación y replanificación de tareas del agente.

El plan es una lista de tareas con prioridad numérica (0 = más urgente).
Se ejecuta siempre la tarea pendiente de menor (prioridad, secuencia).
Después de cada tarea, `replanificar` examina el resultado y ajusta el plan:
agrega, omite o reprioriza tareas según las condiciones detectadas. Cada
ajuste queda registrado como una decisión con su condición y regla.
"""

from . import reglas

# Prioridades base (menor número = antes).
P_CRITICA = 0
P_ALTA = 1
P_MEDIA = 2
P_FUNDAMENTO = 3
P_BAJA = 4
P_REGISTRO = 5
P_COMUNICACION = 6
P_APROBACION = 7
P_CIERRE = 9

CLAVES_ANTECEDENTE_RIESGO = {"importador_inconsistente", "operacion_distinta", "diferencia_valor", "permiso_faltante"}


def nueva_tarea(plan: list[dict], accion: str, prioridad: int, motivo: str, **args) -> dict:
    tarea = {
        "id": f"T{len(plan) + 1:02d}",
        "accion": accion,
        "args": args,
        "prioridad": prioridad,
        "secuencia": len(plan),
        "estado": "pendiente",
        "motivo": motivo,
        "intentos": 0,
        "resultado": "",
    }
    plan.append(tarea)
    return tarea


def decision(paso: str, condicion: str, decision_tomada: str, regla: str = "") -> dict:
    return {"paso": paso, "condicion": condicion, "decision": decision_tomada, "regla": regla}


def siguiente_tarea(plan: list[dict]) -> dict | None:
    pendientes = [t for t in plan if t["estado"] == "pendiente"]
    if not pendientes:
        return None
    return min(pendientes, key=lambda t: (t["prioridad"], t["secuencia"]))


def tiene_accion(plan: list[dict], accion: str, solo_pendientes: bool = True) -> dict | None:
    for tarea in plan:
        if tarea["accion"] == accion and (not solo_pendientes or tarea["estado"] == "pendiente"):
            return tarea
    return None


def asegurar_tarea(plan: list[dict], accion: str, prioridad: int, motivo: str, decisiones: list, paso: str, **args):
    """Agrega una tarea o eleva su prioridad si ya estaba pendiente."""
    existente = tiene_accion(plan, accion)
    if existente is None:
        nueva = nueva_tarea(plan, accion, prioridad, motivo, **args)
        decisiones.append(decision(paso, motivo, f"Agregar {nueva['id']} '{accion}' con prioridad {prioridad}"))
    elif prioridad < existente["prioridad"]:
        decisiones.append(decision(paso, motivo,
                                   f"Elevar prioridad de {existente['id']} '{accion}' de {existente['prioridad']} a {prioridad}"))
        existente["prioridad"] = prioridad


# --------------------------------------------------------------------------
# Plan inicial
# --------------------------------------------------------------------------
def crear_plan(expediente: dict, recuerdos: list[dict], observaciones_abiertas: list[dict],
               correccion_pendiente: str | None) -> tuple[list[dict], list[dict]]:
    plan, decisiones = [], []
    op = expediente["operacion_id"]
    categoria = expediente["mercancia"]["categoria"]

    if correccion_pendiente:
        nueva_tarea(plan, "incorporar_correccion", P_CRITICA,
                    "Se informó la llegada de un documento corregido", ruta=correccion_pendiente)
        decisiones.append(decision("planificar", "El usuario informa un documento corregido",
                                   "Incorporarlo como nueva versión antes de revisar", "INT-003: no sobrescribir versiones"))

    if observaciones_abiertas:
        nueva_tarea(plan, "verificar_resolucion", P_ALTA,
                    f"Existen {len(observaciones_abiertas)} observaciones abiertas de una revisión previa")
        decisiones.append(decision("planificar", f"{len(observaciones_abiertas)} observaciones abiertas en el registro",
                                   "Verificar si fueron resueltas antes de continuar", "INT-002: cierre de observaciones"))

    if categoria in reglas.CATEGORIAS_REGULADAS:
        nueva_tarea(plan, "verificar_permisos", P_CRITICA, f"Mercancía regulada ({categoria}): control crítico primero")
        decisiones.append(decision("planificar", f"Categoría '{categoria}' sujeta a control previo",
                                   "Verificar permisos con prioridad 0", "EXT-001: control previo"))
    elif categoria not in reglas.CATEGORIAS_SIN_CONTROL:
        nueva_tarea(plan, "evaluar_requisitos_especiales", P_ALTA,
                    f"Categoría '{categoria}' no catalogada: consultar la base documental")
        decisiones.append(decision("planificar", f"Categoría '{categoria}' desconocida para las reglas",
                                   "Consultar RAG antes de asumir requisitos", "INT-002: no resolver por suposiciones"))
    else:
        decisiones.append(decision("planificar", f"Categoría '{categoria}' sin control previo conocido",
                                   "Omitir verificación de permisos", "EXT-001"))

    riesgos = [r for r in recuerdos if r.get("tipo") in ("antecedente", "episodio")
               and r.get("clave") in CLAVES_ANTECEDENTE_RIESGO]
    if riesgos:
        # El antecedente adelanta la validación de identidad: se planifica
        # antes que la revisión documental, con validación reforzada.
        nueva_tarea(plan, "validar_concordancia", P_ALTA,
                    f"Antecedente recuperado de memoria: {riesgos[0]['texto'][:90]}...", reforzada=True)
        decisiones.append(decision("planificar", f"Memoria de largo plazo: antecedente '{riesgos[0]['clave']}' del cliente",
                                   "Validación de concordancia REFORZADA, adelantada a prioridad 1 y antes de documentos",
                                   "Aprendizaje de episodios previos"))
    nueva_tarea(plan, "verificar_documentos", P_ALTA, "Documentos iniciales requeridos (INT-001)")
    if not riesgos:
        nueva_tarea(plan, "validar_concordancia", P_MEDIA, "Concordancia factura / transporte / lista de empaque (INT-001)",
                    reforzada=False)

    nueva_tarea(plan, "validar_nomenclatura", P_BAJA, "Convención de nombres de archivo (INT-003)")
    nueva_tarea(plan, "actualizar_estado", P_CIERRE, "Toda revisión termina con un estado trazable (INT-001)")

    if expediente.get("urgente"):
        decisiones.append(decision("planificar", "Operación marcada como urgente",
                                   "Asunto [URGENTE] y plazo de 24 horas, salvo preferencia registrada del cliente", "Priorización"))
    return plan, decisiones


# --------------------------------------------------------------------------
# Replanificación después de cada tarea
# --------------------------------------------------------------------------
def replanificar(tarea: dict, resultado: dict, estado: dict) -> tuple[list[dict], list[dict]]:
    plan = estado["plan"]
    decisiones: list[dict] = []
    hallazgos = estado.get("hallazgos", [])
    paso = f"{tarea['id']} {tarea['accion']}"

    if tarea["estado"] == "fallida":
        asegurar_tarea(plan, "escalar", P_CRITICA, f"La tarea {tarea['id']} falló tras reintentos",
                       decisiones, paso, motivo_tecnico=resultado.get("error", ""))
        return plan, decisiones

    nuevos = resultado.get("hallazgos_nuevos", [])
    niveles = {h["nivel"] for h in nuevos}

    if tarea["accion"] == "verificar_resolucion":
        if resultado.get("resueltas"):
            asegurar_tarea(plan, "cerrar_observaciones", P_ALTA,
                           f"{len(resultado['resueltas'])} observaciones ya no se reproducen en el expediente",
                           decisiones, paso, ids=[o["id"] for o in resultado["resueltas"]])
        if not resultado.get("pendientes"):
            decisiones.append(decision(paso, "No quedan observaciones previas vigentes",
                                       "Continuar la revisión para confirmar derivación", "INT-002: cierre"))

    if tarea["accion"] == "validar_concordancia" and not resultado.get("ejecutada", True):
        decisiones.append(decision(paso, resultado.get("motivo", ""), "Omitir concordancia; queda pendiente de documentación"))

    if tarea["accion"] == "evaluar_requisitos_especiales":
        consulta = resultado.get("consulta", {})
        decisiones.append(decision(
            paso, f"RAG {'con' if consulta.get('suficiente') else 'sin'} evidencia suficiente ({consulta.get('motivo')})",
            "Solicitar confirmación al cliente" if consulta.get("suficiente") else "Escalar: no se infieren requisitos",
            "INT-003: respuesta ante información insuficiente"))

    if nuevos:
        asegurar_tarea(plan, "fundamentar", P_FUNDAMENTO, "Hay hallazgos que deben respaldarse en la base documental",
                       decisiones, paso)
        asegurar_tarea(plan, "registrar_observaciones", P_REGISTRO, "Toda inconsistencia debe registrarse (INT-001)",
                       decisiones, paso)

    if "critica" in niveles:
        asegurar_tarea(plan, "registrar_observaciones", P_CRITICA,
                       "Observación crítica detectada: registrar de inmediato", decisiones, paso)
        asegurar_tarea(plan, "escalar", P_CRITICA, "Observación crítica: escalar al responsable (INT-002)",
                       decisiones, paso)
        comunicacion = tiene_accion(plan, "redactar_comunicacion")
        if comunicacion:
            comunicacion["estado"] = "omitida"
            comunicacion["resultado"] = "Suspendida: existe observación crítica escalada"
            decisiones.append(decision(paso, "Existe observación crítica",
                                       "Suspender comunicación al cliente hasta decisión del responsable", "INT-002"))

    criticas = any(h["nivel"] == "critica" for h in hallazgos)
    cliente_debe_actuar = any(h["nivel"] == "corregible" for h in nuevos)
    if cliente_debe_actuar and not criticas and not tiene_accion(plan, "redactar_comunicacion", solo_pendientes=False):
        asegurar_tarea(plan, "redactar_comunicacion", P_COMUNICACION,
                       "Hay antecedentes que el cliente debe aclarar o enviar", decisiones, paso)
        asegurar_tarea(plan, "aprobar_comunicacion", P_APROBACION,
                       "Toda comunicación al cliente requiere aprobación humana", decisiones, paso)

    if tarea["accion"] == "fundamentar":
        sin_respaldo = [f for f in resultado.get("fundamentos", []) if not f["respaldado"]]
        if sin_respaldo:
            asegurar_tarea(plan, "escalar", P_CRITICA,
                           f"{len(sin_respaldo)} hallazgos sin respaldo documental suficiente", decisiones, paso)

    if tarea["accion"] == "aprobar_comunicacion" and resultado.get("decision") == "rechazar":
        decisiones.append(decision(paso, "El ejecutivo rechazó el borrador",
                                   "No enviar; mantener la operación con observaciones para gestión manual"))

    return plan, decisiones


def determinar_estado_final(hallazgos: list[dict], observaciones_abiertas: list[dict]) -> tuple[str, str]:
    """Regla de estado de la operación (INT-001)."""
    abiertos = [h for h in hallazgos if h.get("estado_obs") != reglas.OBS_CERRADA]
    if any(h["tipo"] == "documento_faltante" for h in abiertos):
        return reglas.ESTADO_PENDIENTE, "Faltan uno o más antecedentes obligatorios"
    if any(h["nivel"] in ("critica", "corregible") for h in abiertos) or any(
            o["nivel"] in ("critica", "corregible") for o in observaciones_abiertas):
        return reglas.ESTADO_CON_OBSERVACIONES, "Existen inconsistencias que deben corregirse o revisarse"
    return reglas.ESTADO_DERIVADA, "Antecedentes validados inicialmente; solo observaciones informativas o ninguna"
