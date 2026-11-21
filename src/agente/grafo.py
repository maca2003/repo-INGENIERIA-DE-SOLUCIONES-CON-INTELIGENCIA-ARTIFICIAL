"""Orquestación del agente con LangGraph.

Flujo general (ver documentacion/diagramas):

    START -> gestionar_memoria_corta -> recuperar_contexto -> enrutar
        enrutar = "revision"     -> planificar -> [ejecutar_tarea -> evaluar]* -> sintetizar
                                    (pausa en aprobacion_humana si hay comunicación al cliente)
        enrutar = "conversacion" -> agente_conversacional (ReAct con herramientas)
        enrutar = "cola"         -> priorizar_cola
    -> consolidar_memoria -> END
"""

import copy
import operator
import re
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, RemoveMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

from . import config as ajustes
from . import reglas
from .almacen import ahora
from .herramientas import HERRAMIENTAS_CONVERSACION, POR_NOMBRE
from .planificador import (
    crear_plan,
    decision,
    determinar_estado_final,
    replanificar,
    siguiente_tarea,
)
from .prompts import PROMPT_COMPACTACION, PROMPT_CONVERSACIONAL, PROMPT_SINTESIS
from .seguridad import MENSAJE_BLOQUEO, enmascarar, validar_entrada
from .servicios import obtener_servicios

PATRON_OPERACION = re.compile(r"\bOP\s?-?(\d{4})\b", re.IGNORECASE)
VERBOS_REVISION = ("revisa", "revisar", "revisión", "revision", "procesa", "procesar", "analiza", "analizar",
                   "reprocesa", "evalúa", "evalua", "valida", "validar")
PALABRAS_CORRECCION = ("corregid", "corrección", "correccion", "llegó", "llego", "nueva versión", "nueva version")
# Ruta directa (EP3): intenciones inequívocas que no necesitan que el LLM elija
# herramientas (ReAct). Ahorra una o dos llamadas al modelo por consulta.
PALABRAS_MEMORIA = ("recuerda", "preferencia", "prefiere", "historial")
PALABRAS_LISTADO = ("quedaron", "quedan", "tiene", "tienen", "registrad", "pendiente", "abierta", "hay ")
PISTAS_PREGUNTA = ("?", "¿", "qué ", "que ", "cómo", "como ", "cuándo", "cuando", "cuál", "cual", "debe",
                   "puede", "procedimiento", "requisit", "clasifica", "función", "diferencia")
PALABRAS_COLA = ("prioriza", "priorizar", "cola", "jornada", "qué reviso primero", "que reviso primero", "orden de revisión")


class EstadoAgente(TypedDict, total=False):
    # Memoria de corto plazo (persistida por el checkpointer en cada hilo)
    messages: Annotated[list[AnyMessage], add_messages]
    resumen_conversacion: str
    operacion_activa: str
    # Contexto de la solicitud actual
    intencion: str
    operacion_id: str
    expediente: dict
    recuerdos: list[dict]
    correccion: str
    # Planificación y ejecución
    plan: list[dict]
    hallazgos: list[dict]
    fundamentos: list[dict]
    comunicacion: dict
    decisiones: list[dict]
    bitacora: Annotated[list[dict], operator.add]
    estado_final: dict
    pasos: int
    ultima_tarea: str
    ultimo_resultado: dict


# --------------------------------------------------------------------------
# Nodos de memoria y contexto
# --------------------------------------------------------------------------
def gestionar_memoria_corta(estado: EstadoAgente) -> dict:
    """Compacta el hilo cuando supera el límite de mensajes."""
    mensajes = estado.get("messages", [])
    if len(mensajes) <= ajustes.MAX_MENSAJES_HILO:
        return {}
    corte = len(mensajes) - ajustes.MENSAJES_CONSERVADOS
    while corte > 0 and not isinstance(mensajes[corte], HumanMessage):
        corte -= 1  # no separar llamadas a herramientas de sus respuestas
    antiguos = mensajes[:corte]
    if not antiguos:
        return {}
    texto = "\n".join(f"{m.type}: {m.text[:300]}" for m in antiguos if m.text)
    try:
        resumen = obtener_servicios().llm.invoke(
            [SystemMessage(content=PROMPT_COMPACTACION), HumanMessage(content=texto)]
        ).text
    except Exception:  # degradación: resumen extractivo
        resumen = texto[-800:]
    previo = estado.get("resumen_conversacion", "")
    return {
        "messages": [RemoveMessage(id=m.id) for m in antiguos],
        "resumen_conversacion": (previo + "\n" + resumen).strip()[-2000:],
        "bitacora": [{"nodo": "gestionar_memoria_corta", "detalle": f"{len(antiguos)} mensajes compactados en el resumen"}],
    }


