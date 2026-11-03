# Resumen de evidencias

- Fecha: 2026-11-03 01:05
- Proveedor del modelo: **ollama** (ollama · llama3.2:3b · qwen3-embedding:0.6b)
- Python: 3.12.10 · Sistema: win32

| Paso | Estado | Tiempo (s) | Archivo | Última línea |
|---|---|---:|---|---|
| 1. Verificar modelos | OK | 4.3 | `evidencias/ejecucion/01_probar_modelos.txt` | Primeros cinco valores: [-0.012503553, -0.032151792, -0.011848554, -0.06314403, 0.010900005] |
| 3. Pruebas automatizadas (suite completa) | OK | 52.4 | `evidencias/pytest_output.txt` | ============================= 37 passed in 47.94s ============================= |
| 4. Pruebas con el modelo real | OK | 22.3 | `evidencias/pytest_real_output.txt` | ====================== 4 passed, 33 deselected in 19.06s ====================== |
| 5. Escenarios de decisión | OK | 58.3 | `evidencias/ejecucion/05_escenarios_ollama.txt` | 10/10 escenarios cumplen su criterio. Evidencias en C:\Users\macar\proyectos\aduanarag\evidencias\agente\ollama |
| 6. Evaluación RAG (EP1) | OK | 24.3 | `evidencias/ejecucion/06_evaluacion_rag.txt` | Resultados guardados en: C:\Users\macar\proyectos\aduanarag\evidencias\resultados_evaluacion.json |
| Capturas de la interfaz | OK | 33.4 | `evidencias/capturas/ollama/` | 6 capturas |
