"""Observabilidad del agente (EP3).

Un callback de LangChain registra en JSONL, sin intervenir en la lógica:

* solicitud    – cada mensaje del usuario: latencia total, intención, estado,
                 llamadas al LLM, tokens, CPU y memoria del proceso.
* nodo         – cada nodo del grafo LangGraph y su duración.
* herramienta  – cada herramienta @tool: duración, estado y resultado resumido.
* llm          – cada llamada al modelo: duración, tokens de entrada y salida,
                 tiempo de carga del modelo (arranque en frío) y tokens/s.
* recuperacion – cada búsqueda en ChromaDB (embeddings + similitud).
* seguridad    – entradas bloqueadas por el guardarraíl.

Los textos se enmascaran (seguridad.enmascarar) y los archivos se rotan por
día; los de más de RETENCION_LOGS_DIAS días se eliminan.
"""

import contextvars
import json
import threading
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from langchain_core.callbacks import BaseCallbackHandler

from . import config
from .seguridad import enmascarar

try:
    import psutil
    _PROCESO = psutil.Process()
except Exception:  # psutil es opcional
    psutil = None
    _PROCESO = None

_traza_actual: contextvars.ContextVar[str | None] = contextvars.ContextVar("traza_actual", default=None)


def _recursos() -> dict:
    if _PROCESO is None:
        return {}
    tiempos = _PROCESO.cpu_times()
    return {"rss_mb": round(_PROCESO.memory_info().rss / 1_048_576, 1),
            "cpu_s": round(tiempos.user + tiempos.system, 3)}


def _ns_a_ms(valor) -> float:
    return round((valor or 0) / 1_000_000, 1)


