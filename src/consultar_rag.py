from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from crear_base_vectorial import obtener_base_vectorial


MODELO_LLM = "llama3.2:3b"
CANTIDAD_FRAGMENTOS = 4

MENSAJE_SIN_INFORMACION = (
    "No existe información suficiente en las fuentes "
    "disponibles para responder con seguridad."
)


PROMPT_RAG = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Eres AduanaRAG, un asistente de consulta documental aduanera.

Debes responder únicamente con la información incluida en el contexto.

Reglas obligatorias:
1. Responde únicamente con información incluida en el contexto.
2. No inventes información ni uses conocimiento externo.
3. Identifica la sección del contexto que responda de manera más directa la pregunta.
4. Contesta exactamente lo consultado y no reemplaces la respuesta por información de otra sección relacionada.
5. Incluye todos los elementos relevantes que aparezcan en esa sección.
6. Respeta estrictamente las negaciones del contexto. Nunca elimines ni cambies palabras como "no", "nunca", "solo" o "hasta".
7. Si la pregunta solicita qué debe comunicarse al cliente, prioriza la sección relacionada con comunicación y no la sección de registro interno.
8. Si el contexto no permite responder con seguridad, responde exactamente:
   "No existe información suficiente en las fuentes disponibles para responder con seguridad."
9. Entrega una respuesta clara, breve y en español.
10. No presentes la respuesta como asesoría legal definitiva.

Contexto:
{contexto}
            """,
        ),
        (
            "human",
            "{pregunta}",
        ),
    ]
)


def recuperar_fragmentos(
    pregunta: str,
) -> list[Document]:
    """Busca en ChromaDB los fragmentos más relacionados con la pregunta."""

    base_vectorial = obtener_base_vectorial()

    fragmentos = base_vectorial.similarity_search(
        pregunta,
        k=CANTIDAD_FRAGMENTOS,
    )

    return fragmentos


def preparar_contexto(
    fragmentos: list[Document],
) -> str:
    """Convierte los fragmentos recuperados en el contexto del modelo."""

    bloques = []

    for numero, fragmento in enumerate(fragmentos, start=1):
        fuente = fragmento.metadata.get(
            "fuente",
            "fuente_desconocida",
        )

        tipo = fragmento.metadata.get(
            "tipo_fuente",
            "tipo_desconocido",
        )

        bloque = (
            f"[Fragmento {numero}]\n"
            f"Fuente: {fuente}\n"
            f"Tipo: {tipo}\n"
            f"Contenido:\n{fragmento.page_content}"
        )

        bloques.append(bloque)

    return "\n\n".join(bloques)


def consultar_rag(
    pregunta: str,
) -> dict:
    """Recupera información documental y genera una respuesta."""

    pregunta = pregunta.strip()

    if not pregunta:
        return {
            "respuesta": "Debes escribir una pregunta.",
            "fragmentos": [],
        }

    fragmentos = recuperar_fragmentos(pregunta)

    if not fragmentos:
        return {
            "respuesta": MENSAJE_SIN_INFORMACION,
            "fragmentos": [],
        }

    contexto = preparar_contexto(fragmentos)

    modelo = ChatOllama(
        model=MODELO_LLM,
        temperature=0,
    )

    cadena = PROMPT_RAG | modelo

    resultado = cadena.invoke(
        {
            "pregunta": pregunta,
            "contexto": contexto,
        }
    )

    respuesta = resultado.content.strip()

    if not respuesta:
        respuesta = MENSAJE_SIN_INFORMACION

    return {
        "respuesta": respuesta,
        "fragmentos": fragmentos,
    }


def obtener_fuentes_unicas(
    fragmentos: list[Document],
) -> list[dict]:
    """Obtiene las fuentes recuperadas sin repetir nombres."""

    fuentes = []
    nombres_agregados = set()

    for fragmento in fragmentos:
        fuente = fragmento.metadata.get(
            "fuente",
            "fuente_desconocida",
        )

        tipo = fragmento.metadata.get(
            "tipo_fuente",
            "tipo_desconocido",
        )

        if fuente not in nombres_agregados:
            fuentes.append(
                {
                    "fuente": fuente,
                    "tipo": tipo,
                }
            )

            nombres_agregados.add(fuente)

    return fuentes


def mostrar_resultado(
    pregunta: str,
    resultado: dict,
) -> None:
    """Muestra la respuesta y las fuentes recuperadas en la terminal."""

    print("\nCONSULTA RAG")
    print("=" * 60)
    print(f"Pregunta: {pregunta}")

    print("\nRESPUESTA DEL ASISTENTE")
    print("-" * 60)
    print(resultado["respuesta"])

    print("\nFUENTES RECUPERADAS")
    print("-" * 60)

    fuentes = obtener_fuentes_unicas(
        resultado["fragmentos"]
    )

    if not fuentes:
        print("- No se recuperaron fuentes.")
        return

    for fuente in fuentes:
        print(
            f"- {fuente['fuente']} "
            f"({fuente['tipo']})"
        )


def iniciar_consulta_interactiva() -> None:
    """Inicia el asistente interactivo desde la terminal."""

    print("Asistente documental AduanaRAG")
    print("Escribe /salir para terminar.\n")

    while True:
        pregunta_usuario = input("Pregunta: ").strip()

        if pregunta_usuario.lower() == "/salir":
            print("Consulta finalizada.")
            break

        if not pregunta_usuario:
            print("Debes escribir una pregunta.\n")
            continue

        try:
            resultado_consulta = consultar_rag(
                pregunta_usuario
            )

            mostrar_resultado(
                pregunta_usuario,
                resultado_consulta,
            )

        except Exception as error:
            print("\nNo fue posible procesar la consulta.")
            print(f"Detalle técnico: {error}")
            print(
                "Comprueba que Ollama esté iniciado y "
                "que la base vectorial exista."
            )

        print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    iniciar_consulta_interactiva()