def _ultimo_texto_humano(estado: EstadoAgente) -> str:
    for mensaje in reversed(estado.get("messages", [])):
        if isinstance(mensaje, HumanMessage):
            return mensaje.text
    return ""


def _es_memoria(bajo: str) -> bool:
    return any(p in bajo for p in PALABRAS_MEMORIA) or (
        "antecedente" in bajo and any(c in bajo for c in ("cliente", "ltda", "spa")))


def clasificar_intencion(texto: str, operacion: str, operacion_activa: str) -> str:
    """Enrutamiento determinista: solo lo ambiguo pasa al agente ReAct."""
    bajo = texto.lower()
    if operacion and any(v in bajo for v in VERBOS_REVISION + PALABRAS_CORRECCION):
        return "revision"
    if any(p in bajo for p in PALABRAS_COLA):
        return "cola"
    if ajustes.OPTIMIZADO and not _es_memoria(bajo):
        if "observaci" in bajo and any(p in bajo for p in PALABRAS_LISTADO) and (operacion or operacion_activa):
            return "listado"
        if not operacion and any(p in bajo for p in PISTAS_PREGUNTA):
            return "consulta"
    return "conversacion"


def recuperar_contexto(estado: EstadoAgente) -> dict:
    servicios = obtener_servicios()
    texto = _ultimo_texto_humano(estado)
    permitida, motivo = validar_entrada(texto)
    if not permitida:
        # Guardarraíl: la entrada no llega al LLM ni a las herramientas.
        return {"intencion": "bloqueada", "operacion_id": "", "expediente": {}, "recuerdos": [], "correccion": "",
                "bitacora": [{"nodo": "recuperar_contexto", "detalle": f"Entrada bloqueada: {motivo}"}]}
    bajo = texto.lower()
    coincidencia = PATRON_OPERACION.search(texto)
    operacion = f"OP{coincidencia.group(1)}" if coincidencia else ""
    intencion = clasificar_intencion(texto, operacion, estado.get("operacion_activa", ""))

    correccion = ""
    if intencion == "revision" and any(p in bajo for p in PALABRAS_CORRECCION):
        candidatas = sorted((servicios.rutas.operaciones / "correcciones").glob(f"{operacion}_*.json"))
        if candidatas:
            correccion = str(candidatas[-1])

    if intencion == "revision" and servicios.almacen.obtener_expediente(operacion) is None:
        # Operación inexistente: se responde de forma determinista, sin LLM.
        return {
            "intencion": "inexistente", "operacion_id": operacion, "expediente": {}, "recuerdos": [],
            "correccion": "",
            "bitacora": [{"nodo": "recuperar_contexto", "detalle": f"La operación {operacion} no existe"}],
        }

    operacion_contexto = operacion or estado.get("operacion_activa", "")
    expediente = servicios.almacen.obtener_expediente(operacion_contexto) if operacion_contexto else None

    if intencion in ("consulta", "listado"):
        recuerdos = []  # una pregunta de procedimiento no necesita la memoria del cliente
    elif expediente:
        consulta = (f"{expediente['cliente']} antecedentes observaciones preferencias comunicaciones "
                    f"{expediente['mercancia']['descripcion']}")
        recuerdos = servicios.memoria.recordar(consulta, cliente=expediente["cliente"])
    else:
        recuerdos = servicios.memoria.recordar(texto) if texto else []

    detalle = (f"Intención '{intencion}'" + (f", operación {operacion_contexto}" if operacion_contexto else "")
               + f", {len(recuerdos)} recuerdos de largo plazo recuperados")
    return {
        "intencion": intencion,
        "operacion_id": operacion_contexto,
        "operacion_activa": operacion_contexto or estado.get("operacion_activa", ""),
        "expediente": expediente or {},
        "recuerdos": recuerdos,
        "correccion": correccion,
        "bitacora": [{"nodo": "recuperar_contexto", "detalle": detalle}],
    }


def enrutar(estado: EstadoAgente) -> str:
    return estado["intencion"]


