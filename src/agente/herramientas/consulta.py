"""Herramientas de CONSULTA: leen información sin modificarla."""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from .. import config
from ..servicios import obtener_servicios

# Prompt RAG heredado de la EP1 (consultar_rag.py), validado con 10/10 casos.
PROMPT_RAG = ChatPromptTemplate.from_messages([
    ("system", """
Eres AduanaRAG, un asistente de consulta documental aduanera.

Reglas obligatorias:
1. Responde únicamente con información incluida en el contexto.
2. No inventes información ni uses conocimiento externo.
3. Identifica la sección del contexto que responda de manera más directa la pregunta.
4. Respeta estrictamente las negaciones del contexto. Nunca elimines ni cambies palabras como "no", "nunca", "solo" o "hasta".
5. Si el contexto no permite responder con seguridad, responde exactamente:
   "No existe información suficiente en las fuentes disponibles para responder con seguridad."
6. Entrega una respuesta clara, breve y en español.
7. No presentes la respuesta como asesoría legal definitiva.

Contexto:
{contexto}
"""),
    ("human", "{pregunta}"),
])


def recuperar_con_umbral(pregunta: str, k: int = config.FRAGMENTOS_RAG) -> tuple[list, list]:
    """Devuelve (todos los fragmentos, fragmentos bajo el umbral de distancia)."""
    resultados = obtener_servicios().recuperador(pregunta, k)
    relevantes = [(d, s) for d, s in resultados if s <= config.UMBRAL_DISTANCIA_RAG]
    return resultados, relevantes


@tool
def consultar_procedimientos(pregunta: str) -> dict:
    """Consulta los procedimientos internos y las fuentes oficiales (RAG).

    Úsala para responder preguntas sobre cómo proceder en la agencia de
    aduanas: documentos requeridos, observaciones, trazabilidad, permisos.
    Devuelve la respuesta, si hubo evidencia suficiente y las fuentes.
    """
    servicios = obtener_servicios()
    resultados, relevantes = recuperar_con_umbral(pregunta)
    fuentes = [
        {"fuente": d.metadata.get("fuente"), "tipo": d.metadata.get("tipo_fuente"), "distancia": round(float(s), 4)}
        for d, s in resultados
    ]
    if not relevantes:
        return {"respuesta": config.MENSAJE_SIN_INFORMACION, "suficiente": False,
                "motivo": "ningún fragmento bajo el umbral de distancia", "fuentes": fuentes}

    contexto = "\n\n".join(
        f"[Fragmento {i}]\nFuente: {d.metadata.get('fuente')}\nTipo: {d.metadata.get('tipo_fuente')}\n"
        f"Contenido:\n{d.page_content}"
        for i, (d, _) in enumerate(relevantes, start=1)
    )
    respuesta = (PROMPT_RAG | servicios.llm).invoke({"contexto": contexto, "pregunta": pregunta}).text.strip()
    suficiente = bool(respuesta) and "no existe información suficiente" not in respuesta.lower()
    return {
        "respuesta": respuesta or config.MENSAJE_SIN_INFORMACION,
        "suficiente": suficiente,
        "motivo": "respuesta respaldada" if suficiente else "el modelo se abstuvo",
        "fuentes": fuentes,
    }


@tool
def obtener_expediente(operacion_id: str) -> dict:
    """Obtiene el expediente de una operación (ej. OP1003): cliente, mercancía,
    documentos recibidos, permisos, estado actual y observaciones abiertas."""
    servicios = obtener_servicios()
    expediente = servicios.almacen.obtener_expediente(operacion_id)
    if expediente is None:
        return {"error": f"No existe la operación {operacion_id}",
                "operaciones_disponibles": servicios.almacen.listar_operaciones()}
    abiertas = [o for o in servicios.almacen.observaciones(operacion_id) if o["estado"] != "Cerrada"]
    return {
        **expediente,
        "estado_actual": servicios.almacen.estado_operacion(operacion_id),
        "observaciones_abiertas": len(abiertas),
    }


@tool
def listar_observaciones(operacion_id: str = "") -> list[dict]:
    """Lista las observaciones registradas. Si se indica operacion_id (ej. OP1003)
    filtra por esa operación; si se deja vacío devuelve todas."""
    campos = ("id", "operacion_id", "documento", "nivel", "estado", "descripcion", "accion_requerida")
    return [{c: o.get(c) for c in campos} for o in obtener_servicios().almacen.observaciones(operacion_id or None)]


@tool
def buscar_memoria(consulta: str, cliente: str = "") -> list[dict]:
    """Busca en la memoria de largo plazo antecedentes, preferencias o episodios
    anteriores relacionados con la consulta. Puede filtrar por nombre de cliente."""
    return obtener_servicios().memoria.recordar(consulta, cliente=cliente)
