# Cómo cumple AduanaAgent la guía EVA02 (fase por fase)

La guía del docente (*Agente TechStore Returns*) es un **ejemplo de implementación** con un caso de devoluciones. Nuestro proyecto aplica el mismo camino al caso aduanero de la EP1. Este documento muestra, para cada fase, qué pide la guía, dónde está en nuestro repositorio y con qué comando se verifica el checkpoint.

## Equivalencias del caso

| Guía (TechStore) | AduanaAgent |
|---|---|
| Pedido `PED-001` | Operación `OP1001`–`OP1005` (`data/operaciones/*.json`) |
| `data/politicas.md` | Procedimientos `data/internos/` (INT-001/002/003) y `data/externos/` (EXT-001/002) |
| `data/techstore.db` (pedidos, clientes, historial) | Expedientes JSON + `salidas/` (observaciones, estados, trazabilidad) + memoria SQLite/Chroma |
| Aprobar / escalar / pedir información | Derivada a revisión / Con observaciones (escalada) / Pendiente de documentación |
| `decidir_accion` (6 reglas) | `planificador.py` (prioridades + replanificación) y `determinar_estado_final` |
| `procesar_solicitud` (determinista) + `crear_agente` (LLM) | Flujo de revisión del grafo (determinista) + `agente_conversacional` (ReAct con LLM) |

## Fase por fase

| Fase | Qué pide la guía | Dónde está en el proyecto | Checkpoint (comando) |
|---|---|---|---|
| 0 Entorno | Python 3.10+, venv, `requirements.txt`, `.env.example`, `.gitignore`, verificar el LLM | `requirements.txt` (versiones acotadas), `.env.example`, `.gitignore`, `src/probar_modelos.py` | `python src\probar_modelos.py` imprime `CONEXION LLM CORRECTA` |
| 1 Problema | `alcance.md`, contratos de tools, reglas | `documentacion/alcance.md`, `herramientas.md`, `reglas.md` | Explicar el flujo en 60 s |
| 2 Datos mock + 1.ª tool | Datos ficticios reproducibles, primera tool con prueba | `data/operaciones/` (5 expedientes + corrección), `data/memoria_inicial/`, `obtener_expediente` | `python -m pytest tests/test_herramientas.py -v` |
| 3 Las 7 tools | Tools con `@tool` y docstring, 6+ pruebas | 20 tools en `src/agente/herramientas/` | `python -m pytest tests/test_herramientas.py -v` → 11 pruebas |
| 4 Memoria corto/largo | Buffer de conversación + historial persistente | `memoria.py`: `SqliteSaver` por hilo (corto) + Chroma `memoria_agente` (largo) | `python -m pytest tests/test_memoria.py -v` |
| 5 Memoria semántica | Chroma + embeddings + tool RAG | `consultar_procedimientos`, `fundamentar_hallazgos`, `buscar_memoria` | `python src\calibrar_umbral.py` |
| 6 Planner | Reglas en orden de prioridad, función pura, pruebas | `planificador.py`, `reglas.py` | `python -m pytest tests/test_planificacion.py -v` |
| 7 Agente integrado | Flujo end-to-end con decisión trazable | `grafo.py` (LangGraph), `agente_cli.py` | `python src\agente_cli.py` → `Revisa la OP1003` |
| 8 Streamlit | UI con trace, memoria e historial | `src/app_agente.py` (pestañas Plan, Decisiones, Memoria, Trazabilidad) | `streamlit run src\app_agente.py` |
| 9 Pruebas | 12+ pruebas, E2E, fixture que limpia la base, `pytest_output.txt` | `tests/` (33 pruebas + 4 con el modelo real), `conftest.py` usa carpetas temporales | `python -m pytest -v` → `evidencias/pytest_output.txt` |
| 10 Documentación | README reproducible, Mermaid, informe de 5 páginas, declaración de IA | `README.md`, `documentacion/diagrama_orquestacion.md`, informe Word | Clonar en una carpeta limpia y seguir el README |
| 11 Demo | Guion de 4 escenas, roles, plan B, video | `documentacion/guion_demo.md`, presentación, `src/generar_evidencias.py --capturas` | Ensayar 2 veces con cronómetro |

## Diferencias con la guía y por qué