class Observador(BaseCallbackHandler):
    """Callback que convierte las ejecuciones del agente en eventos estructurados."""

    raise_error = False

    def __init__(self, carpeta: Path, retencion_dias: int = config.RETENCION_LOGS_DIAS):
        self.carpeta = Path(carpeta)
        self.carpeta.mkdir(parents=True, exist_ok=True)
        self.retencion_dias = retencion_dias
        self._lock = threading.Lock()
        self._inicio: dict[str, dict] = {}
        self._traza_de: dict[str, str] = {}
        self._totales: dict[str, dict] = {}
        self.eventos: list[dict] = []  # memoria de la ejecución actual (benchmark y pruebas)
        self.purgar_antiguos()

    # ------------------------------------------------------------ persistencia
    @property
    def archivo(self) -> Path:
        return self.carpeta / f"eventos_{date.today():%Y-%m-%d}.jsonl"

    def purgar_antiguos(self) -> int:
        """Política de retención: elimina registros con más de N días."""
        limite = date.today() - timedelta(days=self.retencion_dias)
        eliminados = 0
        for archivo in self.carpeta.glob("eventos_*.jsonl"):
            try:
                fecha = datetime.strptime(archivo.stem.split("_", 1)[1], "%Y-%m-%d").date()
            except ValueError:
                continue
            if fecha < limite:
                archivo.unlink()
                eliminados += 1
        return eliminados

    def registrar(self, tipo: str, nombre: str, **datos) -> dict:
        evento = {"ts": datetime.now().isoformat(timespec="milliseconds"), "tipo": tipo, "nombre": nombre,
                  "traza": datos.pop("traza", None) or _traza_actual.get(), **datos}
        with self._lock:
            self.eventos.append(evento)
            with self.archivo.open("a", encoding="utf-8") as f:
                f.write(json.dumps(evento, ensure_ascii=False, default=str) + "\n")
        return evento

    def reiniciar_memoria(self) -> None:
        with self._lock:
            self.eventos = []

    # ------------------------------------------------------------- utilidades
    def _abrir(self, run_id, parent_run_id, tipo: str, nombre: str, **extra) -> str:
        run, padre = str(run_id), str(parent_run_id) if parent_run_id else None
        traza = self._traza_de.get(padre) if padre else None
        if traza is None:
            traza = run if padre is None else (_traza_actual.get() or run)
        self._traza_de[run] = traza
        self._inicio[run] = {"t": time.perf_counter(), "tipo": tipo, "nombre": nombre, "traza": traza, **extra}
        return traza

    def _cerrar(self, run_id) -> dict | None:
        datos = self._inicio.pop(str(run_id), None)
        if datos:
            datos["duracion_ms"] = round((time.perf_counter() - datos.pop("t")) * 1000, 1)
        return datos

    def _acumular(self, traza: str, **valores) -> None:
        totales = self._totales.setdefault(traza, {})
        for clave, valor in valores.items():
            totales[clave] = totales.get(clave, 0) + (valor or 0)

    # ------------------------------------------------------------ cadenas/nodos
    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id=None, tags=None, metadata=None, **kwargs):
        nombre = kwargs.get("name") or (serialized or {}).get("name") or "cadena"
        metadata = metadata or {}
        if parent_run_id is None:  # solicitud del usuario
            traza = self._abrir(run_id, None, "solicitud", nombre, recursos=_recursos(),
                                hilo=metadata.get("thread_id"), entrada=self._texto_entrada(inputs))
            _traza_actual.set(traza)
            self._totales[traza] = {}
        elif metadata.get("langgraph_node") == nombre:
            self._abrir(run_id, parent_run_id, "nodo", nombre)
        else:
            self._traza_de[str(run_id)] = self._traza_de.get(str(parent_run_id), _traza_actual.get())

    def on_chain_end(self, outputs, *, run_id, parent_run_id=None, **kwargs):
        datos = self._cerrar(run_id)
        if not datos:
            return
        if datos["tipo"] == "solicitud":
            self._registrar_solicitud(datos, outputs, "ok")
        else:
            self.registrar("nodo", datos["nombre"], traza=datos["traza"], duracion_ms=datos["duracion_ms"], estado="ok")

    def on_chain_error(self, error, *, run_id, parent_run_id=None, **kwargs):
        datos = self._cerrar(run_id)
        if not datos:
            return
        pausa = "Interrupt" in type(error).__name__  # interrupt() de LangGraph: pausa, no error
        estado = "pausa" if pausa else "error"
        if datos["tipo"] == "solicitud":
            self._registrar_solicitud(datos, {}, estado, error=None if pausa else f"{type(error).__name__}: {error}")
        else:
            self.registrar("nodo", datos["nombre"], traza=datos["traza"], duracion_ms=datos["duracion_ms"],
                           estado=estado, error=None if pausa else enmascarar(f"{type(error).__name__}: {error}")[:300])

    def _registrar_solicitud(self, datos: dict, salidas, estado: str, error: str | None = None) -> None:
        antes, despues = datos.get("recursos", {}), _recursos()
        totales = self._totales.pop(datos["traza"], {})
        salidas = salidas if isinstance(salidas, dict) else {}
        estado_final = salidas.get("estado_final") or {}
        self.registrar(
            "solicitud", datos["nombre"], traza=datos["traza"], duracion_ms=datos["duracion_ms"], estado=estado,
            error=enmascarar(error)[:300] if error else None, hilo=datos.get("hilo"), entrada=datos.get("entrada"),
            intencion=salidas.get("intencion"), operacion=salidas.get("operacion_id"),
            estado_operacion=estado_final.get("estado") if isinstance(estado_final, dict) else None,
            llamadas_llm=int(totales.get("llamadas_llm", 0)), tokens_entrada=int(totales.get("tokens_entrada", 0)),
            tokens_salida=int(totales.get("tokens_salida", 0)), llm_ms=round(totales.get("llm_ms", 0), 1),
            herramientas_ms=round(totales.get("herramientas_ms", 0), 1), errores=int(totales.get("errores", 0)),
            rss_mb=despues.get("rss_mb"), cpu_ms=round((despues.get("cpu_s", 0) - antes.get("cpu_s", 0)) * 1000, 1),
        )

    @staticmethod
    def _texto_entrada(inputs) -> str:
        try:
            mensajes = inputs.get("messages") or []
            texto = mensajes[-1].content if hasattr(mensajes[-1], "content") else str(mensajes[-1])
        except Exception:
            texto = "(reanudación)" if inputs is not None else ""
        return enmascarar(texto)[:200]

    # -------------------------------------------------------------------- LLM
    def on_chat_model_start(self, serialized, messages, *, run_id, parent_run_id=None, tags=None, metadata=None, **kwargs):
        modelo = (kwargs.get("invocation_params") or {}).get("model") or (serialized or {}).get("name", "llm")
        nodo = (metadata or {}).get("langgraph_node")
        self._abrir(run_id, parent_run_id, "llm", str(modelo), nodo=nodo)

    def on_llm_end(self, response, *, run_id, parent_run_id=None, tags=None, **kwargs):
        datos = self._cerrar(run_id)
        if not datos:
            return
        meta, uso = {}, {}
        try:
            mensaje = response.generations[0][0].message
            meta = getattr(mensaje, "response_metadata", {}) or {}
            uso = getattr(mensaje, "usage_metadata", {}) or {}
        except Exception:
            pass
        entrada = meta.get("prompt_eval_count") or uso.get("input_tokens") or 0
        salida = meta.get("eval_count") or uso.get("output_tokens") or 0
        eval_ms = _ns_a_ms(meta.get("eval_duration"))
        self._acumular(datos["traza"], llamadas_llm=1, tokens_entrada=entrada, tokens_salida=salida,
                       llm_ms=datos["duracion_ms"])
        self.registrar("llm", datos["nombre"], traza=datos["traza"], duracion_ms=datos["duracion_ms"], estado="ok",
                       nodo=datos.get("nodo"), tokens_entrada=entrada, tokens_salida=salida,
                       carga_modelo_ms=_ns_a_ms(meta.get("load_duration")),
                       evaluacion_prompt_ms=_ns_a_ms(meta.get("prompt_eval_duration")), generacion_ms=eval_ms,
                       tokens_por_s=round(salida / (eval_ms / 1000), 1) if eval_ms else None)

    def on_llm_error(self, error, *, run_id, parent_run_id=None, tags=None, **kwargs):
        datos = self._cerrar(run_id)
        if datos:
            self._acumular(datos["traza"], errores=1)
            self.registrar("llm", datos["nombre"], traza=datos["traza"], duracion_ms=datos["duracion_ms"],
                           estado="error", nodo=datos.get("nodo"), error=enmascarar(f"{type(error).__name__}: {error}")[:300])

    # ------------------------------------------------------------ herramientas
    def on_tool_start(self, serialized, input_str, *, run_id, parent_run_id=None, tags=None, metadata=None, inputs=None, **kwargs):
        nombre = kwargs.get("name") or (serialized or {}).get("name", "herramienta")
        self._abrir(run_id, parent_run_id, "herramienta", nombre, entrada=enmascarar(input_str)[:200],
                    nodo=(metadata or {}).get("langgraph_node"))

    def on_tool_end(self, output, *, run_id, parent_run_id=None, **kwargs):
        datos = self._cerrar(run_id)
        if not datos:
            return
        contenido = getattr(output, "content", output)
        if isinstance(contenido, str) and contenido.startswith("{"):
            try:  # dentro de ReAct la herramienta devuelve un ToolMessage con JSON
                contenido = json.loads(contenido)
            except ValueError:
                pass
        resumen = {}
        if isinstance(contenido, dict):
            for clave in ("suficiente", "motivo", "estado"):
                if clave in contenido:
                    resumen[clave] = contenido[clave]
            if "hallazgos" in contenido:
                resumen["hallazgos"] = len(contenido["hallazgos"])
            if "fuentes" in contenido:
                resumen["fuentes"] = [f.get("fuente") for f in contenido["fuentes"]][:4]
        self._acumular(datos["traza"], herramientas_ms=datos["duracion_ms"])
        self.registrar("herramienta", datos["nombre"], traza=datos["traza"], duracion_ms=datos["duracion_ms"],
                       estado="ok", nodo=datos.get("nodo"), entrada=datos.get("entrada"), resultado=resumen)

    def on_tool_error(self, error, *, run_id, parent_run_id=None, **kwargs):
        datos = self._cerrar(run_id)
        if datos:
            self._acumular(datos["traza"], errores=1, herramientas_ms=datos["duracion_ms"])
            self.registrar("herramienta", datos["nombre"], traza=datos["traza"], duracion_ms=datos["duracion_ms"],
                           estado="error", nodo=datos.get("nodo"), entrada=datos.get("entrada"),
                           error=enmascarar(f"{type(error).__name__}: {error}")[:300])


# ---------------------------------------------------------------------------
_OBSERVADOR: Observador | None = None


def configurar(carpeta: Path) -> Observador | None:
    global _OBSERVADOR
    _OBSERVADOR = Observador(carpeta) if config.OBSERVABILIDAD else None
    return _OBSERVADOR


def obtener_observador() -> Observador | None:
    return _OBSERVADOR


def medir_recuperacion(recuperador):
    """Envuelve el recuperador de ChromaDB para registrar cada búsqueda."""

    def envoltura(pregunta: str, k: int):
        inicio = time.perf_counter()
        estado, resultados = "ok", []
        try:
            resultados = recuperador(pregunta, k)
            return resultados
        except Exception:
            estado = "error"
            raise
        finally:
            observador = obtener_observador()
            if observador is not None:
                distancias = [round(float(s), 4) for _, s in resultados]
                observador.registrar("recuperacion", "chromadb", duracion_ms=round((time.perf_counter() - inicio) * 1000, 1),
                                     estado=estado, k=k, mejor_distancia=min(distancias) if distancias else None)

    return envoltura


def nueva_traza() -> str:
    return uuid.uuid4().hex
