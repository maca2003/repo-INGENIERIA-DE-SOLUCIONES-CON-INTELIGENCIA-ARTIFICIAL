"""Cálculo de métricas y análisis de registros de observabilidad (EP3).

Lo usan el benchmark (evaluar_observabilidad.py), el analizador de logs
(analizar_logs.py) y el dashboard (dashboard_observabilidad.py).
"""

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


# ----------------------------------------------------------------- utilidades
def cargar_eventos(origen: Path) -> list[dict]:
    """Lee un archivo .jsonl o todos los eventos_*.jsonl de una carpeta."""
    origen = Path(origen)
    archivos = sorted(origen.glob("*.jsonl")) if origen.is_dir() else [origen]
    eventos = []
    for archivo in archivos:
        if not archivo.exists():
            continue
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if linea.strip():
                eventos.append(json.loads(linea))
    return eventos


def percentil(valores: list[float], p: float) -> float | None:
    datos = sorted(v for v in valores if v is not None)
    if not datos:
        return None
    if len(datos) == 1:
        return round(datos[0], 1)
    posicion = (len(datos) - 1) * p / 100
    inferior = int(posicion)
    superior = min(inferior + 1, len(datos) - 1)
    return round(datos[inferior] + (datos[superior] - datos[inferior]) * (posicion - inferior), 1)


def estadisticas(valores: list[float]) -> dict:
    datos = [v for v in valores if v is not None]
    if not datos:
        return {"n": 0, "media": None, "p50": None, "p95": None, "max": None}
    return {"n": len(datos), "media": round(statistics.mean(datos), 1), "p50": percentil(datos, 50),
            "p95": percentil(datos, 95), "max": round(max(datos), 1)}


def jaccard(a: str, b: str) -> float:
    pa, pb = set(a.lower().split()), set(b.lower().split())
    if not pa and not pb:
        return 1.0
    return len(pa & pb) / len(pa | pb)


# -------------------------------------------------------- métricas por casos
def metricas_de_casos(casos: list[dict]) -> dict:
    """Precisión, consistencia, errores y latencia a partir de los casos del benchmark.

    Cada caso: {modo, repeticion, caso, tipo, correcto, firma, respuesta, error,
    latencia_ms, llamadas_llm, tokens_entrada, tokens_salida, cpu_ms, rss_mb}
    """
    resultado = {}
    for modo in sorted({c["modo"] for c in casos}):
        del_modo = [c for c in casos if c["modo"] == modo]
        por_tipo = defaultdict(list)
        for c in del_modo:
            por_tipo[c["tipo"]].append(c)

        # Consistencia: mismo resultado en todas las repeticiones de un caso.
        grupos = defaultdict(list)
        for c in del_modo:
            grupos[c["caso"]].append(c)
        repetidos = {k: v for k, v in grupos.items() if len(v) > 1}
        consistentes = [k for k, v in repetidos.items() if len({x["firma"] for x in v}) == 1]
        similitudes = []
        for v in repetidos.values():
            textos = [x.get("respuesta") or "" for x in v]
            similitudes += [jaccard(textos[0], t) for t in textos[1:]]

        primera = [c for c in del_modo if c.get("primera_consulta")]
        resultado[modo] = {
            "casos": len(del_modo),
            "repeticiones": max(c["repeticion"] for c in del_modo),
            "precision": round(100 * sum(c["correcto"] for c in del_modo) / len(del_modo), 1),
            "precision_por_tipo": {t: round(100 * sum(c["correcto"] for c in v) / len(v), 1) for t, v in por_tipo.items()},
            "consistencia": round(100 * len(consistentes) / len(repetidos), 1) if repetidos else None,
            "similitud_textual": round(100 * statistics.mean(similitudes), 1) if similitudes else None,
            "frecuencia_errores": round(100 * sum(1 for c in del_modo if c.get("error")) / len(del_modo), 1),
            "latencia_ms": estadisticas([c["latencia_ms"] for c in del_modo]),
            "latencia_por_tipo_ms": {t: estadisticas([c["latencia_ms"] for c in v]) for t, v in por_tipo.items()},
            "primera_consulta_ms": primera[0]["latencia_ms"] if primera else None,
            "llamadas_llm_promedio": round(statistics.mean(c["llamadas_llm"] for c in del_modo), 2),
            "tokens_promedio": round(statistics.mean(c["tokens_entrada"] + c["tokens_salida"] for c in del_modo), 1),
            "cpu_ms_promedio": round(statistics.mean(c.get("cpu_ms") or 0 for c in del_modo), 1),
            "rss_mb_max": max((c.get("rss_mb") or 0) for c in del_modo),
            "casos_incorrectos": sorted({c["caso"] for c in del_modo if not c["correcto"]}),
        }
    if "base" in resultado and "optimizado" in resultado:
        base, opt = resultado["base"], resultado["optimizado"]
        resultado["comparacion"] = {
            "reduccion_latencia_media_pct": _reduccion(base["latencia_ms"]["media"], opt["latencia_ms"]["media"]),
            "reduccion_latencia_p95_pct": _reduccion(base["latencia_ms"]["p95"], opt["latencia_ms"]["p95"]),
            "reduccion_por_tipo_pct": {
                t: _reduccion(base["latencia_por_tipo_ms"][t]["media"], opt["latencia_por_tipo_ms"].get(t, {}).get("media"))
                for t in base["latencia_por_tipo_ms"]},
            "reduccion_llamadas_llm_pct": _reduccion(base["llamadas_llm_promedio"], opt["llamadas_llm_promedio"]),
            "diferencia_precision_pp": round(opt["precision"] - base["precision"], 1),
        }
    return resultado


