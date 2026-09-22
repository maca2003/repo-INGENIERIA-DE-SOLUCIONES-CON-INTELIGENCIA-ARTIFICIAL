from collections import Counter

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from cargar_documentos import cargar_todos_los_documentos


TAMANO_FRAGMENTO = 800
SUPERPOSICION = 120


def fragmentar_documentos(
    documentos: list[Document],
) -> list[Document]:
    fragmentador = RecursiveCharacterTextSplitter(
        chunk_size=TAMANO_FRAGMENTO,
        chunk_overlap=SUPERPOSICION,
        length_function=len,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
    )

    fragmentos = fragmentador.split_documents(documentos)

    for numero, fragmento in enumerate(fragmentos):
        fragmento.metadata["fragmento_id"] = numero
        fragmento.metadata["tamano_fragmento"] = len(
            fragmento.page_content
        )

    return fragmentos


def mostrar_resultados(
    documentos: list[Document],
    fragmentos: list[Document],
) -> None:
    print("\nRESULTADO DE LA FRAGMENTACION")
    print("=" * 55)
    print(f"Documentos originales: {len(documentos)}")
    print(f"Fragmentos generados: {len(fragmentos)}")
    print(f"Tamaño máximo configurado: {TAMANO_FRAGMENTO}")
    print(f"Superposición configurada: {SUPERPOSICION}")

    conteo_por_fuente = Counter(
        fragmento.metadata["fuente"]
        for fragmento in fragmentos
    )

    print("\nFRAGMENTOS POR DOCUMENTO")

    for fuente, cantidad in sorted(conteo_por_fuente.items()):
        print(f"- {fuente}: {cantidad} fragmentos")

    print("\nEJEMPLO DEL PRIMER FRAGMENTO")
    print("-" * 55)

    if fragmentos:
        primero = fragmentos[0]

        print(f"ID: {primero.metadata['fragmento_id']}")
        print(f"Fuente: {primero.metadata['fuente']}")
        print(f"Tipo: {primero.metadata['tipo_fuente']}")
        print(f"Caracteres: {len(primero.page_content)}")
        print("\nContenido:")
        print(primero.page_content)
        print("\nFRAGMENTACION CORRECTA")
    else:
        print("NO SE GENERARON FRAGMENTOS")


if __name__ == "__main__":
    documentos_cargados = cargar_todos_los_documentos()
    fragmentos_generados = fragmentar_documentos(
        documentos_cargados
    )

    mostrar_resultados(
        documentos_cargados,
        fragmentos_generados,
    )