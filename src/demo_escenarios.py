"""Ejecuta los escenarios de demostración del agente y genera evidencias.

Uso:
    python src/demo_escenarios.py              # proveedor del .env (evidencia real)
    python src/demo_escenarios.py --simulado   # sin LLM (modelo simulado)

Cada escenario muestra cómo el agente ajusta su plan ante condiciones
distintas. Las evidencias se guardan en evidencias/agente/<modo>/.
"""

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agente import Rutas, configuracion_hilo, crear_agente
from agente.grafo import construir_grafo
from agente.memoria import crear_checkpointer
from agente.servicios import obtener_servicios

RAIZ = Path(__file__).resolve().parent.parent


def tabla_plan(plan: list[dict]) -> list[str]:
    lineas = ["| Orden | Tarea | Acción | Prioridad | Estado | Resultado |", "|---:|---|---|---:|---|---|"]
    for t in sorted(plan, key=lambda t: (t.get("orden_ejecucion") or 99, t["secuencia"])):
        lineas.append(f"| {t.get('orden_ejecucion') or '-'} | {t['id']} | {t['accion']} | {t['prioridad']} | "
                      f"{t['estado']} | {t['resultado']} |")
    return lineas


def tabla_decisiones(decisiones: list[dict]) -> list[str]:
    lineas = ["| Paso | Condición detectada | Decisión | Regla |", "|---|---|---|---|"]
    lineas += [f"| {d['paso']} | {d['condicion']} | {d['decision']} | {d['regla']} |" for d in decisiones]
    return lineas