# --------------------------------------------------------------------------
# Flujo de revisión: planificar -> ejecutar -> evaluar
# --------------------------------------------------------------------------
def planificar(estado: EstadoAgente) -> dict:
    servicios = obtener_servicios()
    expediente = estado["expediente"]
    abiertas = [o for o in servicios.almacen.observaciones(expediente["operacion_id"])
                if o["estado"] != reglas.OBS_CERRADA]
    plan, decisiones = crear_plan(expediente, estado.get("recuerdos", []), abiertas, estado.get("correccion") or None)
    servicios.almacen.trazar(expediente["operacion_id"], "Inicia revisión del agente", "-",
                             f"Plan de {len(plan)} tareas", "; ".join(t["accion"] for t in plan))
    return {
        "plan": plan, "decisiones": decisiones, "hallazgos": [], "fundamentos": [], "comunicacion": {},
        "estado_final": {}, "pasos": 0,
        "bitacora": [{"nodo": "planificar", "detalle": f"Plan inicial con {len(plan)} tareas"}],
    }


def seleccionar(estado: EstadoAgente) -> str:
    if estado.get("pasos", 0) >= ajustes.MAX_PASOS_FLUJO:
        return "sintetizar"
    tarea = siguiente_tarea(estado["plan"])
    if tarea is None:
        return "sintetizar"
    if tarea["accion"] == "aprobar_comunicacion":
        return "aprobacion_humana"
    return "ejecutar_tarea"


def _preferencia(recuerdos: list[dict], clave: str) -> str:
    for recuerdo in recuerdos:
        if recuerdo.get("tipo") == "preferencia" and recuerdo.get("clave") == clave:
            return recuerdo.get("valor", "")
    return ""


def _agregar_hallazgos(existentes: list[dict], nuevos: list[dict]) -> list[dict]:
    claves = {h["clave"] for h in existentes}
    agregados = [h for h in nuevos if h["clave"] not in claves]
    existentes.extend(agregados)
    return agregados


