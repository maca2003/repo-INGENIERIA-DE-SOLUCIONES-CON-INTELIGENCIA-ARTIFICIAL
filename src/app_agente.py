"""Interfaz web de AduanaAgent (Streamlit).

Ejecutar:  streamlit run src/app_agente.py
"""

import uuid

import pandas as pd
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from agente import configuracion_hilo, crear_agente

st.set_page_config(page_title="AduanaAgent", page_icon="📦", layout="wide")


@st.cache_resource(show_spinner="Iniciando el agente y los modelos locales...")
def obtener_agente(modo: str):
    return crear_agente(modo)


with st.sidebar:
    st.header("Configuración")
    modo = st.radio("Modelo", ["ollama", "simulado"], help="'simulado' funciona sin Ollama (solo pruebas).")
    if "hilo" not in st.session_state:
        st.session_state.hilo = "web-" + uuid.uuid4().hex[:6]
    hilo = st.text_input("Hilo de conversación (memoria corta)", st.session_state.hilo)
    st.session_state.hilo = hilo
    if st.button("Nuevo hilo", use_container_width=True):
        st.session_state.hilo = "web-" + uuid.uuid4().hex[:6]
        st.rerun()
    st.caption("Ejemplos")
    for ejemplo in ["Revisa la OP1003", "Revisa la OP1004", "Prioriza la cola de revisión",
                    "Llegó la lista de empaque corregida de la OP1003, reprocésala",
                    "¿Qué observaciones tiene la OP1003?"]:
        st.code(ejemplo, language=None)

try:
    grafo, servicios = obtener_agente(modo)
except Exception as error:
    st.error(f"No fue posible iniciar el agente: {error}")
    st.info("Inicia Ollama y crea la base vectorial con: python src/crear_base_vectorial.py")
    st.stop()

cfg = configuracion_hilo(st.session_state.hilo)
st.title("📦 AduanaAgent")
st.caption("Agente de revisión documental aduanera · LangGraph + LangChain + ChromaDB + Ollama · caso académico simulado")

chat, panel = st.columns([3, 2])
estado = grafo.get_state(cfg)
valores = estado.values

with chat:
    for mensaje in valores.get("messages", []):
        if isinstance(mensaje, HumanMessage):
            st.chat_message("user").markdown(mensaje.content)
        elif isinstance(mensaje, AIMessage) and mensaje.content:
            st.chat_message("assistant").markdown(mensaje.content)

    if estado.interrupts:
        pausa = estado.interrupts[0].value
        with st.container(border=True):
            st.warning(f"Aprobación requerida – {pausa['operacion_id']}")
            st.text(pausa["borrador"])
            col1, col2 = st.columns(2)
            if col1.button("✅ Aprobar envío", use_container_width=True):
                grafo.invoke(Command(resume="aprobar"), cfg)
                st.rerun()
            if col2.button("❌ Rechazar", use_container_width=True):
                grafo.invoke(Command(resume="rechazar"), cfg)
                st.rerun()

    if texto := st.chat_input("Escribe una instrucción o pregunta", disabled=bool(estado.interrupts)):
        with st.spinner("El agente está trabajando..."):
            grafo.invoke({"messages": [HumanMessage(content=texto)]}, cfg)
        st.rerun()

with panel:
    pestañas = st.tabs(["Plan", "Decisiones", "Memoria", "Trazabilidad"])
    with pestañas[0]:
        plan = valores.get("plan", [])
        if plan:
            st.markdown(f"**Operación:** {valores.get('operacion_id')} · "
                        f"**Estado:** {(valores.get('estado_final') or {}).get('estado', 'en curso')}")
            filas = sorted(plan, key=lambda t: (t.get("orden_ejecucion") or 99, t["secuencia"]))
            st.dataframe(pd.DataFrame([{"orden": t.get("orden_ejecucion"), "tarea": t["id"], "acción": t["accion"],
                                        "prioridad": t["prioridad"], "estado": t["estado"], "resultado": t["resultado"]}
                                       for t in filas]), hide_index=True, use_container_width=True)
        else:
            st.info("Aún no hay un plan en este hilo.")
    with pestañas[1]:
        for d in valores.get("decisiones", []):
            st.markdown(f"- **{d['paso']}** · {d['condicion']}  \n  → {d['decision']} _{d['regla']}_")
    with pestañas[2]:
        st.markdown("**Recuerdos usados en la última solicitud**")
        for r in valores.get("recuerdos", []):
            st.markdown(f"- `{r['tipo']}` {r['texto']} (distancia {r['distancia']})")
        if valores.get("resumen_conversacion"):
            st.markdown("**Resumen compactado del hilo**")
            st.caption(valores["resumen_conversacion"])
        st.metric("Memorias de largo plazo", servicios.memoria.cantidad())
    with pestañas[3]:
        registros = servicios.almacen.leer_trazabilidad(valores.get("operacion_id") or None)
        if registros:
            st.dataframe(pd.DataFrame(registros[-30:]), hide_index=True, use_container_width=True)
