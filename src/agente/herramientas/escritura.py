"""Herramientas de ESCRITURA: registran observaciones, redactan comunicaciones,
actualizan estados, escalan casos y guardan memoria. Cada acción deja un
registro de trazabilidad con los campos exigidos por INT-003."""

import copy
import json
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool

from .. import reglas
from ..almacen import ahora
from ..servicios import obtener_servicios


@tool
def registrar_observacion(operacion_id: str, tipo: str, documento: str, descripcion: str, clave: str = "") -> dict:
    """Registra una observación en el control interno con los campos de INT-002.
    Si ya existe una observación abierta con la misma clave no la duplica."""
    servicios = obtener_servicios()
    clave = clave or f"{tipo}:{documento}"
    for existente in servicios.almacen.observaciones(operacion_id):
        if existente["clave"] == clave and existente["estado"] != reglas.OBS_CERRADA:
            return {**existente, "ya_registrada": True}
    clasificacion = reglas.clasificar(tipo)
    observacion = servicios.almacen.agregar_observacion({
        "fecha_deteccion": ahora(),
        "operacion_id": operacion_id,
        "documento": documento,
        "tipo": tipo,
        "clave": clave,
        "descripcion": descripcion,
        "nivel": clasificacion["nivel"],
        "accion_requerida": clasificacion["accion"],
        "responsable_seguimiento": "Ejecutivo de cuenta",
        "estado": reglas.OBS_ABIERTA,
        "fecha_resolucion": None,
    })
    servicios.almacen.trazar(operacion_id, "Detecta una inconsistencia", documento,
                             f"{observacion['id']} registrada ({observacion['nivel']})", descripcion)
    return {**observacion, "ya_registrada": False}


@tool
def cerrar_observacion(id_observacion: str, resolucion: str) -> dict:
    """Cierra una observación verificada como resuelta (INT-002, cierre)."""
    servicios = obtener_servicios()
    observacion = servicios.almacen.actualizar_observacion(id_observacion, {
        "estado": reglas.OBS_CERRADA, "fecha_resolucion": ahora(), "resolucion": resolucion,
    })
    if observacion is None:
        return {"error": f"No existe la observación {id_observacion}"}
    servicios.almacen.trazar(observacion["operacion_id"], "Cierra una observación", observacion["documento"],
                             f"{id_observacion} cerrada", resolucion)
    return observacion


@tool
def redactar_comunicacion_cliente(operacion_id: str, observaciones: list[dict], destinatario: str = "",
                                  plazo_respuesta: str = "", urgente: bool = False) -> dict:
    """Redacta el borrador de comunicación al cliente. Cada punto indica el
    documento afectado, la inconsistencia detectada y la acción necesaria
    (INT-002, Comunicación). No incluye suposiciones."""
    servicios = obtener_servicios()
    expediente = servicios.almacen.obtener_expediente(operacion_id)
    saludo = f"Estimado/a {destinatario}" if destinatario else f"Estimados/as {expediente['cliente']}"
    lineas = [
        f"Asunto: {'[URGENTE] ' if urgente else ''}Observaciones de la operación {operacion_id}",
        "",
        f"{saludo}:",
        "",
        f"Durante la revisión documental de la operación {operacion_id} "
        f"({expediente['mercancia']['descripcion']}) se identificaron los siguientes puntos:",
        "",
    ]
    for numero, obs in enumerate(observaciones, start=1):
        documento = reglas.NOMBRES_DOCUMENTOS.get(obs["documento"], obs["documento"])
        lineas += [
            f"{numero}. Documento afectado: {documento}",
            f"   Inconsistencia detectada: {obs['descripcion']}",
            f"   Acción necesaria: {obs.get('accion_requerida') or obs.get('accion')}",
            "",
        ]
    if plazo_respuesta:
        lineas.append(f"Agradeceremos su respuesta dentro de un plazo de {plazo_respuesta}.")
    lineas += [
        "La operación no continuará su preparación hasta recibir los antecedentes indicados.",
        "",
        "Saludos cordiales,",
        "Agencia de Aduanas del Norte (borrador generado por AduanaAgent, sujeto a revisión del ejecutivo)",
    ]
    texto = "\n".join(lineas)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = servicios.rutas.carpeta_operacion(operacion_id) / f"comunicacion_cliente_{marca}.md"
    ruta.write_text(texto, encoding="utf-8")
    servicios.almacen.trazar(operacion_id, "Redacta comunicación al cliente", ruta.name,
                             "Borrador pendiente de aprobación", f"{len(observaciones)} puntos")
    return {"ruta": str(ruta), "texto": texto, "estado": "borrador"}