def _ejecutar(tarea: dict, estado: EstadoAgente) -> dict:
    """Despacha cada acción del plan a su herramienta LangChain."""
    servicios = obtener_servicios()
    op = estado["operacion_id"]
    hallazgos = estado["hallazgos"]
    accion = tarea["accion"]

    if accion == "incorporar_correccion":
        resultado = POR_NOMBRE["recibir_documento_corregido"].invoke({"ruta_correccion": tarea["args"]["ruta"]})
        estado["expediente"] = servicios.almacen.obtener_expediente(op)
        return {**resultado, "resumen": f"Nueva versión {resultado['version_nueva']} incorporada"}

    if accion == "verificar_resolucion":
        resultado = POR_NOMBRE["verificar_resolucion_observaciones"].invoke({"operacion_id": op})
        return {**resultado, "resumen": f"{len(resultado['resueltas'])} resueltas, {len(resultado['pendientes'])} vigentes"}

    if accion == "cerrar_observaciones":
        for id_obs in tarea["args"]["ids"]:
            POR_NOMBRE["cerrar_observacion"].invoke({
                "id_observacion": id_obs,
                "resolucion": "Verificado por el agente: la inconsistencia no se reproduce en la versión vigente.",
            })
        return {"resumen": f"Cerradas: {', '.join(tarea['args']['ids'])}"}

    herramientas_analisis = {
        "verificar_permisos": ("verificar_permisos", {"operacion_id": op}),
        "evaluar_requisitos_especiales": ("evaluar_requisitos_especiales", {"operacion_id": op}),
        "verificar_documentos": ("verificar_documentos_requeridos", {"operacion_id": op}),
        "validar_concordancia": ("validar_concordancia", {"operacion_id": op, "reforzada": tarea["args"].get("reforzada", False)}),
        "validar_nomenclatura": ("validar_nomenclatura", {"operacion_id": op}),
    }
    if accion in herramientas_analisis:
        nombre, argumentos = herramientas_analisis[accion]
        resultado = POR_NOMBRE[nombre].invoke(argumentos)
        nuevos = _agregar_hallazgos(hallazgos, resultado.get("hallazgos", []))
        niveles = ", ".join(f"{h['tipo']}({h['nivel']})" for h in nuevos) or "sin hallazgos"
        return {**resultado, "hallazgos_nuevos": nuevos, "resumen": f"{nombre}: {niveles}"}

    if accion == "fundamentar":
        ya = {f["tipo"] for f in estado["fundamentos"]}
        tipos = [h["tipo"] for h in hallazgos if h["tipo"] not in ya]
        fundamentos = POR_NOMBRE["fundamentar_hallazgos"].invoke({"tipos": tipos}) if tipos else []
        estado["fundamentos"].extend(fundamentos)
        respaldados = sum(f["respaldado"] for f in fundamentos)
        return {"fundamentos": fundamentos, "resumen": f"{respaldados}/{len(fundamentos)} hallazgos con respaldo documental"}

    if accion == "registrar_observaciones":
        registradas = []
        for h in hallazgos:
            if h.get("id_observacion"):
                continue
            obs = POR_NOMBRE["registrar_observacion"].invoke({
                "operacion_id": op, "tipo": h["tipo"], "documento": h["documento"], "descripcion": h["descripcion"],
                "clave": h["clave"],
            })
            h["id_observacion"] = obs["id"]
            registradas.append(obs["id"])
        return {"registradas": registradas, "resumen": f"Observaciones registradas: {', '.join(registradas) or 'ninguna nueva'}"}

    if accion == "escalar":
        criticas = [h for h in hallazgos if h["nivel"] == "critica" and h.get("id_observacion") and not h.get("escalada")]
        motivo = tarea["motivo"] + (f" ({tarea['args']['motivo_tecnico']})" if tarea["args"].get("motivo_tecnico") else "")
        if any(h.get("reincidencia") for h in criticas):
            motivo += ". Cliente reincidente: antecedente del mismo tipo en la memoria de largo plazo"
        resultado = POR_NOMBRE["escalar_a_responsable"].invoke({
            "operacion_id": op, "motivo": motivo, "ids_observaciones": [h["id_observacion"] for h in criticas],
        })
        for h in criticas:
            h["escalada"] = True
        return {**resultado, "resumen": f"Escalamiento generado ({len(criticas)} observaciones)"}

    if accion == "redactar_comunicacion":
        para_cliente = [h for h in hallazgos if h["nivel"] == "corregible"]
        destinatario = _preferencia(estado.get("recuerdos", []), "contacto_comunicaciones")
        urgente = bool(estado["expediente"].get("urgente"))
        plazo = "48 horas" if "48 horas" in destinatario else ("24 horas" if urgente else "5 días hábiles")
        resultado = POR_NOMBRE["redactar_comunicacion_cliente"].invoke({
            "operacion_id": op, "observaciones": para_cliente,
            "destinatario": destinatario.split(";")[0].strip() if destinatario else "",
            "plazo_respuesta": plazo, "urgente": urgente,
        })
        estado["comunicacion"] = resultado
        if destinatario:
            estado["decisiones"].append(decision(
                f"{tarea['id']} redactar_comunicacion", f"Preferencia del cliente recuperada de memoria: {destinatario}",
                f"Dirigir la comunicación a ese contacto y usar plazo {plazo}", "Memoria de largo plazo prevalece"))
        fuente = "preferencia recuperada de memoria" if destinatario else "sin preferencia registrada"
        return {**resultado, "destinatario_desde_memoria": bool(destinatario),
                "resumen": f"Borrador con {len(para_cliente)} puntos ({fuente}); plazo {plazo}"}

    if accion == "actualizar_estado":
        abiertas = [o for o in servicios.almacen.observaciones(op) if o["estado"] != reglas.OBS_CERRADA]
        estado_op, motivo = determinar_estado_final(hallazgos, abiertas)
        if estado_op == reglas.ESTADO_DERIVADA:
            POR_NOMBRE["actualizar_estado_operacion"].invoke(
                {"operacion_id": op, "estado": reglas.ESTADO_COMPLETA, "motivo": "Antecedentes completos y concordantes"})
        registro = POR_NOMBRE["actualizar_estado_operacion"].invoke(
            {"operacion_id": op, "estado": estado_op, "motivo": motivo})
        estado["estado_final"] = registro
        return {**registro, "resumen": f"Estado final: {estado_op}"}

    raise ValueError(f"Acción desconocida: {accion}")