def _reduccion(antes, despues):
    if not antes or despues is None:
        return None
    return round(100 * (antes - despues) / antes, 1)


# ------------------------------------------------------- análisis de registros
def analizar_eventos(eventos: list[dict]) -> dict:
    """Detecta cuellos de botella, arranques en frío, errores y anomalías."""
    solicitudes = [e for e in eventos if e["tipo"] == "solicitud"]
    llm = [e for e in eventos if e["tipo"] == "llm"]
    herramientas = [e for e in eventos if e["tipo"] == "herramienta"]
    nodos = [e for e in eventos if e["tipo"] == "nodo"]
    recuperaciones = [e for e in eventos if e["tipo"] == "recuperacion"]

    total_ms = sum(e.get("duracion_ms") or 0 for e in solicitudes) or 1
    llm_ms = sum(e.get("duracion_ms") or 0 for e in llm)
    # Las herramientas que llaman al RAG ya se cuentan en LLM y recuperación.
    con_rag = {"consultar_procedimientos", "evaluar_requisitos_especiales", "fundamentar_hallazgos"}
    herramientas_ms = sum(e.get("duracion_ms") or 0 for e in herramientas if e["nombre"] not in con_rag)
    recuperacion_ms = sum(e.get("duracion_ms") or 0 for e in recuperaciones)

    def ranking(lista, clave="nombre"):
        grupos = defaultdict(list)
        for e in lista:
            grupos[e.get(clave) or "?"].append(e.get("duracion_ms") or 0)
        filas = [{"nombre": k, "llamadas": len(v), "total_ms": round(sum(v), 1), "media_ms": round(sum(v) / len(v), 1),
                  "p95_ms": percentil(v, 95)} for k, v in grupos.items()]
        return sorted(filas, key=lambda f: -f["total_ms"])

    llm_por_nodo = ranking(llm, "nodo")
    frios = [e for e in llm if (e.get("carga_modelo_ms") or 0) > 1000]
    latencias = [e.get("duracion_ms") or 0 for e in solicitudes]
    mediana = statistics.median(latencias) if latencias else 0
    p95 = percentil(latencias, 95) or 0
    anomalias = [e for e in solicitudes if (e.get("duracion_ms") or 0) > max(2 * mediana, p95) and len(solicitudes) >= 5]
    errores = [e for e in eventos if e.get("estado") == "error"]
    rag = [e for e in herramientas if e["nombre"] == "consultar_procedimientos"]
    abstenciones = [e for e in rag if (e.get("resultado") or {}).get("suficiente") is False]
    seguridad = [e for e in eventos if e["tipo"] == "seguridad"]
    tps = [e["tokens_por_s"] for e in llm if e.get("tokens_por_s")]

    return {
        "solicitudes": len(solicitudes),
        "latencia_solicitud_ms": estadisticas(latencias),
        "reparto_tiempo_pct": {
            "llm": round(100 * llm_ms / total_ms, 1),
            "recuperacion_chroma": round(100 * recuperacion_ms / total_ms, 1),
            "herramientas_sin_llm": round(100 * herramientas_ms / total_ms, 1),
            "orquestacion_y_resto": round(max(0.0, 100 - 100 * (llm_ms + recuperacion_ms + herramientas_ms) / total_ms), 1),
        },
        "llamadas_llm": len(llm),
        "llm_por_nodo": llm_por_nodo,
        "nodos_mas_lentos": ranking(nodos)[:8],
        "herramientas_mas_lentas": ranking(herramientas)[:8],
        "arranques_en_frio": [{"ts": e["ts"], "carga_ms": e["carga_modelo_ms"], "nodo": e.get("nodo")} for e in frios],
        "tokens_por_s": estadisticas(tps),
        "tokens_entrada_media": round(statistics.mean(e.get("tokens_entrada") or 0 for e in llm), 1) if llm else None,
        "tokens_salida_media": round(statistics.mean(e.get("tokens_salida") or 0 for e in llm), 1) if llm else None,
        "anomalias": [{"ts": e["ts"], "duracion_ms": e["duracion_ms"], "intencion": e.get("intencion"),
                       "entrada": e.get("entrada"), "llamadas_llm": e.get("llamadas_llm")} for e in anomalias],
        "errores": [{"ts": e["ts"], "tipo": e["tipo"], "nombre": e["nombre"], "error": e.get("error")} for e in errores],
        "errores_por_componente": dict(Counter(f"{e['tipo']}:{e['nombre']}" for e in errores)),
        "rag_consultas": len(rag),
        "rag_abstenciones": len(abstenciones),
        "seguridad_bloqueos": [{"ts": e["ts"], "motivo": e.get("motivo")} for e in seguridad],
        "intenciones": dict(Counter(e.get("intencion") for e in solicitudes)),
        "memoria_rss_mb_max": max((e.get("rss_mb") or 0) for e in solicitudes) if solicitudes else None,
    }