@tool
def actualizar_estado_operacion(operacion_id: str, estado: str, motivo: str) -> dict:
    """Actualiza el estado de la operación (INT-001): Pendiente de documentación,
    Con observaciones, Documentación completa o Derivada a revisión."""
    servicios = obtener_servicios()
    validos = {reglas.ESTADO_PENDIENTE, reglas.ESTADO_CON_OBSERVACIONES, reglas.ESTADO_COMPLETA, reglas.ESTADO_DERIVADA}
    if estado not in validos:
        return {"error": f"Estado no válido: {estado}", "validos": sorted(validos)}
    registro = servicios.almacen.fijar_estado(operacion_id, estado, motivo)
    servicios.almacen.trazar(operacion_id, "Modifica el estado de una operación", "-",
                             f"{registro['estado_anterior']} -> {estado}", motivo)
    return registro


@tool
def escalar_a_responsable(operacion_id: str, motivo: str, ids_observaciones: list[str]) -> dict:
    """Escala observaciones críticas al responsable de revisión (INT-002,
    Escalamiento) y genera el ticket correspondiente."""
    servicios = obtener_servicios()
    for id_obs in ids_observaciones:
        servicios.almacen.actualizar_observacion(id_obs, {"estado": reglas.OBS_ESCALADA,
                                                          "responsable_seguimiento": "Responsable de revisión"})
    observaciones = [o for o in servicios.almacen.observaciones(operacion_id) if o["id"] in ids_observaciones]
    lineas = [f"# Escalamiento {operacion_id}", "", f"- Fecha: {ahora()}", f"- Motivo: {motivo}",
              "- Destinatario: Responsable de revisión", "", "## Observaciones escaladas", ""]
    lineas += [f"- {o['id']} [{o['nivel']}] {o['descripcion']}" for o in observaciones]
    lineas += ["", "El agente no resuelve observaciones críticas mediante suposiciones (INT-002)."]
    ruta = servicios.rutas.carpeta_operacion(operacion_id) / "escalamiento.md"
    ruta.write_text("\n".join(lineas), encoding="utf-8")
    servicios.almacen.trazar(operacion_id, "Escala una observación", ruta.name,
                             f"{len(ids_observaciones)} observaciones escaladas", motivo)
    return {"ruta": str(ruta), "escaladas": ids_observaciones}


@tool
def recibir_documento_corregido(ruta_correccion: str) -> dict:
    """Incorpora un documento corregido como NUEVA versión sin sobrescribir la
    anterior (INT-003). ruta_correccion apunta a un JSON de data/operaciones/correcciones."""
    servicios = obtener_servicios()
    ruta = Path(ruta_correccion)
    if not ruta.is_absolute():
        ruta = servicios.rutas.raiz / ruta
    correccion = json.loads(ruta.read_text(encoding="utf-8"))
    operacion_id, clave = correccion["operacion_id"], correccion["documento"]
    expediente = copy.deepcopy(servicios.almacen.obtener_expediente(operacion_id))
    anterior = expediente["documentos"].get(clave)
    expediente.setdefault("historial_versiones", []).append({
        "documento": clave, "version_reemplazada": anterior, "recibido": ahora(), "motivo": correccion["motivo"],
    })
    expediente["documentos"][clave] = correccion["contenido"]
    servicios.almacen.guardar_expediente(expediente)
    servicios.almacen.trazar(operacion_id, "Agrega o reemplaza un archivo", correccion["contenido"]["archivo"],
                             f"Nueva versión V{correccion['contenido'].get('version')} incorporada", correccion["motivo"])
    return {"operacion_id": operacion_id, "documento": clave,
            "version_nueva": correccion["contenido"]["archivo"],
            "version_anterior": anterior["archivo"] if anterior else None}


@tool
def guardar_memoria(texto: str, tipo: str = "preferencia", cliente: str = "", operacion_id: str = "",
                    contacto: str = "") -> dict:
    """Guarda un recuerdo en la memoria de largo plazo (preferencia de un cliente,
    antecedente o episodio) para usarlo en sesiones futuras. Si la preferencia
    indica a quién dirigir las comunicaciones, informa ese nombre en `contacto`."""
    servicios = obtener_servicios()
    clave = "contacto_comunicaciones" if contacto else ""
    identificador = servicios.memoria.guardar(texto=texto, tipo=tipo, cliente=cliente,
                                              operacion_id=operacion_id, clave=clave, valor=contacto)
    servicios.almacen.trazar(operacion_id or "-", "Guarda memoria de largo plazo", identificador, tipo, texto[:120])
    return {"id": identificador, "tipo": tipo, "cliente": cliente, "contacto": contacto}