class Demo:
    def __init__(self, modo: str):
        self.modo = modo
        self.salidas = RAIZ / "salidas" / f"demo_{modo}"
        if self.salidas.exists():
            shutil.rmtree(self.salidas)
        self.rutas = Rutas()
        self.rutas.salidas = self.salidas
        self.grafo, self.servicios = crear_agente(modo, self.rutas)
        self.modo = self.servicios.modo  # "ollama", "gemini" o "simulado"
        if self.modo == "simulado":
            self.descripcion = "modelo y embeddings deterministas, sin LLM"
        else:
            from agente import modelos
            self.descripcion = modelos.describir().split(" · ", 1)[1]
        self.evidencias = RAIZ / "evidencias" / "agente" / self.modo
        self.evidencias.mkdir(parents=True, exist_ok=True)
        self.resumen = []

    def ejecutar(self, hilo: str, mensaje: str, respuesta_humana: str | None = "aprobar", grafo=None) -> tuple[dict, list]:
        grafo = grafo or self.grafo
        cfg = configuracion_hilo(hilo)
        inicio = time.perf_counter()
        resultado = grafo.invoke({"messages": [HumanMessage(content=mensaje)]}, cfg)
        pausas = []
        while "__interrupt__" in resultado and respuesta_humana is not None:
            pausas.append(resultado["__interrupt__"][0].value)
            resultado = grafo.invoke(Command(resume=respuesta_humana), cfg)
        resultado["_segundos"] = round(time.perf_counter() - inicio, 1)
        return resultado, pausas

    def registrar(self, numero: int, titulo: str, objetivo: str, mensaje: str, resultado: dict,
                  pausas: list, notas: list[str] | None = None, criterio: tuple[str, bool] | None = None) -> None:
        lineas = [f"# Escenario {numero}: {titulo}", "", f"- Modo: **{self.modo}** ({self.descripcion})", f"- Fecha de ejecución: {time.strftime('%Y-%m-%d %H:%M')}",
                  f"- Objetivo: {objetivo}", f"- Entrada del usuario: `{mensaje}`",
                  f"- Tiempo de ejecución: {resultado.get('_segundos')} s", ""]
        if resultado.get("recuerdos"):
            lineas += ["## Memoria de largo plazo recuperada", ""]
            lineas += [f"- [{r['tipo']}] {r['texto']} (distancia {r['distancia']})" for r in resultado["recuerdos"]]
            lineas.append("")
        if resultado.get("plan"):
            lineas += ["## Plan ejecutado (ordenado por ejecución)", ""] + tabla_plan(resultado["plan"]) + [""]
        if resultado.get("decisiones"):
            lineas += ["## Decisiones adaptativas", ""] + tabla_decisiones(resultado["decisiones"]) + [""]
        if pausas:
            lineas += ["## Pausa human-in-the-loop", "", "```text", pausas[0]["borrador"], "```", ""]
        lineas += ["## Respuesta del agente", "", resultado["messages"][-1].text, ""]
        if notas:
            lineas += ["## Observaciones", ""] + [f"- {n}" for n in notas] + [""]
        if criterio:
            lineas += [f"**Criterio de aceptación:** {criterio[0]} → {'CUMPLE' if criterio[1] else 'NO CUMPLE'}"]
        nombre = f"escenario_{numero:02d}.md"
        (self.evidencias / nombre).write_text("\n".join(lineas), encoding="utf-8")
        self.resumen.append({"escenario": numero, "titulo": titulo, "archivo": nombre,
                             "estado_final": (resultado.get("estado_final") or {}).get("estado"),
                             "tareas": len(resultado.get("plan", [])), "decisiones": len(resultado.get("decisiones", [])),
                             "segundos": resultado.get("_segundos"),
                             "criterio": criterio[0] if criterio else "", "cumple": criterio[1] if criterio else None})
        estado = "OK " if (criterio is None or criterio[1]) else "REVISAR"
        print(f"[{estado}] Escenario {numero}: {titulo} ({resultado.get('_segundos')} s)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulado", action="store_true")
    args = parser.parse_args()
    modo = "simulado" if args.simulado else "real"
    try:
        demo = Demo(modo)
    except Exception as error:
        print(f"No fue posible iniciar el agente: {error}")
        sys.exit(1)
    estado_de = lambda r: (r.get("estado_final") or {}).get("estado")  # noqa: E731
    acciones = lambda r: [t["accion"] for t in r.get("plan", [])]  # noqa: E731

    # 1. Flujo sin observaciones
    r, p = demo.ejecutar("e1", "Revisa la OP1001")
    demo.registrar(1, "Expediente completo y concordante", "Verificar el flujo base sin hallazgos.",
                   "Revisa la OP1001", r, p, criterio=("Estado 'Derivada a revisión' sin observaciones",
                                                       estado_de(r) == "Derivada a revisión"))

    # 2. Documentos faltantes + preferencia de memoria + HITL
    r, p = demo.ejecutar("e2", "Revisa la OP1002")
    demo.registrar(2, "Documentos faltantes y preferencia del cliente", "Detectar faltantes (incluye certificado de "
                   "origen por preferencia arancelaria) y usar la preferencia de contacto guardada en memoria.",
                   "Revisa la OP1002", r, p,
                   criterio=("Pendiente de documentación, comunicación a Paula Rojas aprobada por humano",
                             estado_de(r) == "Pendiente de documentación" and bool(p) and "Paula Rojas" in p[0]["borrador"]))

    # 3. Inconsistencias corregibles
    r3, p = demo.ejecutar("e3", "Revisa la OP1003")
    demo.registrar(3, "Inconsistencias corregibles", "Detectar diferencias de bultos y peso y comunicar al cliente.",
                   "Revisa la OP1003", r3, p, criterio=("Con observaciones y comunicación generada",
                                                        estado_de(r3) == "Con observaciones" and bool(p)))

    # 4. Observación crítica + antecedente en memoria
    r4, p = demo.ejecutar("e4", "Revisa la OP1004")
    critico_primero = sorted(r4["plan"], key=lambda t: t.get("orden_ejecucion") or 99)[0]["accion"] == "verificar_permisos"
    reforzada = any(t["accion"] == "validar_concordancia" and t["args"].get("reforzada") for t in r4["plan"])
    demo.registrar(4, "Observación crítica con antecedente del cliente", "Priorizar el control crítico, escalar y "
                   "reforzar la validación por un antecedente recuperado de la memoria de largo plazo.",
                   "Revisa la OP1004", r4, p,
                   notas=["La comunicación al cliente no se genera: las observaciones críticas se escalan (INT-002)."],
                   criterio=("Permisos verificados primero, validación reforzada y escalamiento sin comunicación",
                             critico_primero and reforzada and "escalar" in acciones(r4) and not p))

    # 4b. Mismo expediente sin memoria de largo plazo
    import copy
    from agente.memoria import MemoriaLargoPlazo
    servicios = obtener_servicios()
    memoria_original = servicios.memoria
    rutas_sin_memoria = copy.copy(demo.rutas)
    rutas_sin_memoria.salidas = demo.salidas / "sin_memoria"
    from agente.almacen import Almacen
    almacen_original, rutas_originales = servicios.almacen, servicios.rutas
    servicios.memoria = MemoriaLargoPlazo(memoria_original.almacen.embeddings, rutas_sin_memoria.salidas / "chroma_vacia",
                                          coleccion="memoria_vacia")
    servicios.almacen, servicios.rutas = Almacen(rutas_sin_memoria), rutas_sin_memoria  # registro limpio
    r4b, p = demo.ejecutar("e4b", "Revisa la OP1004")
    servicios.memoria, servicios.almacen, servicios.rutas = memoria_original, almacen_original, rutas_originales
    reforzada_b = any(t["accion"] == "validar_concordancia" and t["args"].get("reforzada") for t in r4b["plan"])
    demo.registrar(5, "Control: OP1004 sin memoria de largo plazo", "Comparar el plan con el escenario 4 para "
                   "evidenciar el efecto de la memoria.", "Revisa la OP1004", r4b, p,
                   notas=["Sin antecedentes la concordancia se planifica con prioridad 2, después de documentos y sin "
                          "verificación reforzada. Se usa un registro de observaciones limpio para aislar el efecto."],
                   criterio=("El plan NO incluye validación reforzada", not reforzada_b))

    # 5. Mercancía no catalogada + documento ilegible
    r, p = demo.ejecutar("e5", "Revisa la OP1005")
    tipos = [h["tipo"] for h in r.get("hallazgos", [])]
    demo.registrar(6, "Mercancía no catalogada", "Consultar la base documental antes de asumir requisitos y actuar "
                   "según exista o no evidencia suficiente.", "Revisa la OP1005", r, p,
                   criterio=("Requisito por confirmar o escalado + documento ilegible",
                             ("requisito_no_determinado" in tipos or "requisito_por_confirmar" in tipos)
                             and "documento_ilegible" in tipos))

    # 6. Condición cambiante: llega un documento corregido (mismo hilo que el escenario 3)
    mensaje = "Llegó la lista de empaque corregida de la OP1003, reprocésala"
    r, p = demo.ejecutar("e3", mensaje)
    demo.registrar(7, "Condición cambiante: documento corregido", "Incorporar la nueva versión sin sobrescribir, "
                   "verificar y cerrar observaciones, y replanificar el estado.", mensaje, r, p,
                   notas=[f"Mensajes en el hilo e3 (memoria corta): {len(r['messages'])}"],
                   criterio=("Observaciones cerradas y estado 'Derivada a revisión'",
                             estado_de(r) == "Derivada a revisión" and "cerrar_observaciones" in acciones(r)))

    # 7. Continuidad: flujo pausado y retomado desde otro proceso (checkpointer SQLite)
    cfg = configuracion_hilo("e7")
    pausado = demo.grafo.invoke({"messages": [HumanMessage(content="Revisa nuevamente la OP1002")]}, cfg)
    observaciones_previas = len(demo.servicios.almacen.observaciones("OP1002"))
    nuevo_grafo = construir_grafo(crear_checkpointer(demo.rutas.checkpoints))  # simula reiniciar el programa
    estado_guardado = nuevo_grafo.get_state(cfg)
    retomado = nuevo_grafo.invoke(Command(resume="rechazar"), cfg)
    retomado["_segundos"] = "-"
    demo.registrar(8, "Continuidad de un flujo prolongado", "Pausar en la aprobación humana, reiniciar el grafo "
                   "con el mismo checkpointer SQLite y retomar el flujo en el punto exacto.", "Revisa nuevamente la OP1002",
                   retomado, [],
                   notas=[f"Interrupción detectada: {'__interrupt__' in pausado}",
                          f"Nodo pendiente tras reiniciar: {estado_guardado.next}",
                          "Se respondió 'rechazar': el borrador no se envía y la operación sigue con observaciones.",
                          f"Observaciones en el registro: {observaciones_previas}"],
                   criterio=("El nuevo proceso retoma en 'aprobacion_humana' y termina el flujo",
                             estado_guardado.next == ("aprobacion_humana",) and bool(retomado.get("estado_final"))))

    # 8. Priorización de la cola de trabajo
    r, p = demo.ejecutar("e8", "Prioriza la cola de revisión de hoy")
    cola = r["bitacora"][-2].get("cola", []) if len(r["bitacora"]) > 1 else []
    demo.registrar(9, "Secuenciación de la jornada", "Ordenar operaciones pendientes por urgencia, cercanía del "
                   "arribo y riesgo de la mercancía.", "Prioriza la cola de revisión de hoy", r, p,
                   criterio=("Se entrega un orden con justificación", "Orden recomendado" in r["messages"][-1].text))

    # 9. Conversación: el modelo elige herramientas y usa memoria entre hilos
    mensajes = ["¿Qué debe hacer el ejecutivo si existen diferencias en cantidades o peso?",
                "¿Qué observaciones tiene registradas la OP1003?",
                "Recuerda que el cliente Ferretería Central Ltda prefiere que las comunicaciones se dirijan a Jorge Díaz"]
    salidas = []
    for m in mensajes:
        r, _ = demo.ejecutar("e9", m)
        herramienta = next((b["detalle"] for b in reversed(r["bitacora"]) if b["nodo"] == "agente_conversacional"), "")
        salidas.append(f"**{m}** → {herramienta}\n\n> {r['messages'][-1].text[:500]}")
    r, _ = demo.ejecutar("e9-otro-hilo", "¿Qué antecedentes o preferencias tienes de Ferretería Central Ltda?")
    salidas.append(f"**(nuevo hilo) ¿Qué antecedentes o preferencias tienes de Ferretería Central Ltda?** → "
                   f"{r['bitacora'][-2]['detalle']}\n\n> {r['messages'][-1].text[:500]}")
    r["plan"], r["decisiones"] = [], []
    demo.registrar(10, "Modo conversacional (ReAct) y memoria entre sesiones", "Verificar que el modelo selecciona "
                   "herramientas y que una preferencia guardada se recupera desde otro hilo.", " / ".join(mensajes), r, [],
                   notas=salidas)

    (demo.evidencias / "resumen.json").write_text(json.dumps(demo.resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    (demo.evidencias / "memoria_largo_plazo.json").write_text(
        json.dumps(demo.servicios.memoria.exportar(), ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy(demo.rutas.registro_observaciones, demo.evidencias / "registro_observaciones.json")
    shutil.copy(demo.rutas.trazabilidad, demo.evidencias / "trazabilidad.jsonl")
    shutil.copy(demo.rutas.estados_operaciones, demo.evidencias / "estados_operaciones.json")
    cumplen = sum(1 for e in demo.resumen if e["cumple"] is not False)
    print(f"\n{cumplen}/{len(demo.resumen)} escenarios cumplen su criterio. Evidencias en {demo.evidencias}")


if __name__ == "__main__":
    main()