def ejecutar_tarea(estado: EstadoAgente) -> dict:
    trabajo = copy.deepcopy(dict(estado))
    tarea = siguiente_tarea(trabajo["plan"])
    tarea["intentos"] += 1
    try:
        resultado = _ejecutar(tarea, trabajo)
        tarea["estado"] = "completada"
        tarea["resultado"] = resultado.get("resumen", "")
        tarea["orden_ejecucion"] = trabajo.get("pasos", 0) + 1
    except Exception as error:  # condición cambiante: falla de herramienta o modelo
        resultado = {"error": f"{type(error).__name__}: {error}"}
        if tarea["intentos"] <= ajustes.MAX_REINTENTOS_HERRAMIENTA:
            tarea["resultado"] = f"Error, se reintentará: {resultado['error']}"
            trabajo["decisiones"].append(decision(f"{tarea['id']} {tarea['accion']}", resultado["error"],
                                                  "Reintentar la tarea", "Tolerancia a fallos"))
        else:
            tarea["estado"] = "fallida"
            tarea["resultado"] = resultado["error"]
    return {
        "plan": trabajo["plan"], "hallazgos": trabajo["hallazgos"], "fundamentos": trabajo["fundamentos"],
        "comunicacion": trabajo["comunicacion"], "expediente": trabajo["expediente"],
        "estado_final": trabajo["estado_final"], "decisiones": trabajo["decisiones"],
        "pasos": trabajo.get("pasos", 0) + 1,
        "ultima_tarea": tarea["id"], "ultimo_resultado": resultado,
        "bitacora": [{"nodo": "ejecutar_tarea", "tarea": tarea["id"], "accion": tarea["accion"],
                      "detalle": tarea["resultado"]}],
    }


def evaluar(estado: EstadoAgente) -> dict:
    """Examina el último resultado y replanifica."""
    trabajo = copy.deepcopy(dict(estado))
    tarea = next(t for t in trabajo["plan"] if t["id"] == estado["ultima_tarea"])
    if tarea["estado"] == "pendiente":  # reintento programado
        return {"bitacora": [{"nodo": "evaluar", "detalle": f"{tarea['id']} se reintentará"}]}
    plan, nuevas = replanificar(tarea, estado.get("ultimo_resultado", {}), trabajo)
    return {
        "plan": plan,
        "decisiones": trabajo["decisiones"] + nuevas,
        "bitacora": [{"nodo": "evaluar", "detalle": f"{len(nuevas)} ajustes al plan" if nuevas else "Plan sin cambios"}],
    }


def aprobacion_humana(estado: EstadoAgente, config: RunnableConfig) -> dict:
    """Human-in-the-loop: pausa el grafo hasta que el ejecutivo apruebe el borrador.

    El estado queda guardado en el checkpointer, por lo que la aprobación puede
    llegar minutos u horas después, desde otra sesión, usando el mismo thread_id.
    """
    servicios = obtener_servicios()
    plan = copy.deepcopy(estado["plan"])
    tarea = siguiente_tarea(plan)
    automatica = config.get("configurable", {}).get("aprobacion_automatica", False)
    if automatica:
        respuesta = "aprobar"
    else:
        respuesta = interrupt({
            "tipo": "aprobacion_comunicacion",
            "operacion_id": estado["operacion_id"],
            "borrador": estado.get("comunicacion", {}).get("texto", ""),
            "pregunta": "¿Apruebas el envío de esta comunicación al cliente? (aprobar / rechazar)",
        })
    respuesta = str(respuesta).strip().lower()
    aprobada = respuesta.startswith(("a", "s", "y"))
    tarea["estado"] = "completada"
    tarea["orden_ejecucion"] = estado.get("pasos", 0) + 1
    tarea["resultado"] = "Aprobada" + (" (automática, modo lote)" if automatica else " por el ejecutivo") if aprobada else "Rechazada por el ejecutivo"
    ruta = estado.get("comunicacion", {}).get("ruta", "-")
    servicios.almacen.trazar(estado["operacion_id"], "Aprobación de comunicación", Path(ruta).name,
                             "Aprobada para envío" if aprobada else "Rechazada", respuesta)
    decisiones = list(estado["decisiones"])
    decisiones.append(decision(f"{tarea['id']} aprobar_comunicacion", "Borrador listo para el cliente",
                               "Enviar (aprobada)" if aprobada else "No enviar (rechazada)",
                               "Supervisión humana obligatoria"))
    return {
        "plan": plan, "decisiones": decisiones, "pasos": estado.get("pasos", 0) + 1,
        "comunicacion": {**estado.get("comunicacion", {}), "estado": "aprobada" if aprobada else "rechazada"},
        "bitacora": [{"nodo": "aprobacion_humana", "tarea": tarea["id"], "detalle": tarea["resultado"]}],
    }