| La guía usa | Nosotros usamos | Por qué |
|---|---|---|
| Gemini Flash (API) | **Ollama local** por defecto; Gemini opcional con `AGENTE_PROVEEDOR=gemini` | Continuidad con la EP1 y confidencialidad de documentos (INT-003). Gemini queda disponible si el computador no corre Ollama con fluidez. |
| `langchain<1.0` con `AgentExecutor` y `ConversationBufferMemory` | LangChain 1.x (`create_agent`) y LangGraph 1.x | `AgentExecutor` y `ConversationBufferMemory` están obsoletos. LangGraph aporta el checkpointer (memoria persistente) y el `interrupt` (aprobación humana). Las versiones quedan acotadas en `requirements.txt`. |
| 7 tools | 20 tools en 3 capacidades | El flujo aduanero tiene más etapas: documentos, permisos, concordancia, cierre y escalamiento. |
| Memoria larga en SQLite | Memoria larga **semántica** en Chroma (por cliente) + corto plazo en SQLite (checkpointer) | Recuperar por significado los antecedentes de un cliente cubre IE3 e IE4 a la vez. |
| `st.session_state` como memoria corta | Checkpointer SQLite por `thread_id` | Sobrevive al cierre del programa: un flujo pausado se retoma después. |
| `scripts/seed_data.py` recrea la base antes de los tests | Cada prueba usa una carpeta temporal (`tmp_path`) | Mismo objetivo (pruebas repetibles) sin tocar los datos del usuario. |

## Mapa de indicadores → evidencia (Apéndice E adaptado)

| Indicador | Dónde se evidencia |
|---|---|
| IE1 Herramientas autónomas | `src/agente/herramientas/` (20 tools) · `tests/test_herramientas.py` · `documentacion/herramientas.md` |
| IE2 Frameworks | `requirements.txt` (LangChain, LangGraph, Chroma) · README reproducible · GitHub Actions |
| IE3 Memoria | `src/agente/memoria.py` · `tests/test_memoria.py` · escenario 8 (reanudación) |
| IE4 Recuperación semántica | `consultar_procedimientos`, `buscar_memoria`, `fundamentar_hallazgos` · escenarios 4, 5 y 10 |
| IE5 Planificación | `planificador.py` · `documentacion/reglas.md` · `tests/test_planificacion.py` |
| IE6 Informe técnico | Informe Word (5 páginas) · diagramas Mermaid |
| IE7 Decisiones en la demo | `documentacion/guion_demo.md` · `evidencias/agente/<proveedor>/` · capturas |
| IE8 Diagrama + README | `README.md` · `documentacion/diagrama_orquestacion.md` · `grafo_langgraph.mmd` |
| IE9 Justificación | Informe, sección 2.2 · README, sección 10 · tabla "Diferencias con la guía" de este documento |
| IE10 Lenguaje técnico | Presentación y preguntas preparadas |

## Checklist final (Apéndice D)

**Repositorio**
- [x] README reproducible desde cero (verificado en una carpeta limpia)
- [x] `.gitignore` excluye `.env`, `.venv/`, `chroma_db*/`, `salidas/`
- [x] `pytest` en verde (33 pruebas sin modelo + 4 con el modelo real)
- [x] Diagramas Mermaid que GitHub dibuja
- [x] Declaración de uso de IA en el README
- [ ] Repositorio **público** en GitHub (revisar en Settings → General → Danger Zone → Change visibility)
- [ ] Evidencia con el modelo real: `python src\generar_evidencias.py --capturas`

**Informe**
- [x] Máximo 5 páginas, portada, secciones de la guía, referencias APA y enlace al repositorio
- [ ] Reflexiones individuales y conclusión **escritas sin IA**
- [ ] Justificación técnica (sección 2.2) reescrita con palabras propias
- [ ] Completar los resultados con el modelo real y exportar a PDF

**Presentación**
- [x] Diapositivas con diagrama y guion de 4 escenas
- [ ] Video de respaldo de 2 minutos
- [ ] Ensayo de 2 veces con cronómetro

**Entrega**
- [ ] PDF + enlace al repositorio por AVA y al correo del docente (6 de noviembre)
- [ ] Respaldo del repositorio en un pendrive para el 7 de noviembre
