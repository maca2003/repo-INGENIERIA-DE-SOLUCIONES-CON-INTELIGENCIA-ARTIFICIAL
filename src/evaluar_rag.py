import json
import sys
import unicodedata
from pathlib import Path

from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.prompts import ChatPromptTemplate


# Rutas del proyecto
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_PREGUNTAS = RAIZ_PROYECTO / "tests" / "preguntas_evaluacion.json"
RUTA_CHROMA = RAIZ_PROYECTO / "chroma_db"
RUTA_RESULTADOS = RAIZ_PROYECTO / "evidencias" / "resultados_evaluacion.json"

MODELO_LLM = "llama3.2:3b"
MODELO_EMBEDDINGS = "qwen3-embedding:0.6b"
NOMBRE_COLECCION = "aduanarag"
CANTIDAD_FRAGMENTOS = 4

MENSAJE_SIN_INFORMACION = (
    "No existe información suficiente en las fuentes disponibles "
    "para responder con seguridad."
)


PROMPT = ChatPromptTemplate.from_messages(
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
        ("human", "{pregunta}"),
    ]
)


def normalizar(texto):
    """Convierte el texto a minúsculas y elimina tildes."""
    texto = texto.lower()
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )


def cargar_preguntas():
    """Carga las preguntas almacenadas en el archivo JSON."""
    if not RUTA_PREGUNTAS.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de preguntas: {RUTA_PREGUNTAS}"
        )

    with RUTA_PREGUNTAS.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def crear_componentes():
    """Inicializa embeddings, ChromaDB y el modelo de lenguaje."""
    embeddings = OllamaEmbeddings(model=MODELO_EMBEDDINGS)

    base_vectorial = Chroma(
        collection_name=NOMBRE_COLECCION,
        embedding_function=embeddings,
        persist_directory=str(RUTA_CHROMA),
    )

    modelo = ChatOllama(
        model=MODELO_LLM,
        temperature=0,
    )

    cadena = PROMPT | modelo
    return base_vectorial, cadena


def evaluar_pregunta(caso, base_vectorial, cadena):
    """Ejecuta una pregunta y calcula sus comprobaciones automáticas."""
    documentos = base_vectorial.similarity_search(
        caso["pregunta"],
        k=CANTIDAD_FRAGMENTOS,
    )

    contexto = "\n\n".join(
        f"Fuente: {documento.metadata.get('fuente', 'desconocida')}\n"
        f"Contenido: {documento.page_content}"
        for documento in documentos
    )

    respuesta = cadena.invoke(
        {
            "contexto": contexto,
            "pregunta": caso["pregunta"],
        }
    ).content.strip()

    fuentes_recuperadas = list(
        dict.fromkeys(
            documento.metadata.get("fuente", "desconocida")
            for documento in documentos
        )
    )

    respuesta_normalizada = normalizar(respuesta)

    palabras_encontradas = [
        palabra
        for palabra in caso["palabras_clave"]
        if normalizar(palabra) in respuesta_normalizada
    ]

    cobertura_palabras = (
        len(palabras_encontradas) / len(caso["palabras_clave"])
        if caso["palabras_clave"]
        else 0
    )

    if caso["categoria"] == "sin_respuesta":
        rechazo_correcto = (
            "no existe informacion" in respuesta_normalizada
            and "responder con seguridad" in respuesta_normalizada
        )
        fuente_correcta = True
        resultado_correcto = rechazo_correcto
    else:
        rechazo_correcto = None
        fuente_correcta = caso["fuente_esperada"] in fuentes_recuperadas
        resultado_correcto = fuente_correcta and cobertura_palabras == 1.0

    return {
        "id": caso["id"],
        "categoria": caso["categoria"],
        "pregunta": caso["pregunta"],
        "respuesta": respuesta,
        "fuente_esperada": caso["fuente_esperada"],
        "fuentes_recuperadas": fuentes_recuperadas,
        "palabras_clave": caso["palabras_clave"],
        "palabras_encontradas": palabras_encontradas,
        "cobertura_palabras": round(cobertura_palabras, 2),
        "fuente_correcta": fuente_correcta,
        "rechazo_correcto": rechazo_correcto,
        "resultado_correcto": resultado_correcto,
    }