def _informe_markdown(estado: EstadoAgente) -> str:
    exp = estado["expediente"]
    lineas = [
        f"# Informe de revisión {estado['operacion_id']}", "",
        f"- Cliente: {exp['cliente']}", f"- Mercancía: {exp['mercancia']['descripcion']}",
        f"- Fecha: {ahora()}", f"- Modo de ejecución: {obtener_servicios().modo}",
        f"- Estado final: **{estado.get('estado_final', {}).get('estado', 'sin estado')}**", "",
        "## Recuerdos de largo plazo utilizados", "",
    ]
    lineas += [f"- [{r['tipo']}] {r['texto']} (distancia {r['distancia']})" for r in estado.get("recuerdos", [])] or ["- Ninguno"]
    lineas += ["", "## Plan ejecutado", "", "| Orden | Tarea | Acción | Prioridad | Estado | Motivo | Resultado |",
               "|---:|---|---|---:|---|---|---|"]
    for t in sorted(estado["plan"], key=lambda t: (t.get("orden_ejecucion") or 99, t["secuencia"])):
        lineas.append(f"| {t.get('orden_ejecucion') or '-'} | {t['id']} | {t['accion']} | {t['prioridad']} | "
                      f"{t['estado']} | {t['motivo']} | {t['resultado']} |")
    lineas += ["", "## Hallazgos", "", "| Nivel | Tipo | Documento | Descripción | Observación |", "|---|---|---|---|---|"]
    for h in estado["hallazgos"]:
        lineas.append(f"| {h['nivel']} | {h['tipo']} | {h['documento']} | {h['descripcion']} | {h.get('id_observacion', '-')} |")
    if not estado["hallazgos"]:
        lineas.append("| - | - | - | Sin hallazgos | - |")
    lineas += ["", "## Fundamento documental (RAG)", ""]
    lineas += [f"- {f['tipo']}: {f.get('fuente_recuperada')} (distancia {f.get('distancia')}, "
               f"respaldado={f['respaldado']})" for f in estado.get("fundamentos", [])] or ["- No requerido"]
    lineas += ["", "## Decisiones del agente", "", "| Paso | Condición | Decisión | Regla |", "|---|---|---|---|"]
    for d in estado["decisiones"]:
        lineas.append(f"| {d['paso']} | {d['condicion']} | {d['decision']} | {d['regla']} |")
    return "\n".join(lineas)


def _ruta_visible(ruta: Path, raiz: Path) -> str:
    try:
        return ruta.relative_to(raiz).as_posix()
    except ValueError:
        return str(ruta)


def _resumen_estructurado(estado: EstadoAgente) -> str:
    hallazgos = estado.get("hallazgos", [])
    por_nivel = {n: sum(1 for h in hallazgos if h["nivel"] == n) for n in ("critica", "corregible", "informativa")}
    lineas = [f"{len(hallazgos)} hallazgos: {por_nivel['critica']} críticos, {por_nivel['corregible']} corregibles "
              f"y {por_nivel['informativa']} informativos."]
    lineas += [f"- [{h['nivel']}] {h['descripcion']}" for h in hallazgos[:6]]
    acciones = {t["accion"] for t in estado.get("plan", []) if t["estado"] == "completada"}
    if "escalar" in acciones:
        lineas.append("Se escaló al responsable de revisión; no se redactó comunicación al cliente.")
    comunicacion = estado.get("comunicacion", {}).get("estado")
    if comunicacion:
        lineas.append(f"Comunicación al cliente: {comunicacion}.")
    if "cerrar_observaciones" in acciones:
        lineas.append("Se cerraron las observaciones que ya no se reproducen.")
    return "\n".join(lineas)


def sintetizar(estado: EstadoAgente) -> dict:
    servicios = obtener_servicios()
    informe = _informe_markdown(estado)
    ruta = servicios.rutas.carpeta_operacion(estado["operacion_id"]) / "informe_revision.md"
    estado_op = estado.get("estado_final", {}).get("estado", "sin estado")
    datos = (f"Operación {estado['operacion_id']} – estado final: {estado_op}.\n"
             + "\n".join(f"- [{h['nivel']}] {h['descripcion']}" for h in estado["hallazgos"])
             + "\nDecisiones: " + "; ".join(d["decision"] for d in estado["decisiones"][-6:]))
    if ajustes.OPTIMIZADO:
        # EP3: el resumen se arma con los datos estructurados. Elimina una llamada
        # al LLM por revisión y evita imprecisiones observadas en los registros.
        resumen, nota = _resumen_estructurado(estado), "Resumen estructurado (sin LLM)"
    else:
        try:
            resumen = servicios.llm.invoke([SystemMessage(content=PROMPT_SINTESIS), HumanMessage(content=datos)]).text
            nota = ""
        except Exception as error:  # el modelo no responde: se entrega el resumen estructurado
            resumen = datos
            nota = f"Síntesis en modo degradado ({type(error).__name__})"
    informe += "\n\n## Resumen del agente\n\n" + resumen
    ruta.write_text(informe, encoding="utf-8")
    respuesta = (f"**Revisión {estado['operacion_id']} – {estado_op}**\n\n{resumen}\n\n"
                 f"Informe: {_ruta_visible(ruta, servicios.rutas.raiz)}")
    bitacora = [{"nodo": "sintetizar", "detalle": nota or "Informe generado"}]
    return {"messages": [AIMessage(content=respuesta)], "bitacora": bitacora}


