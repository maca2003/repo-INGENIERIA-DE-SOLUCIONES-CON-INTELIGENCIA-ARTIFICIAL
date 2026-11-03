# Evidencias del agente (EP2)

Generadas con `python src/demo_escenarios.py`.

| Carpeta | Cómo se generó | Validez |
|---|---|---|
| `ollama/` | Con Ollama (`llama3.2:3b` + `qwen3-embedding:0.6b`) | Evidencia del comportamiento real del agente. |
| `simulado/` | `--simulado`: modelo y embeddings deterministas, sin Ollama | Verifica la orquestación, la planificación, la memoria y las herramientas. Los textos generados por el "modelo" son simulados. |

Cada carpeta contiene:

- `escenario_XX.md`: plan ejecutado, decisiones adaptativas, pausa humana y respuesta.
- `resumen.json`: criterio de aceptación de cada escenario.
- `registro_observaciones.json`, `estados_operaciones.json` y `trazabilidad.jsonl`: escrituras del agente.
- `memoria_largo_plazo.json`: exportación de la memoria semántica al final de la demo.
