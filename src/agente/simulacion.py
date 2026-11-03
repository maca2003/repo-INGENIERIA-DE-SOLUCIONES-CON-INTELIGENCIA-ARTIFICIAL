"""Componentes simulados para ejecutar el agente sin Ollama.

Se usan en las pruebas automáticas (pytest / GitHub Actions) y en el modo
--simulado de los scripts. No reemplazan a los modelos reales: permiten
verificar de forma reproducible la orquestación, la memoria, la planificación
y las herramientas, que son deterministas.
"""

import hashlib
import json
import math
import re
import unicodedata
import uuid
from pathlib import Path
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import MENSAJE_SIN_INFORMACION

PALABRAS_VACIAS = {
    "a", "al", "ante", "con", "de", "del", "el", "en", "es", "la", "las", "lo", "los", "o", "para",
    "por", "que", "qué", "se", "si", "su", "sus", "un", "una", "y", "como", "cómo", "cual", "cuál",
    "debe", "deben", "existe", "existen", "hacer", "entre", "sobre", "son", "esta", "este", "le",
    "les", "no", "mas", "más", "ser", "hay", "dice", "segun", "según",
}


def tokens(texto: str) -> list[str]:
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    palabras = re.findall(r"[a-z0-9]+", texto)
    return [p[:6] for p in palabras if p not in PALABRAS_VACIAS and len(p) > 2]


class EmbeddingsLexicos(Embeddings):
    """Embeddings deterministas por hashing de palabras (bolsa de palabras)."""

    def __init__(self, dimensiones: int = 384):
        self.dimensiones = dimensiones

    def _vector(self, texto: str) -> list[float]:
        vector = [0.0] * self.dimensiones
        for palabra in tokens(texto):
            indice = int(hashlib.md5(palabra.encode()).hexdigest(), 16) % self.dimensiones
            vector[indice] += 1.0
        norma = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norma for v in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class RecuperadorLexico:
    """Recuperador por coincidencia de términos sobre la misma base documental."""

    def __init__(self, carpeta_datos: Path):
        separador = RecursiveCharacterTextSplitter(
            chunk_size=800, chunk_overlap=120,
            separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
        )
        documentos = []
        for subcarpeta, tipo in (("internos", "interna_simulada"), ("externos", "externa_oficial")):
            for archivo in sorted((carpeta_datos / subcarpeta).glob("*.md")):
                documentos.append(Document(
                    page_content=archivo.read_text(encoding="utf-8"),
                    metadata={"fuente": archivo.name, "tipo_fuente": tipo},
                ))
        self.fragmentos = separador.split_documents(documentos)
        self._tokens = [set(tokens(f.page_content)) for f in self.fragmentos]

    def __call__(self, pregunta: str, k: int) -> list[tuple[Document, float]]:
        consulta = set(tokens(pregunta))
        if not consulta:
            return []
        puntajes = []
        for fragmento, conjunto in zip(self.fragmentos, self._tokens):
            cobertura = len(consulta & conjunto) / len(consulta)
            puntajes.append((fragmento, round(2 * (1 - cobertura), 4)))
        puntajes.sort(key=lambda par: par[1])
        return puntajes[:k]