# --------------------------------------------------------------------------
# Modo conversacional y cola de trabajo
# --------------------------------------------------------------------------
def agente_conversacional(estado: EstadoAgente) -> dict:
    servicios = obtener_servicios()
    contexto = []
    if estado.get("resumen_conversacion"):
        contexto.append(f"Resumen de la conversación previa:\n{estado['resumen_conversacion']}")
    if estado.get("operacion_activa"):
        contexto.append(f"Operación activa en esta conversación: {estado['operacion_activa']}")
    if estado.get("recuerdos"):
        contexto.append("Recuerdos relevantes:\n" + "\n".join(f"- {r['texto']}" for r in estado["recuerdos"][:3]))
    sistema = PROMPT_CONVERSACIONAL.format(contexto="\n\n" + "\n\n".join(contexto) if contexto else "")
    agente = create_agent(servicios.llm, tools=HERRAMIENTAS_CONVERSACION, system_prompt=sistema)
    entrada = list(estado["messages"])
    resultado = agente.invoke({"messages": entrada}, {"recursion_limit": 12})
    nuevos = resultado["messages"][len(entrada):]
    usadas = [tc["name"] for m in nuevos if isinstance(m, AIMessage) for tc in (m.tool_calls or [])]
    return {
        "messages": nuevos,
        "bitacora": [{"nodo": "agente_conversacional",
                      "detalle": f"Herramientas elegidas por el modelo: {', '.join(usadas) or 'ninguna'}"}],
    }


def respuesta_directa(estado: EstadoAgente) -> dict:
    """Ruta directa (EP3): ejecuta la única herramienta necesaria sin pasar por ReAct."""
    texto = _ultimo_texto_humano(estado)
    if estado["intencion"] == "listado":
        op = estado["operacion_id"]
        observaciones = POR_NOMBRE["listar_observaciones"].invoke({"operacion_id": op})
        if observaciones:
            lineas = [f"Observaciones registradas de la {op}:"]
            lineas += [f"- {o['id']} [{o['nivel']} · {o['estado']}] {o['descripcion']}" for o in observaciones]
            respuesta = "\n".join(lineas)
        else:
            respuesta = f"La {op} no tiene observaciones registradas."
        herramienta = "listar_observaciones"
    else:
        resultado = POR_NOMBRE["consultar_procedimientos"].invoke({"pregunta": texto})
        respuesta = resultado["respuesta"]
        if resultado["suficiente"]:
            fuentes = list(dict.fromkeys(f["fuente"] for f in resultado["fuentes"]))[:2]
            respuesta += "\n\nFuentes: " + ", ".join(fuentes)
        herramienta = "consultar_procedimientos"
    return {"messages": [AIMessage(content=respuesta)],
            "bitacora": [{"nodo": "respuesta_directa", "detalle": f"Ruta directa (sin ReAct): {herramienta}"}]}


def entrada_bloqueada(estado: EstadoAgente) -> dict:
    motivo = estado["bitacora"][-1]["detalle"].replace("Entrada bloqueada: ", "")
    from .observabilidad import obtener_observador
    observador = obtener_observador()
    if observador is not None:
        observador.registrar("seguridad", "guardarrail_entrada", estado="bloqueada", motivo=motivo,
                             entrada=enmascarar(_ultimo_texto_humano(estado))[:200])
    return {"messages": [AIMessage(content=MENSAJE_BLOQUEO.format(motivo=motivo))],
            "bitacora": [{"nodo": "entrada_bloqueada", "detalle": motivo}]}


def operacion_inexistente(estado: EstadoAgente) -> dict:
    disponibles = ", ".join(obtener_servicios().almacen.listar_operaciones())
    texto = (f"No existe la operación {estado['operacion_id']} en la bandeja de expedientes. "
             f"Operaciones disponibles: {disponibles}.")
    return {"messages": [AIMessage(content=texto)],
            "bitacora": [{"nodo": "operacion_inexistente", "detalle": texto}]}


