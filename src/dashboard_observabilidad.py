"""Dashboard de observabilidad de AduanaAgent (EP3, IE4).

Ejecutar:  streamlit run src/dashboard_observabilidad.py

Fuentes de datos:
* Benchmark: evidencias/observabilidad/<proveedor>/ (src/evaluar_observabilidad.py)
* Uso en vivo: salidas/observabilidad/ (se llena al usar el agente)
"""

import json
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
from agente import config  # noqa: E402
from agente.analitica import analizar_eventos, cargar_eventos, hallazgos_en_texto  # noqa: E402

st.set_page_config(page_title="Observabilidad AduanaAgent", page_icon="📊", layout="wide")
COLORES = alt.Scale(domain=["base", "optimizado"], range=["#9AA5B1", "#2F6690"])


@st.cache_data(ttl=30)
def cargar_benchmark(carpeta: str):
    carpeta = Path(carpeta)
    metricas = json.loads((carpeta / "metricas.json").read_text(encoding="utf-8"))
    casos = pd.read_csv(carpeta / "casos.csv")
    eventos = cargar_eventos(carpeta / "eventos.jsonl")
    return metricas, casos, eventos


@st.cache_data(ttl=10)
def cargar_vivo(carpetas: tuple[str, ...]):
    eventos = []
    for carpeta in carpetas:
        eventos += cargar_eventos(Path(carpeta))
    return eventos


# ------------------------------------------------------------------ barra lateral
with st.sidebar:
    st.header("Fuente de datos")
    benchmarks = sorted(p.name for p in (RAIZ / "evidencias" / "observabilidad").glob("*") if (p / "metricas.json").exists())
    opciones = [f"Benchmark · {b}" for b in benchmarks] + ["Uso en vivo (salidas/)"]
    fuente = st.radio("Origen", opciones, index=0)
    st.caption(f"Retención de registros: {config.RETENCION_LOGS_DIAS} días · datos personales enmascarados")
    if st.button("Recargar", width="stretch"):
        st.cache_data.clear()
        st.rerun()

st.title("📊 Observabilidad de AduanaAgent")

# ===================================================================== en vivo
if fuente.startswith("Uso en vivo"):
    carpetas = tuple(str(p) for p in [RAIZ / "salidas" / "observabilidad", RAIZ / "salidas" / "simulado" / "observabilidad"]
                     if p.exists())
    eventos = cargar_vivo(carpetas)
    if not eventos:
        st.info("Aún no hay registros. Usa el agente (streamlit run src/app_agente.py) y vuelve a esta página.")
        st.stop()
    analisis = analizar_eventos(eventos)
    lat = analisis["latencia_solicitud_ms"]
    c = st.columns(5)
    c[0].metric("Solicitudes", analisis["solicitudes"])
    c[1].metric("Latencia p50", f"{lat['p50']} ms")
    c[2].metric("Latencia p95", f"{lat['p95']} ms")
    c[3].metric("Errores", len(analisis["errores"]))
    c[4].metric("Bloqueos de seguridad", len(analisis["seguridad_bloqueos"]))
    sol = pd.DataFrame([e for e in eventos if e["tipo"] == "solicitud"])
    if not sol.empty:
        sol["ts"] = pd.to_datetime(sol["ts"])
        st.subheader("Latencia por solicitud")
        st.altair_chart(alt.Chart(sol).mark_circle(size=70).encode(
            x=alt.X("ts:T", title="Hora"), y=alt.Y("duracion_ms:Q", title="Latencia (ms)"),
            color=alt.Color("intencion:N", title="Intención"),
            tooltip=["ts", "intencion", "duracion_ms", "llamadas_llm", "entrada"]), width="stretch")
    st.subheader("Hallazgos")
    for h in hallazgos_en_texto(analisis):
        st.markdown(f"- {h}")
    st.subheader("Registros")
    tipos = st.multiselect("Tipo de evento", sorted({e["tipo"] for e in eventos}), default=["solicitud", "llm", "herramienta"])
    st.dataframe(pd.DataFrame([e for e in eventos if e["tipo"] in tipos]).iloc[::-1], hide_index=True, width="stretch")
    st.stop()

# ================================================================== benchmark
proveedor = fuente.split("· ", 1)[1]
metricas, casos, eventos = cargar_benchmark(str(RAIZ / "evidencias" / "observabilidad" / proveedor))
modos = [m for m in ("base", "optimizado") if m in metricas]
ctx = metricas["contexto"]
st.caption(f"Proveedor: {ctx['proveedor']} · {ctx['fecha']} · Python {ctx['python']} · {ctx['plataforma']} · "
           f"{len(casos)} ejecuciones de casos · {len(eventos)} eventos")