class ModeloSimulado(BaseChatModel):
    """Modelo de chat determinista que imita las respuestas necesarias.

    * Prompt RAG: respuesta extractiva desde el contexto o abstención.
    * Agente con herramientas: elige una herramienta por palabras clave y
      luego resume el resultado.
    * Síntesis y compactación: resumen breve del contenido recibido.
    """

    herramientas: list[str] = []
    respuestas_forzadas: list[str] = []

    @property
    def _llm_type(self) -> str:
        return "modelo-simulado"

    def bind_tools(self, tools, **kwargs):  # noqa: D401
        nombres = [getattr(t, "name", None) or t.get("name") for t in tools]
        return self.model_copy(update={"herramientas": nombres})

    # ------------------------------------------------------------------
    def _generate(self, messages: list[BaseMessage], stop=None,
                  run_manager: CallbackManagerForLLMRun | None = None, **kwargs: Any) -> ChatResult:
        if self.respuestas_forzadas:
            mensaje = AIMessage(content=self.respuestas_forzadas.pop(0))
        else:
            mensaje = self._responder(messages)
        return ChatResult(generations=[ChatGeneration(message=mensaje)])

    def _responder(self, messages: list[BaseMessage]) -> AIMessage:
        sistema = next((m.content for m in messages if isinstance(m, SystemMessage)), "")
        ultimo = messages[-1]

        if "Eres AduanaRAG" in sistema:
            return AIMessage(content=self._respuesta_rag(sistema, ultimo.content))
        if "[SINTESIS]" in sistema:
            return AIMessage(content="(Modo simulado) " + ultimo.content.split("\n\n")[0][:600])
        if "[COMPACTACION]" in sistema:
            return AIMessage(content="Resumen de la conversación previa: " + ultimo.content[:400])
        if self.herramientas:
            if isinstance(ultimo, ToolMessage):
                return AIMessage(content=f"Resultado de {ultimo.name}:\n{str(ultimo.content)[:700]}")
            activa = re.search(r"Operación activa en esta conversación: (OP\d{4})", sistema)
            return self._elegir_herramienta(ultimo.content, activa.group(1) if activa else "")
        return AIMessage(content="Respuesta simulada.")

    @staticmethod
    def _respuesta_rag(sistema: str, pregunta: str) -> str:
        contexto = sistema.split("Contexto:", 1)[-1]
        consulta = set(tokens(pregunta))
        mejores = []
        for linea in contexto.splitlines():
            linea = linea.strip(" -*#>")
            if len(linea) < 15 or linea.startswith(("Fuente:", "Tipo:", "[Fragmento")):
                continue
            coincidencias = len(consulta & set(tokens(linea)))
            mejores.append((coincidencias, linea))
        mejores.sort(key=lambda par: -par[0])
        if not mejores or mejores[0][0] < 3:
            return MENSAJE_SIN_INFORMACION
        return " ".join(linea for _, linea in mejores[:2])

    def _elegir_herramienta(self, texto: str, activa: str = "") -> AIMessage:
        bajo = texto.lower()
        operacion = re.search(r"op\s?-?(\d{4})", bajo)
        op = f"OP{operacion.group(1)}" if operacion else activa
        es_procedimiento = any(p in bajo for p in ("qué debe", "que debe", "cómo", "como se", "procedimiento", "qué dice"))
        if "recuerda" in bajo and "guardar_memoria" in self.herramientas:
            cliente = re.search(r"cliente ([A-ZÁÉÍÓÚÑ][\wáéíóúñ]+(?: [A-ZÁÉÍÓÚÑ][\wáéíóúñ.]+)*)", texto)
            contacto = re.search(r" a ([A-ZÁÉÍÓÚÑ][\wáéíóúñ]+ [A-ZÁÉÍÓÚÑ][\wáéíóúñ]+)\s*$", texto.strip())
            nombre, argumentos = "guardar_memoria", {
                "texto": texto.replace("Recuerda que el", "Preferencia:").strip(), "tipo": "preferencia",
                "cliente": cliente.group(1) if cliente else "",
                "contacto": contacto.group(1) if contacto else "",
            }
        elif any(p in bajo for p in ("antecedente", "preferencia", "historial")) and "buscar_memoria" in self.herramientas:
            cliente = re.search(r"([A-ZÁÉÍÓÚÑ][\wáéíóúñ]+(?: [A-ZÁÉÍÓÚÑ][\wáéíóúñ.]+)+ (?:Ltda|SpA))", texto)
            nombre, argumentos = "buscar_memoria", {"consulta": texto, "cliente": cliente.group(1) if cliente else ""}
        elif not es_procedimiento and ("observacion" in bajo or "observación" in bajo):
            nombre, argumentos = "listar_observaciones", {"operacion_id": op}
        elif op and ("estado" in bajo or "expediente" in bajo):
            nombre, argumentos = "obtener_expediente", {"operacion_id": op}
        elif "prioridad" in bajo or "priori" in bajo or "cola" in bajo:
            nombre, argumentos = "priorizar_operaciones", {}
        else:
            nombre, argumentos = "consultar_procedimientos", {"pregunta": texto}
        if nombre not in self.herramientas:
            return AIMessage(content="No tengo una herramienta adecuada para esa solicitud.")
        return AIMessage(content="", tool_calls=[{
            "name": nombre, "args": argumentos, "id": f"call_{uuid.uuid4().hex[:8]}", "type": "tool_call",
        }])


def a_json(datos) -> str:
    return json.dumps(datos, ensure_ascii=False, indent=2)
