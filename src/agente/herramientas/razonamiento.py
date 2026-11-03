"""Herramientas de RAZONAMIENTO: analizan el expediente aplicando las reglas
de los procedimientos internos y producen hallazgos clasificados."""

import re
from datetime import date

from langchain_core.tools import tool

from .. import config, reglas
from ..servicios import obtener_servicios
from .consulta import consultar_procedimientos, recuperar_con_umbral

CAMPOS_COMPARABLES = ("bultos", "peso_kg", "descripcion")


def _hallazgo(tipo: str, documento: str, descripcion: str, **extra) -> dict:
    clasificacion = reglas.clasificar(tipo)
    return {
        "tipo": tipo,
        "documento": documento,
        "descripcion": descripcion,
        "clave": f"{tipo}:{documento}" + (f":{extra['organismo']}" if extra.get("organismo") else ""),
        **clasificacion,
        **extra,
    }


def _expediente(operacion_id: str) -> dict:
    expediente = obtener_servicios().almacen.obtener_expediente(operacion_id)
    if expediente is None:
        raise ValueError(f"No existe la operación {operacion_id}")
    return expediente


# ------------------------------------------------------------------ análisis
def analizar_documentos(expediente: dict) -> dict:
    documentos = expediente["documentos"]
    requeridos = dict(reglas.DOCUMENTOS_OBLIGATORIOS)
    if expediente["mercancia"].get("preferencia_arancelaria"):
        requeridos["certificado_origen"] = "Certificado de origen (preferencia arancelaria)"

    hallazgos, faltantes = [], []
    for clave, nombre in requeridos.items():
        doc = documentos.get(clave)
        if doc is None:
            faltantes.append(nombre)
            hallazgos.append(_hallazgo("documento_faltante", clave, f"No se recibió: {nombre}."))
            continue
        if clave == "mandato" and not doc.get("vigente", False):
            faltantes.append(nombre)
            hallazgos.append(_hallazgo("documento_faltante", clave, "El mandato recibido no está vigente."))
        if not doc.get("legible", True):
            hallazgos.append(_hallazgo("documento_ilegible", clave, f"El archivo {doc['archivo']} no es legible."))
        for dato in ("numero", "fecha"):
            if not doc.get(dato):
                hallazgos.append(_hallazgo("dato_faltante", clave, f"{nombre}: falta el dato '{dato}'."))
    return {"requeridos": list(requeridos.values()), "faltantes": faltantes, "hallazgos": hallazgos}


def analizar_permisos(expediente: dict) -> dict:
    categoria = expediente["mercancia"]["categoria"]
    organismos = reglas.CATEGORIAS_REGULADAS.get(categoria, [])
    conocida = categoria in reglas.CATEGORIAS_REGULADAS or categoria in reglas.CATEGORIAS_SIN_CONTROL
    presentes = {p.get("organismo") for p in expediente.get("permisos", [])}
    hallazgos = [
        _hallazgo("permiso_faltante", "permiso",
                  f"La mercancía ({expediente['mercancia']['descripcion']}) requiere permiso o visto bueno de "
                  f"{organismo} y no se recibió.", organismo=organismo)
        for organismo in organismos if organismo not in presentes
    ]
    return {"categoria": categoria, "categoria_conocida": conocida, "regulada": bool(organismos),
            "organismos_requeridos": organismos, "hallazgos": hallazgos}


