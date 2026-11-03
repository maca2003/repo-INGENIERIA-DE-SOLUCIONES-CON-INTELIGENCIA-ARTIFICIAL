# Evidencias del agente (EP2)

Se generan con `python src/generar_evidencias.py` (todo en un paso) o solo los escenarios con `python src/demo_escenarios.py`.

| Carpeta | Cómo se generó | Validez |
|---|---|---|
| `ollama/` | Con Ollama (`llama3.2:3b` + `qwen3-embedding:0.6b`) | Evidencia del comportamiento real del agente |
| `gemini/` | Con Gemini (`AGENTE_PROVEEDOR=gemini`) | Evidencia del comportamiento real del agente |
| `simulado/` | `--simulado`: modelo y embeddings deterministas, sin LLM | Verifica la orquestación, la planificación, la memoria y las herramientas; los textos del "modelo" son simulados |

Cada carpeta contiene:

- `escenario_XX.md`: plan ejecutado, decisiones adaptativas, pausa humana y respuesta.
- `resumen.json`: criterio de aceptación de cada escenario.
- `registro_observaciones.json`, `estados_operaciones.json` y `trazabilidad.jsonl`: escrituras del agente.
- `memoria_largo_plazo.json`: exportación de la memoria semántica al final de la demo.

Otras evidencias en `evidencias/`: `pytest_output.txt`, `pytest_real_output.txt`, `capturas/<proveedor>/`, `ejecucion/` (salida de cada paso) y `RESUMEN_EVIDENCIAS_<proveedor>.md`.
