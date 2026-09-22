import streamlit as st

from consultar_rag import consultar_rag


st.set_page_config(
    page_title="AduanaRAG",
    page_icon="📦",
    layout="centered",
)


st.title("📦 AduanaRAG")

st.subheader(
    "Asistente inteligente para consultas documentales aduaneras"
)

st.info(
    "Este prototipo utiliza documentos internos simulados y "
    "fuentes públicas oficiales. Sus respuestas son informativas "
    "y no reemplazan la revisión de un profesional."
)


with st.form("formulario_consulta"):
    pregunta = st.text_area(
        "Escribe tu consulta:",
        placeholder=(
            "Ejemplo: ¿Qué diferencia existe entre una agencia "
            "de aduanas y el Servicio Nacional de Aduanas?"
        ),
        height=120,
    )

    consultar = st.form_submit_button(
        "Consultar documentos",
        use_container_width=True,
    )


if consultar:
    pregunta_limpia = pregunta.strip()

    if not pregunta_limpia:
        st.warning("Debes escribir una pregunta.")
    else:
        with st.spinner(
            "Buscando información y generando respuesta..."
        ):
            try:
                resultado = consultar_rag(
                    pregunta_limpia
                )

                st.success("Consulta procesada correctamente")

                st.markdown("### Respuesta")
                st.markdown(resultado["respuesta"])

                st.markdown("### Fuentes recuperadas")

                fuentes_mostradas = set()

                for fragmento in resultado["fragmentos"]:
                    fuente = fragmento.metadata.get(
                        "fuente",
                        "Fuente desconocida",
                    )

                    tipo = fragmento.metadata.get(
                        "tipo_fuente",
                        "Tipo desconocido",
                    )

                    if fuente in fuentes_mostradas:
                        continue

                    fuentes_mostradas.add(fuente)

                    etiqueta_tipo = {
                        "interna_simulada": (
                            "Documento interno simulado"
                        ),
                        "externa_oficial": (
                            "Fuente externa oficial"
                        ),
                    }.get(tipo, tipo)

                    with st.expander(
                        f"📄 {fuente}"
                    ):
                        st.write(
                            f"**Tipo:** {etiqueta_tipo}"
                        )
                        st.write(
                            fragmento.page_content
                        )

            except Exception as error:
                st.error(
                    "No fue posible procesar la consulta."
                )

                st.exception(error)


st.divider()

st.caption(
    "Proyecto académico desarrollado con Python, Streamlit, "
    "LangChain, ChromaDB y modelos locales mediante Ollama."
)