def analizar_concordancia(expediente: dict, reforzada: bool = False) -> dict:
    documentos = expediente["documentos"]
    factura = documentos.get("factura_comercial")
    if factura is None:
        return {"ejecutada": False, "motivo": "Sin factura comercial no es posible validar concordancia.", "hallazgos": []}

    hallazgos = []
    nombres = {"documento_transporte": "documento de transporte", "lista_empaque": "lista de empaque"}
    for clave, nombre in nombres.items():
        doc = documentos.get(clave)
        if doc is None:
            continue
        for campo in CAMPOS_COMPARABLES:
            if campo in doc and campo in factura and doc[campo] != factura[campo]:
                tipo = {"bultos": "diferencia_bultos", "peso_kg": "diferencia_peso",
                        "descripcion": "diferencia_descripcion"}[campo]
                hallazgos.append(_hallazgo(
                    tipo, clave,
                    f"{campo.replace('_kg', ' (kg)').capitalize()}: factura indica {factura[campo]} y "
                    f"{nombre} indica {doc[campo]}.",
                ))
        if "valor_usd" in doc and doc["valor_usd"] != factura["valor_usd"]:
            diferencia = abs(doc["valor_usd"] - factura["valor_usd"]) / factura["valor_usd"]
            tipo = "diferencia_valor" if diferencia > config.UMBRAL_DIFERENCIA_VALOR else "diferencia_descripcion"
            hallazgos.append(_hallazgo(tipo, clave, f"Valor: diferencia de {diferencia:.1%} respecto de la factura."))
        if doc.get("importador_rut") != factura.get("importador_rut"):
            hallazgos.append(_hallazgo(
                "importador_inconsistente", clave,
                f"RUT del importador en {nombre} ({doc.get('importador_rut')}) no coincide con la factura "
                f"({factura.get('importador_rut')}).",
            ))

    if reforzada:
        # Verificación reforzada: identidad contra el maestro del cliente y
        # pertenencia de cada documento a la operación.
        for clave, doc in documentos.items():
            if doc.get("importador_rut") and doc["importador_rut"] != expediente["rut_cliente"]:
                if not any(h["clave"] == f"importador_inconsistente:{clave}" for h in hallazgos):
                    hallazgos.append(_hallazgo(
                        "importador_inconsistente", clave,
                        f"RUT en {clave} ({doc['importador_rut']}) distinto al RUT registrado del cliente "
                        f"({expediente['rut_cliente']}).",
                    ))
            if doc.get("referencia_operacion") and doc["referencia_operacion"] != expediente["operacion_id"]:
                hallazgos.append(_hallazgo(
                    "operacion_distinta", clave,
                    f"{clave} referencia la operación {doc['referencia_operacion']}.",
                ))
        for h in hallazgos:
            if h["tipo"] == "importador_inconsistente":
                h["reincidencia"] = True
    return {"ejecutada": True, "reforzada": reforzada, "hallazgos": hallazgos}


def analizar_nomenclatura(expediente: dict) -> dict:
    hallazgos = []
    op = expediente["operacion_id"]
    for clave, doc in expediente["documentos"].items():
        prefijo = reglas.PREFIJOS_ARCHIVO.get(clave)
        if prefijo and not re.fullmatch(rf"{prefijo}_{op}_V\d+\.\w+", doc["archivo"]):
            hallazgos.append(_hallazgo(
                "nomenclatura", clave,
                f"El archivo '{doc['archivo']}' no sigue la convención {prefijo}_{op}_V{doc.get('version', 1)}.",
            ))
    return {"hallazgos": hallazgos}


def analisis_completo(expediente: dict, reforzada: bool = False) -> list[dict]:
    hallazgos = []
    hallazgos += analizar_documentos(expediente)["hallazgos"]
    hallazgos += analizar_permisos(expediente)["hallazgos"]
    hallazgos += analizar_concordancia(expediente, reforzada)["hallazgos"]
    hallazgos += analizar_nomenclatura(expediente)["hallazgos"]
    return hallazgos


# ---------------------------------------------------------------- herramientas
@tool
def verificar_documentos_requeridos(operacion_id: str) -> dict:
    """Comprueba que el expediente tenga los documentos exigidos por INT-001
    (factura, transporte, lista de empaque, mandato vigente y certificado de
    origen si hay preferencia arancelaria), su legibilidad y datos mínimos."""
    return analizar_documentos(_expediente(operacion_id))


@tool
def verificar_permisos(operacion_id: str) -> dict:
    """Determina si la mercancía está sujeta a control previo (EXT-001) y si
    se recibieron los permisos o vistos buenos del organismo competente."""
    return analizar_permisos(_expediente(operacion_id))


@tool
def validar_concordancia(operacion_id: str, reforzada: bool = False) -> dict:
    """Compara factura, documento de transporte y lista de empaque (bultos,
    peso, descripción, valor e importador). Con reforzada=True además valida
    identidad contra el RUT del cliente y la referencia de operación."""
    return analizar_concordancia(_expediente(operacion_id), reforzada)


@tool
def validar_nomenclatura(operacion_id: str) -> dict:
    """Verifica la convención de nombres TIPO_DOCUMENTO_OPERACION_VERSION (INT-003)."""
    return analizar_nomenclatura(_expediente(operacion_id))


@tool
def clasificar_observacion(tipo_hallazgo: str) -> dict:
    """Clasifica un hallazgo como informativa, corregible o crítica según INT-002."""
    return reglas.clasificar(tipo_hallazgo)


