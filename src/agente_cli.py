"""Interfaz de terminal de AduanaAgent.

Uso:
    python src/agente_cli.py                     # hilo "principal", proveedor del .env
    python src/agente_cli.py --hilo turno_tarde   # otro hilo de memoria corta
    python src/agente_cli.py --simulado           # sin LLM (modelo simulado)
    python src/agente_cli.py --auto-aprobar       # aprueba comunicaciones (modo lote)

Comandos dentro del chat:
    /plan        muestra el último plan ejecutado
    /decisiones  muestra las decisiones del último flujo
    /memoria     lista la memoria de largo plazo
    /hilo NOMBRE cambia de hilo (memoria de corto plazo distinta)
    /salir       termina
"""

import argparse
import json
import sys

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agente import configuracion_hilo, crear_agente


def mostrar_plan(valores: dict) -> None:
    plan = valores.get("plan", [])
    if not plan:
        print("No hay plan en este hilo.")
        return
    print(f"\nPLAN DE {valores.get('operacion_id', '')}")
    for t in sorted(plan, key=lambda t: (t.get("orden_ejecucion") or 99, t["secuencia"])):
        print(f"  [{t.get('orden_ejecucion') or '-':>2}] {t['id']} p{t['prioridad']} {t['accion']:<30} "
              f"{t['estado']:<11} {t['resultado'][:70]}")


def mostrar_decisiones(valores: dict) -> None:
    for d in valores.get("decisiones", []):
        print(f"  - [{d['paso']}] {d['condicion']}\n      => {d['decision']} ({d['regla']})")


def resolver_interrupciones(grafo, cfg: dict, resultado: dict) -> dict:
    """Atiende pausas human-in-the-loop hasta que el flujo termine."""
    while "__interrupt__" in resultado:
        pausa = resultado["__interrupt__"][0].value
        print("\n" + "=" * 70)
        print(f"APROBACIÓN REQUERIDA – {pausa['operacion_id']}")
        print("=" * 70)
        print(pausa["borrador"])
        print("-" * 70)
        respuesta = input(pausa["pregunta"] + " ").strip() or "aprobar"
        resultado = grafo.invoke(Command(resume=respuesta), cfg)
    return resultado


def main() -> None:
    parser = argparse.ArgumentParser(description="AduanaAgent – agente de revisión documental")
    parser.add_argument("--hilo", default="principal")
    parser.add_argument("--simulado", action="store_true")
    parser.add_argument("--auto-aprobar", action="store_true")
    args = parser.parse_args()

    try:
        grafo, servicios = crear_agente("simulado" if args.simulado else "real")
    except Exception as error:
        print(f"No fue posible iniciar el agente: {error}")
        print("Revisa el proveedor del .env (Ollama iniciado o GOOGLE_API_KEY) y crea la base vectorial:")
        print("python src/probar_modelos.py  y  python src/crear_base_vectorial.py")
        sys.exit(1)

    hilo = args.hilo
    print("AduanaAgent – agente de revisión documental aduanera")
    print(f"Modo: {servicios.modo} | Hilo: {hilo} | Memorias de largo plazo: {servicios.memoria.cantidad()}")
    print("Ejemplos: 'Revisa la OP1003' · '¿Qué observaciones tiene la OP1003?' · 'Prioriza la cola'")
    print("Escribe /salir para terminar.\n")

    cfg = configuracion_hilo(hilo, args.auto_aprobar)
    pendiente = grafo.get_state(cfg)
    if pendiente.interrupts:
        print("Este hilo tiene un flujo pausado esperando aprobación. Se retoma ahora.")
        resolver_interrupciones(grafo, cfg, {"__interrupt__": pendiente.interrupts})

    while True:
        texto = input(f"[{hilo}] Tú: ").strip()
        if not texto:
            continue
        if texto == "/salir":
            break
        valores = grafo.get_state(cfg).values
        if texto == "/plan":
            mostrar_plan(valores)
            continue
        if texto == "/decisiones":
            mostrar_decisiones(valores)
            continue
        if texto == "/memoria":
            for m in servicios.memoria.exportar():
                print(f"  - [{m['tipo']}] {m['cliente']}: {m['texto'][:110]}")
            continue
        if texto.startswith("/hilo"):
            hilo = texto.split(maxsplit=1)[1] if " " in texto else "principal"
            cfg = configuracion_hilo(hilo, args.auto_aprobar)
            print(f"Hilo activo: {hilo}")
            continue
        try:
            resultado = grafo.invoke({"messages": [HumanMessage(content=texto)]}, cfg)
            resultado = resolver_interrupciones(grafo, cfg, resultado)
        except Exception as error:
            print(f"\nNo fue posible procesar la solicitud: {error}")
            continue
        print(f"\nAduanaAgent: {resultado['messages'][-1].text}\n")
        for entrada in resultado.get("bitacora", [])[-3:]:
            if entrada["nodo"] in ("recuperar_contexto", "agente_conversacional"):
                print(f"  · {entrada['nodo']}: {entrada['detalle']}")
        print()


if __name__ == "__main__":
    main()