def hallazgos_en_texto(analisis: dict) -> list[str]:
    """Traduce el análisis a hallazgos legibles (para el informe y el dashboard)."""
    h = []
    reparto = analisis["reparto_tiempo_pct"]
    h.append(f"El LLM concentra el {reparto['llm']} % del tiempo total de las solicitudes; la recuperación en "
             f"ChromaDB, el {reparto['recuperacion_chroma']} %.")
    if analisis["llm_por_nodo"]:
        top = analisis["llm_por_nodo"][0]
        h.append(f"El nodo que más tiempo de LLM consume es «{top['nombre']}» ({top['llamadas']} llamadas, "
                 f"{top['total_ms']} ms en total, media {top['media_ms']} ms).")
    if analisis["arranques_en_frio"]:
        cargas = [a["carga_ms"] for a in analisis["arranques_en_frio"]]
        h.append(f"Se detectaron {len(cargas)} arranques en frío del modelo (carga de hasta {max(cargas)} ms).")
    if analisis["anomalias"]:
        h.append(f"{len(analisis['anomalias'])} solicitudes superan el doble de la mediana o el p95 de latencia.")
    if analisis["errores"]:
        h.append(f"Se registraron {len(analisis['errores'])} errores: {analisis['errores_por_componente']}.")
    else:
        h.append("No se registraron errores de herramientas ni del modelo.")
    if analisis["rag_consultas"]:
        h.append(f"El RAG se abstuvo en {analisis['rag_abstenciones']} de {analisis['rag_consultas']} consultas.")
    if analisis["seguridad_bloqueos"]:
        h.append(f"El guardarraíl bloqueó {len(analisis['seguridad_bloqueos'])} entradas antes de llegar al modelo.")
    return h