def priorizar_cola(estado: EstadoAgente) -> dict:
    cola = POR_NOMBRE["priorizar_operaciones"].invoke({})
    lineas = ["**Orden recomendado de revisión**", ""]
    lineas += [f"{o['orden']}. {o['operacion_id']} ({o['cliente']}) – puntaje {o['puntaje']}: "
               f"{', '.join(o['motivos']) or 'sin factores de urgencia'}" for o in cola]
    return {"messages": [AIMessage(content="\n".join(lineas))],
            "bitacora": [{"nodo": "priorizar_cola", "detalle": f"{len(cola)} operaciones ordenadas", "cola": cola}]}


def consolidar_memoria(estado: EstadoAgente) -> dict:
    """Escribe en la memoria de largo plazo el episodio de cada revisión."""
    if estado.get("intencion") != "revision" or not estado.get("estado_final"):
        return {}
    servicios = obtener_servicios()
    exp = estado["expediente"]
    criticos = sorted({h["tipo"] for h in estado["hallazgos"] if h["nivel"] == "critica"})
    tipos = sorted({h["tipo"] for h in estado["hallazgos"]})
    texto = (f"Episodio {estado['operacion_id']} de {exp['cliente']} ({ahora()[:10]}): estado "
             f"{estado['estado_final']['estado']}; hallazgos: {', '.join(tipos) or 'ninguno'}.")
    servicios.memoria.guardar(
        texto=texto, tipo="antecedente" if criticos else "episodio", cliente=exp["cliente"],
        operacion_id=estado["operacion_id"], clave=criticos[0] if criticos else "", valor=", ".join(tipos),
    )
    return {"bitacora": [{"nodo": "consolidar_memoria", "detalle": f"Episodio guardado: {texto}"}]}


# --------------------------------------------------------------------------
# Construcción del grafo
# --------------------------------------------------------------------------
def construir_grafo(checkpointer=None):
    grafo = StateGraph(EstadoAgente)
    grafo.add_node("gestionar_memoria_corta", gestionar_memoria_corta)
    grafo.add_node("recuperar_contexto", recuperar_contexto)
    grafo.add_node("planificar", planificar)
    grafo.add_node("ejecutar_tarea", ejecutar_tarea)
    grafo.add_node("evaluar", evaluar)
    grafo.add_node("aprobacion_humana", aprobacion_humana)
    grafo.add_node("sintetizar", sintetizar)
    grafo.add_node("agente_conversacional", agente_conversacional)
    grafo.add_node("priorizar_cola", priorizar_cola)
    grafo.add_node("operacion_inexistente", operacion_inexistente)
    grafo.add_node("respuesta_directa", respuesta_directa)
    grafo.add_node("entrada_bloqueada", entrada_bloqueada)
    grafo.add_node("consolidar_memoria", consolidar_memoria)

    grafo.add_edge(START, "gestionar_memoria_corta")
    grafo.add_edge("gestionar_memoria_corta", "recuperar_contexto")
    grafo.add_conditional_edges("recuperar_contexto", enrutar, {
        "revision": "planificar", "conversacion": "agente_conversacional", "cola": "priorizar_cola",
        "inexistente": "operacion_inexistente",
        "consulta": "respuesta_directa", "listado": "respuesta_directa", "bloqueada": "entrada_bloqueada",
    })
    destinos = {"ejecutar_tarea": "ejecutar_tarea", "aprobacion_humana": "aprobacion_humana", "sintetizar": "sintetizar"}
    grafo.add_conditional_edges("planificar", seleccionar, destinos)
    grafo.add_edge("ejecutar_tarea", "evaluar")
    grafo.add_conditional_edges("evaluar", seleccionar, destinos)
    grafo.add_conditional_edges("aprobacion_humana", seleccionar, destinos)
    grafo.add_edge("sintetizar", "consolidar_memoria")
    grafo.add_edge("agente_conversacional", "consolidar_memoria")
    grafo.add_edge("priorizar_cola", "consolidar_memoria")
    grafo.add_edge("operacion_inexistente", END)
    grafo.add_edge("respuesta_directa", END)
    grafo.add_edge("entrada_bloqueada", END)
    grafo.add_edge("consolidar_memoria", END)
    return grafo.compile(checkpointer=checkpointer)
