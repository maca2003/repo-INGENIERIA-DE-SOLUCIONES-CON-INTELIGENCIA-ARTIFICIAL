# Alcance de AduanaAgent

Fase 1 de la guía EVA02: qué hace el agente y qué no hace, antes de programar.

## Lo que SÍ hace

- Recibe instrucciones en lenguaje natural (`Revisa la OP1003`, `¿Qué observaciones quedaron?`).
- Consulta el expediente de la operación y su estado.
- Verifica los documentos obligatorios, la concordancia entre documentos, los permisos y la nomenclatura (INT-001, INT-003 y EXT-001).
- Clasifica cada hallazgo como informativo, corregible o crítico (INT-002) y lo fundamenta con un fragmento recuperado por RAG.
- Ejecuta acciones de escritura: registra observaciones, redacta el borrador al cliente, escala al responsable, cambia el estado y guarda la trazabilidad.
- Recuerda la conversación del hilo (memoria corta) y los antecedentes y preferencias de cada cliente (memoria larga).
- Replanifica cuando cambian las condiciones: observación crítica, falta de evidencia, falla de una herramienta o documento corregido.
- Pide aprobación humana antes de cualquier comunicación externa.
- Prioriza la cola de operaciones pendientes.

## Lo que NO hace

- No presenta declaraciones ante el Servicio Nacional de Aduanas ni autoriza operaciones.
- No envía correos reales: genera borradores que una persona aprueba.
- No lee PDF ni hace OCR: los expedientes son JSON simulados.
- No resuelve observaciones críticas por su cuenta: las escala.
- No entrega asesoría legal ni reemplaza al agente de aduana.
- No usa datos reales de clientes: la organización y las operaciones son simuladas.

## Métricas de éxito (demo)

| Métrica | Meta | Cómo se verifica |
|---|---|---|
| Escenarios de decisión con criterio de aceptación | 10/10 | `python src/demo_escenarios.py` → `evidencias/agente/<proveedor>/resumen.json` |
| Pruebas automatizadas | 100 % aprobadas | `python -m pytest -v` → `evidencias/pytest_output.txt` |
| Comunicaciones enviadas sin aprobación humana | 0 | Pausa `interrupt()` en `aprobacion_humana` |
| Escrituras con trazabilidad INT-003 | 100 % | `salidas/trazabilidad.jsonl` |
| Escenarios distintos demostrables en 10 minutos | 4 | `documentacion/guion_demo.md` |
