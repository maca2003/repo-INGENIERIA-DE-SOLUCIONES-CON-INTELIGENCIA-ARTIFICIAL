"""Configuración central del agente AduanaAgent.

Todos los parámetros pueden sobrescribirse mediante variables de entorno
(archivo .env) para ajustar el agente sin modificar el código.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent.parent
load_dotenv(RAIZ_PROYECTO / ".env")


def _entero(nombre: str, defecto: int) -> int:
    return int(os.getenv(nombre, defecto))


def _decimal(nombre: str, defecto: float) -> float:
    return float(os.getenv(nombre, defecto))


# Proveedor de modelos: "ollama" (local, por defecto) o "gemini" (API).
PROVEEDOR = os.getenv("AGENTE_PROVEEDOR", "ollama")

# Modelos locales (Ollama). Se mantienen los modelos de la EP1.
MODELO_LLM = os.getenv("AGENTE_MODELO_LLM", "llama3.2:3b")
MODELO_EMBEDDINGS = os.getenv("AGENTE_MODELO_EMBEDDINGS", "qwen3-embedding:0.6b")
TEMPERATURA = _decimal("AGENTE_TEMPERATURA", 0.0)

# Gemini (opcional). El nombre del modelo cambia con frecuencia: si aparece
# "model not found", revisar https://ai.google.dev/gemini-api/docs/models
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
MODELO_LLM_GEMINI = os.getenv("LLM_MODEL", "gemini-3.8-flash")
MODELO_EMBEDDINGS_GEMINI = os.getenv("AGENTE_MODELO_EMBEDDINGS_GEMINI", "models/gemini-embedding-001")

# Base de conocimiento creada en la EP1 (colección ChromaDB "aduanarag").
COLECCION_CONOCIMIENTO = "aduanarag"
COLECCION_MEMORIA = "memoria_agente"

# Recuperación semántica.
FRAGMENTOS_RAG = _entero("AGENTE_FRAGMENTOS_RAG", 4)
# Distancia L2 máxima aceptada para considerar que un fragmento respalda una
# respuesta. Se calibra con src/calibrar_umbral.py.
UMBRAL_DISTANCIA_RAG = _decimal("AGENTE_UMBRAL_DISTANCIA_RAG", 1.40)
RECUERDOS_POR_CONSULTA = _entero("AGENTE_RECUERDOS_POR_CONSULTA", 4)
UMBRAL_DISTANCIA_MEMORIA = _decimal("AGENTE_UMBRAL_DISTANCIA_MEMORIA", 1.60)

# Memoria de corto plazo.
MAX_MENSAJES_HILO = _entero("AGENTE_MAX_MENSAJES_HILO", 12)
MENSAJES_CONSERVADOS = _entero("AGENTE_MENSAJES_CONSERVADOS", 6)

# Planificación y control.
MAX_PASOS_FLUJO = _entero("AGENTE_MAX_PASOS_FLUJO", 30)
MAX_REINTENTOS_HERRAMIENTA = _entero("AGENTE_MAX_REINTENTOS", 1)
# Diferencia porcentual de valor a partir de la cual se considera
# "inconsistencia importante en el valor declarado" (INT-002).
UMBRAL_DIFERENCIA_VALOR = _decimal("AGENTE_UMBRAL_DIFERENCIA_VALOR", 0.05)

# Rendimiento (EP3). AGENTE_OPTIMIZADO=false reproduce la versión EP2 (línea
# base) para comparar latencias con src/evaluar_observabilidad.py.
OPTIMIZADO = os.getenv("AGENTE_OPTIMIZADO", "true").strip().lower() in ("1", "true", "si", "sí")
# Tiempo que Ollama mantiene el modelo cargado en memoria entre consultas.
def _segundos(valor: str) -> int:
    """Convierte '30m', '1h', '90s' o '1800' a segundos (OllamaEmbeddings exige un entero)."""
    valor = valor.strip().lower()
    unidades = {"s": 1, "m": 60, "h": 3600}
    if valor and valor[-1] in unidades:
        return int(float(valor[:-1]) * unidades[valor[-1]])
    return int(valor)


KEEP_ALIVE = _segundos(os.getenv("AGENTE_KEEP_ALIVE", "30m"))
# Máximo de tokens generados por respuesta y ventana de contexto.
NUM_PREDICT = _entero("AGENTE_NUM_PREDICT", 320)
NUM_CTX = _entero("AGENTE_NUM_CTX", 4096)

# Observabilidad y privacidad (EP3).
OBSERVABILIDAD = os.getenv("AGENTE_OBSERVABILIDAD", "true").strip().lower() in ("1", "true", "si", "sí")
RETENCION_LOGS_DIAS = _entero("AGENTE_RETENCION_LOGS_DIAS", 30)
MAX_LARGO_ENTRADA = _entero("AGENTE_MAX_LARGO_ENTRADA", 1000)

# Fecha usada para priorizar la cola (AAAA-MM-DD). Vacía = fecha actual.
FECHA_REFERENCIA = os.getenv("AGENTE_FECHA_REFERENCIA", "")

USUARIO_AGENTE = "agente_revision_aduanaagent"

MENSAJE_SIN_INFORMACION = (
    "No existe información suficiente en las fuentes "
    "disponibles para responder con seguridad."
)


@dataclass
class Rutas:
    """Ubicaciones de lectura y escritura del agente."""

    raiz: Path = RAIZ_PROYECTO
    operaciones: Path = field(default_factory=lambda: RAIZ_PROYECTO / "data" / "operaciones")
    memoria_inicial: Path = field(
        default_factory=lambda: RAIZ_PROYECTO / "data" / "memoria_inicial" / "memorias_semilla.json"
    )
    chroma: Path = field(default_factory=lambda: RAIZ_PROYECTO / "chroma_db")
    salidas: Path = field(default_factory=lambda: RAIZ_PROYECTO / "salidas")

    @property
    def checkpoints(self) -> Path:
        return self.salidas / "memoria_corto_plazo.sqlite"

    @property
    def memoria_larga(self) -> Path:
        return self.salidas / "memoria_largo_plazo"

    @property
    def expedientes_trabajo(self) -> Path:
        return self.salidas / "expedientes"

    @property
    def registro_observaciones(self) -> Path:
        return self.salidas / "registro_observaciones.json"

    @property
    def estados_operaciones(self) -> Path:
        return self.salidas / "estados_operaciones.json"

    @property
    def trazabilidad(self) -> Path:
        return self.salidas / "trazabilidad.jsonl"

    def carpeta_operacion(self, operacion_id: str) -> Path:
        carpeta = self.salidas / operacion_id
        carpeta.mkdir(parents=True, exist_ok=True)
        return carpeta
