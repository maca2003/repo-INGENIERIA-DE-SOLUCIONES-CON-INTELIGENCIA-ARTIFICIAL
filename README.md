# AduanaRAG

AduanaRAG es un prototipo académico de asistente inteligente para realizar consultas sobre procedimientos y documentación aduanera.

El sistema utiliza generación aumentada por recuperación (RAG) para buscar información en documentos internos simulados y fuentes públicas oficiales. Las respuestas se generan mediante modelos locales ejecutados con Ollama, sin utilizar una API externa de pago.

## Objetivo

Facilitar la consulta de procedimientos y antecedentes aduaneros mediante un asistente documental capaz de:

- Recuperar fragmentos relacionados con una pregunta.
- Generar respuestas basadas en documentos disponibles.
- Identificar las fuentes utilizadas.
- Diferenciar documentos internos simulados y fuentes externas oficiales.
- Evitar respuestas cuando no existe información suficiente.
- Ejecutarse localmente sin enviar documentos a servicios externos.

## Advertencia

Este proyecto fue desarrollado con fines exclusivamente académicos.

Las respuestas son informativas y no reemplazan:

- La normativa aduanera vigente.
- La revisión de un agente de aduana.
- La evaluación de un profesional responsable.
- Las instrucciones del Servicio Nacional de Aduanas.

Los documentos internos incluidos son simulados y no contienen información confidencial de clientes ni de operaciones reales.

## Tecnologías utilizadas

- Python 3.12
- Streamlit
- LangChain
- ChromaDB
- Ollama
- Llama 3.2 3B
- Qwen3 Embedding 0.6B
- Git y GitHub

## Modelos locales

El proyecto utiliza los siguientes modelos mediante Ollama:

```text
llama3.2:3b
qwen3-embedding:0.6b
```

El primer modelo genera las respuestas y el segundo transforma los fragmentos documentales en vectores para realizar búsquedas semánticas.

## Arquitectura general

El flujo principal del sistema es:

1. Se cargan los documentos internos y externos.
2. Los documentos se dividen en fragmentos.
3. Los fragmentos se convierten en embeddings.
4. Los embeddings se almacenan en ChromaDB.
5. El usuario escribe una pregunta.
6. El sistema recupera los cuatro fragmentos más relacionados.
7. El modelo local recibe la pregunta y el contexto recuperado.
8. Se genera una respuesta limitada a las fuentes disponibles.
9. La interfaz muestra la respuesta y las fuentes recuperadas.

## Estructura del proyecto

```text
aduanarag/
├── data/
│   ├── externos/
│   └── internos/
├── documentacion/
├── evidencias/
├── src/
│   ├── app.py
│   ├── cargar_documentos.py
│   ├── consultar_rag.py
│   ├── crear_base_vectorial.py
│   ├── evaluar_rag.py
│   ├── fragmentar_documentos.py
│   └── probar_modelos.py
├── tests/
│   └── preguntas_evaluacion.json
├── .gitignore
├── README.md
└── requirements.txt
```

La carpeta `chroma_db` se genera localmente y no se publica en GitHub.

## Requisitos previos

Antes de ejecutar el proyecto se necesita:

- Windows 10 u 11.
- Python 3.12.
- Git.
- Ollama.
- Visual Studio Code, recomendado.
- Al menos 8 GB de memoria RAM.

## Instalación

### 1. Clonar el repositorio

```cmd
git clone https://github.com/maca2003repo-INGENIERIA-DE-SOLUCIONES-CON-INTELIGENCIA-ARTIFICIAL
cd aduanarag
```

### 2. Crear el entorno virtual

```cmd
py -3.12 -m venv .venv
```

### 3. Activar el entorno virtual

```cmd
.venv\Scripts\activate
```

### 4. Instalar las dependencias

```cmd
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 5. Descargar los modelos de Ollama

```cmd
ollama pull llama3.2:3b
ollama pull qwen3-embedding:0.6b
```

### 6. Comprobar los modelos

```cmd
ollama list
python src\probar_modelos.py
```

## Preparar la base vectorial

La base de datos vectorial no se descarga desde GitHub. Cada integrante debe generarla localmente.

### Comprobar la carga documental

```cmd
python src\cargar_documentos.py
```

### Comprobar la fragmentación

```cmd
python src\fragmentar_documentos.py
```

### Crear ChromaDB

```cmd
python src\crear_base_vectorial.py
```

Este comando genera localmente la carpeta:

```text
chroma_db/
```

## Ejecutar consultas desde la terminal

```cmd
python src\consultar_rag.py
```

Para cerrar el asistente interactivo:

```text
/salir
```

## Ejecutar la interfaz web

```cmd
streamlit run src\app.py
```

La aplicación estará disponible normalmente en:

```text
http://localhost:8501
```

Para detener Streamlit se debe presionar `Ctrl + C` en la terminal.

## Evaluación automática

El proyecto incluye una batería controlada de diez preguntas:

- Cinco preguntas sobre documentos internos simulados.
- Tres preguntas sobre fuentes externas oficiales.
- Dos preguntas sin respuesta documental para comprobar el control de alucinaciones.

Para ejecutar la evaluación:

```cmd
python src\evaluar_rag.py
```

En la prueba final se obtuvieron los siguientes resultados:

| Indicador | Resultado |
|---|---:|
| Pruebas ejecutadas | 10 |
| Pruebas aprobadas | 10 |
| Resultado general | 100 % |
| Recuperación de fuente esperada | 100 % |
| Control de alucinaciones | 100 % |

Estos resultados corresponden exclusivamente a la batería controlada incluida en el proyecto y no implican precisión universal ante cualquier pregunta.

Los resultados detallados se almacenan en:

```text
evidencias/resultados_evaluacion.json
```

## Fuentes documentales

El prototipo utiliza dos tipos de documentos:

### Documentos internos simulados

- Procedimiento de recepción de documentos.
- Gestión de observaciones de una operación.
- Trazabilidad y seguridad documental.

### Fuentes externas oficiales

Se utilizan síntesis académicas basadas en información pública del Servicio Nacional de Aduanas de Chile sobre:

- Requisitos generales de importación.
- Rol del agente de aduana.

Cada documento externo conserva la referencia de su página oficial y la fecha de consulta.

## Seguridad y limitaciones

AduanaRAG no debe:

- Inventar información ausente en las fuentes.
- Modificar documentos.
- Autorizar operaciones.
- Sustituir la revisión profesional.
- Entregar información confidencial.
- Presentar respuestas como asesoría legal definitiva.

Si las fuentes no permiten contestar una pregunta con seguridad, el sistema informa que no existe información suficiente.

## Trabajo colaborativo

El proyecto utiliza Git y GitHub para:

- Mantener el historial de cambios.
- Compartir el código entre los integrantes.
- Separar archivos versionados y archivos locales.
- Registrar avances mediante commits.
- Evitar publicar el entorno virtual y la base vectorial local.