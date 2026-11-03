from pathlib import Path

from langchain_chroma import Chroma

from agente import modelos

from cargar_documentos import cargar_todos_los_documentos
from fragmentar_documentos import fragmentar_documentos


RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
# chroma_db/ con Ollama o chroma_db_gemini/ con Gemini (ver .env).
CARPETA_BASE_VECTORIAL = modelos.carpeta_chroma(RAIZ_PROYECTO)

NOMBRE_COLECCION = "aduanarag"


def obtener_modelo_embeddings():
    return modelos.crear_embeddings()


def obtener_base_vectorial() -> Chroma:
    return Chroma(
        collection_name=NOMBRE_COLECCION,
        embedding_function=obtener_modelo_embeddings(),
        persist_directory=str(CARPETA_BASE_VECTORIAL),
    )


def crear_base_vectorial() -> Chroma:
    print("Cargando documentos...")
    documentos = cargar_todos_los_documentos()

    print("Fragmentando documentos...")
    fragmentos = fragmentar_documentos(documentos)

    print("Generando embeddings y almacenando fragmentos...")
    base_vectorial = obtener_base_vectorial()

    identificadores = [
        f"fragmento-{fragmento.metadata['fragmento_id']}"
        for fragmento in fragmentos
    ]

    base_vectorial.add_documents(
        documents=fragmentos,
        ids=identificadores,
    )

    cantidad_guardada = base_vectorial._collection.count()

    print("\nBASE VECTORIAL CREADA CORRECTAMENTE")
    print("=" * 55)
    print(f"Documentos originales: {len(documentos)}")
    print(f"Fragmentos procesados: {len(fragmentos)}")
    print(f"Registros almacenados: {cantidad_guardada}")
    print(f"Proveedor y modelos: {modelos.describir()}")
    print(f"Ubicación: {CARPETA_BASE_VECTORIAL}")

    return base_vectorial


def probar_busqueda(base_vectorial: Chroma) -> None:
    pregunta = (
        "¿Qué diferencia existe entre una agencia de aduanas "
        "y el Servicio Nacional de Aduanas?"
    )

    print("\nPRUEBA DE BÚSQUEDA SEMÁNTICA")
    print("=" * 55)
    print(f"Pregunta: {pregunta}")

    resultados = base_vectorial.similarity_search_with_score(
        pregunta,
        k=3,
    )

    for posicion, (documento, distancia) in enumerate(
        resultados,
        start=1,
    ):
        print(f"\nResultado {posicion}")
        print(f"Fuente: {documento.metadata['fuente']}")
        print(f"Tipo: {documento.metadata['tipo_fuente']}")
        print(f"Distancia: {distancia:.4f}")
        print("Contenido:")
        print(documento.page_content)


if __name__ == "__main__":
    base = crear_base_vectorial()
    probar_busqueda(base)