with st.sidebar:
    st.header("Filtros")
    modo_kpi = st.selectbox("Modo para los indicadores", modos, index=len(modos) - 1)
    tipos_sel = st.multiselect("Tipos de caso", sorted(casos["tipo"].unique()), default=sorted(casos["tipo"].unique()))

casos_f = casos[casos["tipo"].isin(tipos_sel)]
m = metricas[modo_kpi]
ref = metricas.get("base") if modo_kpi == "optimizado" else None


def delta(clave, sub=None, invertir=False):
    if not ref:
        return None
    a = ref[clave][sub] if sub else ref[clave]
    b = m[clave][sub] if sub else m[clave]
    if a is None or b is None:
        return None
    return round(b - a, 1)


k = st.columns(6)
k[0].metric("Precisión", f"{m['precision']} %", delta("precision"))
k[1].metric("Consistencia", f"{m['consistencia']} %" if m["consistencia"] is not None else "—")
k[2].metric("Frecuencia de errores", f"{m['frecuencia_errores']} %", delta("frecuencia_errores"), delta_color="inverse")
k[3].metric("Latencia p50", f"{m['latencia_ms']['p50']} ms", delta("latencia_ms", "p50"), delta_color="inverse")
k[4].metric("Latencia p95", f"{m['latencia_ms']['p95']} ms", delta("latencia_ms", "p95"), delta_color="inverse")
k[5].metric("Llamadas al LLM por caso", m["llamadas_llm_promedio"], delta("llamadas_llm_promedio"), delta_color="inverse")
if ref:
    st.caption("Las variaciones comparan el modo optimizado con la línea base (comportamiento de la EP2).")

pestañas = st.tabs(["Resumen", "Latencia", "Precisión y consistencia", "Errores y registros", "Recursos", "Seguridad"])

# ------------------------------------------------------------------- resumen
with pestañas[0]:
    izq, der = st.columns([3, 2])
    with izq:
        st.subheader("Latencia media por tipo de caso")
        filas = [{"modo": md, "tipo": t, "media_ms": v["media"], "p95_ms": v["p95"]}
                 for md in modos for t, v in metricas[md]["latencia_por_tipo_ms"].items() if t in tipos_sel]
        st.altair_chart(alt.Chart(pd.DataFrame(filas)).mark_bar().encode(
            x=alt.X("tipo:N", title=None), xOffset="modo:N", y=alt.Y("media_ms:Q", title="Latencia media (ms)"),
            color=alt.Color("modo:N", scale=COLORES), tooltip=["modo", "tipo", "media_ms", "p95_ms"]), width="stretch")
    with der:
        st.subheader("Hallazgos del análisis de registros")
        for h in hallazgos_en_texto(analizar_eventos([e for e in eventos if e.get("modo") == modo_kpi])):
            st.markdown(f"- {h}")
        if "comparacion" in metricas:
            c = metricas["comparacion"]
            st.success(f"Optimizado vs base: latencia media −{c['reduccion_latencia_media_pct']} % · "
                       f"llamadas al LLM −{c['reduccion_llamadas_llm_pct']} % · "
                       f"precisión {c['diferencia_precision_pp']:+} pp")
    st.subheader("Indicadores por modo")
    tabla = pd.DataFrame({md: {"Precisión (%)": metricas[md]["precision"], "Consistencia (%)": metricas[md]["consistencia"],
                               "Similitud textual (%)": metricas[md]["similitud_textual"],
                               "Errores (%)": metricas[md]["frecuencia_errores"],
                               "Latencia media (ms)": metricas[md]["latencia_ms"]["media"],
                               "Latencia p95 (ms)": metricas[md]["latencia_ms"]["p95"],
                               "Primera consulta (ms)": metricas[md]["primera_consulta_ms"],
                               "Llamadas LLM/caso": metricas[md]["llamadas_llm_promedio"],
                               "Tokens/caso": metricas[md]["tokens_promedio"]} for md in modos})
    st.dataframe(tabla, width="stretch")

