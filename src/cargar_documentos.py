from pathlib import Path

from langchain_core.documents import Document


# Obtiene la carpeta principal del proyecto sin depender
# del lugar desde donde se ejecute el programa.
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

CARPETA_INTERNOS = RAIZ_PROYECTO / "data" / "internos"
CARPETA_EXTERNOS = RAIZ_PROYECTO / "data" / "externos"


def cargar_archivos_markdown(carpeta: Path, tipo_fuente: str) -> list[Document]:
    documentos = []

    if not carpeta.exists():
        print(f"ADVERTENCIA: No existe la carpeta {carpeta}")
        return documentos

    for archivo in sorted(carpeta.glob("*.md")):
        contenido = archivo.read_text(encoding="utf-8")

        if not contenido.strip():
            print(f"ADVERTENCIA: El archivo {archivo.name} está vacío.")
            continue

        documento = Document(
            page_content=contenido,
            metadata={
                "fuente": archivo.name,
                "tipo_fuente": tipo_fuente,
                "ruta": str(archivo),
            },
        )

        documentos.append(documento)

    return documentos


def cargar_todos_los_documentos() -> list[Document]:
    documentos_internos = cargar_archivos_markdown(
        CARPETA_INTERNOS,
        "interna_simulada",
    )

    documentos_externos = cargar_archivos_markdown(
        CARPETA_EXTERNOS,
        "externa_oficial",
    )

    return documentos_internos + documentos_externos


def mostrar_resultados(documentos: list[Document]) -> None:
    print("\nRESULTADO DE LA CARGA")
    print("=" * 50)
    print(f"Total de documentos encontrados: {len(documentos)}")

    for numero, documento in enumerate(documentos, start=1):
        print(f"\nDocumento {numero}")
        print(f"Nombre: {documento.metadata['fuente']}")
        print(f"Tipo: {documento.metadata['tipo_fuente']}")
        print(f"Caracteres: {len(documento.page_content)}")

    if documentos:
        print("\nCARGA DE DOCUMENTOS CORRECTA")
    else:
        print("\nNO SE ENCONTRARON DOCUMENTOS")


if __name__ == "__main__":
    documentos_cargados = cargar_todos_los_documentos()
    mostrar_resultados(documentos_cargados)