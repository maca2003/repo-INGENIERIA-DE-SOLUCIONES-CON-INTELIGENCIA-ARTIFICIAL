"""Persistencia de expedientes, observaciones, estados y trazabilidad.

Los expedientes originales de data/operaciones funcionan como bandeja de
entrada de solo lectura. El agente trabaja sobre copias en salidas/expedientes
y nunca sobrescribe una versión anterior de un documento (INT-003).
"""

import json
from datetime import datetime
from pathlib import Path

from .config import USUARIO_AGENTE, Rutas


def ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _leer_json(ruta: Path, defecto):
    if not ruta.exists():
        return defecto
    return json.loads(ruta.read_text(encoding="utf-8"))


def _escribir_json(ruta: Path, datos) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


class Almacen:
    def __init__(self, rutas: Rutas):
        self.rutas = rutas
        self.rutas.salidas.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------ expedientes
    def listar_operaciones(self) -> list[str]:
        ids = {p.stem for p in self.rutas.operaciones.glob("OP*.json")}
        if self.rutas.expedientes_trabajo.exists():
            ids |= {p.stem for p in self.rutas.expedientes_trabajo.glob("OP*.json")}
        return sorted(ids)

    def obtener_expediente(self, operacion_id: str) -> dict | None:
        operacion_id = operacion_id.strip().upper()
        copia = self.rutas.expedientes_trabajo / f"{operacion_id}.json"
        original = self.rutas.operaciones / f"{operacion_id}.json"
        if copia.exists():
            return _leer_json(copia, None)
        if original.exists():
            return _leer_json(original, None)
        return None

    def guardar_expediente(self, expediente: dict) -> Path:
        ruta = self.rutas.expedientes_trabajo / f"{expediente['operacion_id']}.json"
        _escribir_json(ruta, expediente)
        return ruta

    # ---------------------------------------------------------- observaciones
    def observaciones(self, operacion_id: str | None = None) -> list[dict]:
        todas = _leer_json(self.rutas.registro_observaciones, [])
        if operacion_id:
            return [o for o in todas if o["operacion_id"] == operacion_id.upper()]
        return todas

    def agregar_observacion(self, observacion: dict) -> dict:
        todas = _leer_json(self.rutas.registro_observaciones, [])
        observacion["id"] = f"OBS-{len(todas) + 1:04d}"
        todas.append(observacion)
        _escribir_json(self.rutas.registro_observaciones, todas)
        return observacion

    def actualizar_observacion(self, id_observacion: str, cambios: dict) -> dict | None:
        todas = _leer_json(self.rutas.registro_observaciones, [])
        for obs in todas:
            if obs["id"] == id_observacion:
                obs.update(cambios)
                _escribir_json(self.rutas.registro_observaciones, todas)
                return obs
        return None

    # ---------------------------------------------------------------- estados
    def estado_operacion(self, operacion_id: str) -> dict | None:
        return _leer_json(self.rutas.estados_operaciones, {}).get(operacion_id.upper())

    def fijar_estado(self, operacion_id: str, estado: str, motivo: str) -> dict:
        estados = _leer_json(self.rutas.estados_operaciones, {})
        anterior = estados.get(operacion_id, {}).get("estado")
        estados[operacion_id] = {
            "estado": estado,
            "estado_anterior": anterior,
            "motivo": motivo,
            "actualizado": ahora(),
        }
        _escribir_json(self.rutas.estados_operaciones, estados)
        return estados[operacion_id]

    # ----------------------------------------------------------- trazabilidad
    def trazar(self, operacion_id: str, accion: str, documento: str, resultado: str, observaciones: str = "") -> dict:
        """Registra una acción con los campos exigidos por INT-003."""
        registro = {
            "usuario": USUARIO_AGENTE,
            "fecha_hora": ahora(),
            "operacion": operacion_id,
            "accion": accion,
            "documento": documento,
            "resultado": resultado,
            "observaciones": observaciones,
        }
        self.rutas.trazabilidad.parent.mkdir(parents=True, exist_ok=True)
        with self.rutas.trazabilidad.open("a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
        return registro

    def leer_trazabilidad(self, operacion_id: str | None = None) -> list[dict]:
        if not self.rutas.trazabilidad.exists():
            return []
        registros = [
            json.loads(linea)
            for linea in self.rutas.trazabilidad.read_text(encoding="utf-8").splitlines()
            if linea.strip()
        ]
        if operacion_id:
            return [r for r in registros if r["operacion"] == operacion_id]
        return registros