# ------------------------------------------------------------------- latencia
with pestañas[1]:
    st.subheader("Distribución de latencia por tipo de caso")
    st.altair_chart(alt.Chart(casos_f).mark_boxplot(extent="min-max").encode(
        x=alt.X("tipo:N", title=None), xOffset="modo:N", y=alt.Y("latencia_ms:Q", title="Latencia (ms)", scale=alt.Scale(type="symlog")),
        color=alt.Color("modo:N", scale=COLORES)), width="stretch")
    st.subheader("Latencia de cada caso")
    st.altair_chart(alt.Chart(casos_f).mark_circle(size=60).encode(
        x=alt.X("caso:N", title=None, sort=None), y=alt.Y("latencia_ms:Q", title="Latencia (ms)"),
        color=alt.Color("modo:N", scale=COLORES), tooltip=["modo", "repeticion", "caso", "latencia_ms", "llamadas_llm", "firma"]),
        width="stretch")
    eventos_modo = [e for e in eventos if e.get("modo") == modo_kpi]
    analisis = analizar_eventos(eventos_modo)
    a, b = st.columns(2)
    with a:
        st.subheader(f"Reparto del tiempo · {modo_kpi}")
        reparto = pd.DataFrame([{"componente": k2, "porcentaje": v} for k2, v in analisis["reparto_tiempo_pct"].items()])
        st.altair_chart(alt.Chart(reparto).mark_bar().encode(
            x=alt.X("porcentaje:Q", title="% del tiempo total"), y=alt.Y("componente:N", sort="-x", title=None),
            tooltip=["componente", "porcentaje"]), width="stretch")
    with b:
        st.subheader(f"Tiempo de LLM por nodo · {modo_kpi}")
        if analisis["llm_por_nodo"]:
            st.altair_chart(alt.Chart(pd.DataFrame(analisis["llm_por_nodo"])).mark_bar().encode(
                x=alt.X("total_ms:Q", title="ms totales"), y=alt.Y("nombre:N", sort="-x", title=None),
                tooltip=["nombre", "llamadas", "total_ms", "media_ms", "p95_ms"]), width="stretch")
    st.subheader("Nodos y herramientas más lentos")
    c1, c2 = st.columns(2)
    c1.dataframe(pd.DataFrame(analisis["nodos_mas_lentos"]), hide_index=True, width="stretch")
    c2.dataframe(pd.DataFrame(analisis["herramientas_mas_lentas"]), hide_index=True, width="stretch")
    if analisis["arranques_en_frio"]:
        st.warning(f"Arranques en frío del modelo: {len(analisis['arranques_en_frio'])}")
        st.dataframe(pd.DataFrame(analisis["arranques_en_frio"]), hide_index=True)

