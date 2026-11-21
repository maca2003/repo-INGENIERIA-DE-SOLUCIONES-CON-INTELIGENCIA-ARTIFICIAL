"""Analiza los registros de ejecución del agente e identifica cuellos de botella,
arranques en frío, errores y anomalías (EP3, IE3).

Uso:
    python src/analizar_logs.py                       # eventos del benchmark (proveedor del .env)
    python src/analizar_logs.py --origen salidas/observabilidad   # registros del uso diario
    python src/analizar_logs.py --proveedor simulado

Escribe hallazgos_logs.md y hallazgos_logs.json junto a los eventos analizados.
"""

import argparse
import json
from pathlib import Path

from agente.analitica import analizar_eventos, cargar_eventos, hallazgos_en_texto

RAIZ = Path(__file__).resolve().parent.parent


def tabla(filas: list[dict], columnas: list[str]) -> list[str]:
    if not filas:
        return ["Sin datos.", ""]
    lineas = ["| " + " | ".join(columnas) + " |", "|" + "---|" * len(columnas)]
    lineas += ["| " + " | ".join(str(f.get(c, "")) for c in columnas) + " |" for f in filas]
    return lineas + [""]


def informe(analisis: dict, titulo: str) -> str:
    lineas = [f"# Análisis de registros · {titulo}", "", "## Hallazgos", ""]
    lineas += [f"{i}. {h}" for i, h in enumerate(hallazgos_en_texto(analisis), start=1)]
    lat = analisis["latencia_solicitud_ms"]
    lineas += ["", "## Latencia de las solicitudes", "",
               f"- Solicitudes: {analisis['solicitudes']} · media {lat['media']} ms · p50 {lat['p50']} ms · "
               f"p95 {lat['p95']} ms · máx. {lat['max']} ms",
               f"- Reparto del tiempo: {analisis['reparto_tiempo_pct']}", "",
               "## Tiempo de LLM por nodo", ""]
    lineas += tabla(analisis["llm_por_nodo"], ["nombre", "llamadas", "total_ms", "media_ms", "p95_ms"])
    lineas += ["## Nodos más lentos", ""] + tabla(analisis["nodos_mas_lentos"], ["nombre", "llamadas", "total_ms", "media_ms", "p95_ms"])
    lineas += ["## Herramientas más lentas", ""] + tabla(analisis["herramientas_mas_lentas"], ["nombre", "llamadas", "total_ms", "media_ms", "p95_ms"])
    lineas += ["## Arranques en frío del modelo", ""] + tabla(analisis["arranques_en_frio"], ["ts", "carga_ms", "nodo"])
    lineas += ["## Solicitudes anómalas (> 2× mediana o > p95)", ""]
    lineas += tabla(analisis["anomalias"], ["ts", "duracion_ms", "intencion", "llamadas_llm", "entrada"])
    lineas += ["## Errores", ""] + tabla(analisis["errores"], ["ts", "tipo", "nombre", "error"])
    lineas += ["## Seguridad", ""] + tabla(analisis["seguridad_bloqueos"], ["ts", "motivo"])
    tps = analisis["tokens_por_s"]
    lineas += ["## Recursos", "", f"- Tokens/s del modelo: media {tps['media']} · p50 {tps['p50']}",
               f"- Tokens de entrada por llamada: {analisis['tokens_entrada_media']} · de salida: {analisis['tokens_salida_media']}",
               f"- Memoria máxima del proceso: {analisis['memoria_rss_mb_max']} MB", ""]
    return "\n".join(lineas)


def main() -> None:
    parser = argparse.ArgumentParser(description="Análisis de registros de observabilidad")
    parser.add_argument("--origen", help="archivo .jsonl o carpeta con eventos_*.jsonl")
    parser.add_argument("--proveedor", help="ollama, gemini o simulado (por defecto, el del .env)")
    parser.add_argument("--modo", help="filtrar por modo del benchmark: base u optimizado")
    args = parser.parse_args()

    if args.origen:
        origen = Path(args.origen)
        origen = origen if origen.is_absolute() else RAIZ / origen
    else:
        proveedor = args.proveedor
        if not proveedor:
            from agente import modelos
            proveedor = modelos.proveedor()
        origen = RAIZ / "evidencias" / "observabilidad" / proveedor / "eventos.jsonl"
    eventos = cargar_eventos(origen)
    if not eventos:
        print(f"No hay eventos en {origen}. Ejecuta primero: python src/evaluar_observabilidad.py")
        return
    destino = origen if origen.is_dir() else origen.parent
    resultados = {}
    modos = [args.modo] if args.modo else sorted({e.get("modo") for e in eventos if e.get("modo")}) or [None]
    textos = []
    for modo in modos:
        subconjunto = [e for e in eventos if modo is None or e.get("modo") == modo]
        analisis = analizar_eventos(subconjunto)
        resultados[modo or "todos"] = analisis
        textos.append(informe(analisis, modo or "todos los eventos"))
        print(f"\n== {modo or 'todos'} ==")
        for h in hallazgos_en_texto(analisis):
            print(f"- {h}")
    (destino / "hallazgos_logs.md").write_text("\n\n".join(textos), encoding="utf-8")
    (destino / "hallazgos_logs.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nInforme: {destino / 'hallazgos_logs.md'}")


if __name__ == "__main__":
    main()