def mostrar_resultado(resultado):
    """Muestra en consola el resultado de cada prueba."""
    estado = "APROBADA" if resultado["resultado_correcto"] else "REVISAR"

    print("\n" + "=" * 70)
    print(
        f"PRUEBA {resultado['id']} | "
        f"{resultado['categoria'].upper()} | {estado}"
    )
    print("=" * 70)
    print(f"Pregunta: {resultado['pregunta']}")
    print(f"\nRespuesta:\n{resultado['respuesta']}")
    print("\nFuentes recuperadas:")

    for fuente in resultado["fuentes_recuperadas"]:
        print(f"- {fuente}")

    if resultado["categoria"] == "sin_respuesta":
        print(
            "\nControl de alucinación: "
            f"{'CORRECTO' if resultado['rechazo_correcto'] else 'REVISAR'}"
        )
    else:
        print(
            "\nFuente esperada recuperada: "
            f"{'SÍ' if resultado['fuente_correcta'] else 'NO'}"
        )
        print(
            "Palabras clave encontradas: "
            f"{len(resultado['palabras_encontradas'])}/"
            f"{len(resultado['palabras_clave'])}"
        )


def mostrar_resumen(resultados):
    """Calcula y muestra las métricas generales."""
    total = len(resultados)
    aprobadas = sum(
        resultado["resultado_correcto"] for resultado in resultados
    )

    casos_con_fuente = [
        resultado
        for resultado in resultados
        if resultado["categoria"] != "sin_respuesta"
    ]

    fuentes_correctas = sum(
        resultado["fuente_correcta"] for resultado in casos_con_fuente
    )

    casos_sin_respuesta = [
        resultado
        for resultado in resultados
        if resultado["categoria"] == "sin_respuesta"
    ]

    rechazos_correctos = sum(
        resultado["rechazo_correcto"] for resultado in casos_sin_respuesta
    )

    porcentaje_general = (aprobadas / total) * 100 if total else 0
    precision_fuentes = (
        fuentes_correctas / len(casos_con_fuente) * 100
        if casos_con_fuente
        else 0
    )
    control_alucinaciones = (
        rechazos_correctos / len(casos_sin_respuesta) * 100
        if casos_sin_respuesta
        else 0
    )

    print("\n" + "=" * 70)
    print("RESUMEN DE LA EVALUACIÓN")
    print("=" * 70)
    print(f"Pruebas ejecutadas: {total}")
    print(f"Pruebas aprobadas: {aprobadas}")
    print(f"Pruebas para revisar: {total - aprobadas}")
    print(f"Resultado general: {porcentaje_general:.1f}%")
    print(f"Recuperación de fuente esperada: {precision_fuentes:.1f}%")
    print(f"Control de alucinaciones: {control_alucinaciones:.1f}%")
    print(f"Resultados guardados en: {RUTA_RESULTADOS}")


def main():
    print("EVALUACIÓN AUTOMÁTICA DE ADUANARAG")
    print("=" * 70)
    print("Esta prueba puede tardar algunos minutos.")

    preguntas = cargar_preguntas()
    base_vectorial, cadena = crear_componentes()
    resultados = []

    for caso in preguntas:
        print(f"\nProcesando pregunta {caso['id']} de {len(preguntas)}...")

        try:
            resultado = evaluar_pregunta(
                caso,
                base_vectorial,
                cadena,
            )
            resultados.append(resultado)
            mostrar_resultado(resultado)

        except Exception as error:
            print(f"ERROR en la pregunta {caso['id']}: {error}")
            resultados.append(
                {
                    "id": caso["id"],
                    "categoria": caso["categoria"],
                    "pregunta": caso["pregunta"],
                    "error": str(error),
                    "resultado_correcto": False,
                }
            )

    RUTA_RESULTADOS.parent.mkdir(parents=True, exist_ok=True)

    with RUTA_RESULTADOS.open("w", encoding="utf-8") as archivo:
        json.dump(
            resultados,
            archivo,
            ensure_ascii=False,
            indent=2,
        )

    mostrar_resumen(resultados)


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as error:
        print(f"\nERROR: {error}")
        sys.exit(1)
    except Exception as error:
        print(f"\nERROR INESPERADO: {error}")
        print("Comprueba que Ollama esté iniciado y que chroma_db exista.")
        sys.exit(1)