@tool
def evaluar_requisitos_especiales(operacion_id: str) -> dict:
    """Para mercancías no catalogadas, consulta la base documental para saber si
    podrían requerir control previo. Si no hay evidencia, recomienda escalar."""
    expediente = _expediente(operacion_id)
    descripcion = expediente["mercancia"]["descripcion"]
    consulta = consultar_procedimientos.invoke(
        {"pregunta": f"¿La importación de {descripcion} requiere autorización, permiso o control previo?"}
    )
    if consulta["suficiente"]:
        hallazgo = _hallazgo("requisito_por_confirmar", "mercancia",
                             f"Las fuentes sugieren posible control previo para '{descripcion}': {consulta['respuesta']}")
    else:
        hallazgo = _hallazgo("requisito_no_determinado", "mercancia",
                             f"Las fuentes disponibles no permiten determinar si '{descripcion}' requiere control previo.")
    return {"consulta": consulta, "hallazgos": [hallazgo]}


@tool
def fundamentar_hallazgos(tipos: list[str]) -> list[dict]:
    """Busca en la base de conocimiento el fragmento que respalda cada tipo de
    hallazgo y verifica que provenga de la fuente esperada."""
    fundamentos = []
    for tipo in dict.fromkeys(tipos):
        regla = reglas.CATALOGO_HALLAZGOS.get(tipo)
        if regla is None:
            fundamentos.append({"tipo": tipo, "respaldado": False, "motivo": "tipo no catalogado"})
            continue
        resultados, relevantes = recuperar_con_umbral(regla["pregunta"], k=config.FRAGMENTOS_RAG)
        fuentes = [d.metadata.get("fuente") for d, _ in relevantes]
        mejor = relevantes[0] if relevantes else (resultados[0] if resultados else None)
        fundamentos.append({
            "tipo": tipo,
            "respaldado": bool(relevantes),
            "fuente_esperada": regla["fuente_esperada"],
            "fuente_recuperada": mejor[0].metadata.get("fuente") if mejor else None,
            "coincide_fuente": regla["fuente_esperada"] in fuentes,
            "distancia": round(float(mejor[1]), 4) if mejor else None,
            "extracto": mejor[0].page_content[:280].replace("\n", " ") if mejor else "",
        })
    return fundamentos


@tool
def verificar_resolucion_observaciones(operacion_id: str) -> dict:
    """Compara las observaciones abiertas de una operación con el estado actual
    del expediente para identificar cuáles fueron resueltas (INT-002, cierre)."""
    servicios = obtener_servicios()
    expediente = _expediente(operacion_id)
    vigentes = {h["clave"] for h in analisis_completo(expediente, reforzada=True)}
    abiertas = [o for o in servicios.almacen.observaciones(operacion_id) if o["estado"] != reglas.OBS_CERRADA]
    resueltas = [o for o in abiertas if o["clave"] not in vigentes]
    pendientes = [o for o in abiertas if o["clave"] in vigentes]
    return {"resueltas": resueltas, "pendientes": pendientes}


def puntaje_prioridad(expediente: dict, hoy: date | None = None) -> tuple[int, list[str]]:
    hoy = hoy or date.today()
    puntaje, motivos = 0, []
    if expediente.get("urgente"):
        puntaje += 3
        motivos.append("marcada urgente (+3)")
    dias = (date.fromisoformat(expediente["fecha_arribo_estimada"]) - hoy).days
    if dias <= 3:
        puntaje += 2
        motivos.append(f"arribo en {dias} días (+2)")
    elif dias <= 7:
        puntaje += 1
        motivos.append(f"arribo en {dias} días (+1)")
    categoria = expediente["mercancia"]["categoria"]
    if categoria in reglas.CATEGORIAS_REGULADAS or categoria not in reglas.CATEGORIAS_SIN_CONTROL:
        puntaje += 2
        motivos.append("mercancía regulada o no catalogada (+2)")
    return puntaje, motivos


@tool
def priorizar_operaciones(fecha_referencia: str = "") -> list[dict]:
    """Ordena las operaciones pendientes por prioridad (urgencia, cercanía del
    arribo y riesgo de la mercancía) para secuenciar la jornada de revisión."""
    servicios = obtener_servicios()
    fecha = fecha_referencia or config.FECHA_REFERENCIA
    hoy = date.fromisoformat(fecha) if fecha else date.today()
    cola = []
    for operacion_id in servicios.almacen.listar_operaciones():
        estado = servicios.almacen.estado_operacion(operacion_id)
        if estado and estado["estado"] == reglas.ESTADO_DERIVADA:
            continue
        expediente = servicios.almacen.obtener_expediente(operacion_id)
        puntaje, motivos = puntaje_prioridad(expediente, hoy)
        cola.append({"operacion_id": operacion_id, "cliente": expediente["cliente"], "puntaje": puntaje,
                     "motivos": motivos, "fecha_arribo": expediente["fecha_arribo_estimada"]})
    cola.sort(key=lambda o: (-o["puntaje"], o["fecha_arribo"]))
    for posicion, operacion in enumerate(cola, start=1):
        operacion["orden"] = posicion
    return cola