# ------------------------------------------------------ precisión y consistencia
with pestañas[2]:
    a, b = st.columns(2)
    with a:
        st.subheader("Precisión por tipo de caso")
        filas = [{"modo": md, "tipo": t, "precision": v} for md in modos
                 for t, v in metricas[md]["precision_por_tipo"].items() if t in tipos_sel]
        st.altair_chart(alt.Chart(pd.DataFrame(filas)).mark_bar().encode(
            x=alt.X("tipo:N", title=None), xOffset="modo:N", y=alt.Y("precision:Q", title="Precisión (%)", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("modo:N", scale=COLORES), tooltip=["modo", "tipo", "precision"]), width="stretch")
    with b:
        st.subheader("Resultado por caso y repetición")
        mapa = casos_f.assign(resultado=casos_f["correcto"].map({True: "correcto", False: "incorrecto"}),
                              vuelta=casos_f["modo"] + " r" + casos_f["repeticion"].astype(str))
        st.altair_chart(alt.Chart(mapa).mark_rect().encode(
            x=alt.X("vuelta:N", title=None), y=alt.Y("caso:N", sort=None, title=None),
            color=alt.Color("resultado:N", scale=alt.Scale(domain=["correcto", "incorrecto"], range=["#2F6690", "#E8A33D"])),
            tooltip=["caso", "vuelta", "firma", "latencia_ms"]), width="stretch")
    st.subheader("Casos incorrectos")
    st.dataframe(casos_f[~casos_f["correcto"]][["modo", "repeticion", "caso", "tipo", "firma", "respuesta"]],
                 hide_index=True, width="stretch")

# ------------------------------------------------------- errores y registros
with pestañas[3]:
    analisis = analizar_eventos([e for e in eventos if e.get("modo") == modo_kpi])
    st.metric("Eventos con error", len(analisis["errores"]))
    if analisis["errores"]:
        st.dataframe(pd.DataFrame(analisis["errores"]), hide_index=True, width="stretch")
    st.subheader("Solicitudes anómalas (> 2× mediana o > p95)")
    st.dataframe(pd.DataFrame(analisis["anomalias"]), hide_index=True, width="stretch")
    st.subheader("Explorador de registros")
    df = pd.DataFrame(eventos)
    f1, f2, f3 = st.columns(3)
    tipo_ev = f1.multiselect("Tipo", sorted(df["tipo"].unique()), default=["solicitud", "llm", "herramienta"])
    estado_ev = f2.multiselect("Estado", sorted(df["estado"].dropna().unique()), default=sorted(df["estado"].dropna().unique()))
    caso_ev = f3.selectbox("Caso", ["(todos)"] + sorted(df["caso"].dropna().unique()))
    vista = df[df["tipo"].isin(tipo_ev) & (df["estado"].isin(estado_ev) | df["estado"].isna())]
    if caso_ev != "(todos)":
        vista = vista[vista["caso"] == caso_ev]
    columnas = [c for c in ["ts", "modo", "caso", "tipo", "nombre", "nodo", "duracion_ms", "estado", "tokens_entrada",
                            "tokens_salida", "carga_modelo_ms", "error", "entrada"] if c in vista.columns]
    st.dataframe(vista[columnas], hide_index=True, width="stretch")

# ------------------------------------------------------------------- recursos
with pestañas[4]:
    llm = pd.DataFrame([e for e in eventos if e["tipo"] == "llm"])
    a, b, c = st.columns(3)
    vueltas = ctx.get("vueltas", [])
    pre = [v["precalentamiento_s"] for v in vueltas if v.get("precalentamiento_s")]
    a.metric("Precalentamiento de modelos", f"{pre[0]} s" if pre else "—")
    b.metric("Memoria máx. del proceso", f"{m['rss_mb_max']} MB")
    c.metric("CPU por caso", f"{m['cpu_ms_promedio']} ms")
    modelos_mem = [x for v in vueltas for x in v.get("memoria_modelos", [])]
    if modelos_mem:
        st.subheader("Memoria de los modelos en Ollama")
        st.dataframe(pd.DataFrame(modelos_mem).drop_duplicates("modelo"), hide_index=True)
    if not llm.empty and "tokens_por_s" in llm.columns and llm["tokens_por_s"].notna().any():
        st.subheader("Velocidad de generación (tokens/s)")
        st.altair_chart(alt.Chart(llm.dropna(subset=["tokens_por_s"])).mark_bar().encode(
            x=alt.X("tokens_por_s:Q", bin=alt.Bin(maxbins=20), title="tokens/s"), y=alt.Y("count()", title="llamadas"),
            color=alt.Color("modo:N", scale=COLORES)), width="stretch")
        st.subheader("Tokens por llamada al LLM")
        st.altair_chart(alt.Chart(llm).mark_circle(size=60).encode(
            x=alt.X("tokens_entrada:Q", title="tokens de entrada"), y=alt.Y("duracion_ms:Q", title="duración (ms)"),
            color=alt.Color("modo:N", scale=COLORES), tooltip=["modo", "caso", "nodo", "tokens_entrada", "tokens_salida", "duracion_ms"]),
            width="stretch")
    st.subheader("CPU y memoria por caso")
    st.altair_chart(alt.Chart(casos_f).mark_circle(size=60).encode(
        x=alt.X("cpu_ms:Q", title="CPU (ms)"), y=alt.Y("rss_mb:Q", title="Memoria del proceso (MB)", scale=alt.Scale(zero=False)),
        color=alt.Color("modo:N", scale=COLORES), tooltip=["modo", "caso", "cpu_ms", "rss_mb"]), width="stretch")

# ------------------------------------------------------------------- seguridad
with pestañas[5]:
    bloqueos = [e for e in eventos if e["tipo"] == "seguridad"]
    seg = casos[casos["tipo"] == "seguridad"]
    a, b, c = st.columns(3)
    a.metric("Entradas bloqueadas", len(bloqueos))
    b.metric("Casos de seguridad bloqueados", f"{round(100 * seg['correcto'].mean(), 1) if len(seg) else 0} %")
    c.metric("Retención de registros", f"{config.RETENCION_LOGS_DIAS} días")
    st.dataframe(pd.DataFrame(bloqueos)[["ts", "modo", "caso", "motivo", "entrada"]] if bloqueos else pd.DataFrame(),
                 hide_index=True, width="stretch")
    st.markdown("""
**Protocolos activos**
- Datos personales (RUT, correo, teléfono, tarjeta) enmascarados antes de escribir cualquier registro.
- Guardarraíl de entrada: largo máximo, patrones de inyección de instrucciones y solicitudes de autorizar operaciones.
- Modelos locales (Ollama): los expedientes no salen del equipo.
- Aprobación humana obligatoria antes de comunicar al cliente; las observaciones críticas se escalan.
- Rotación diaria de registros y eliminación automática después del período de retención.
""")
