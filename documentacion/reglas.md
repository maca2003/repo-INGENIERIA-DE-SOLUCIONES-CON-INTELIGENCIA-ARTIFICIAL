# Reglas de decisión

Fases 1.4 y 6 de la guía. Las reglas viven en `src/agente/reglas.py` (catálogo) y en `src/agente/planificador.py` (orden y replanificación). Son **funciones puras y deterministas**: ante los mismos datos siempre dan el mismo resultado, por eso se prueban en `tests/test_planificacion.py`.

## 1. Prioridad de las tareas del plan (0 = primero)

El agente siempre ejecuta la tarea pendiente de menor `(prioridad, secuencia)`. Por eso lo delicado va antes que lo rutinario, igual que en la guía.

| Prioridad | Tarea | Cuándo entra al plan | Razón |
|---:|---|---|---|
| 0 | `incorporar_correccion` | El usuario informa un documento corregido | Hay que revisar la versión vigente |
| 0 | `verificar_permisos` | Mercancía regulada (EXT-001) | Un permiso faltante es crítico y bloquea todo |
| 0 | `registrar_observaciones` + `escalar` | Aparece un hallazgo crítico (dinámico) | INT-002: escalar de inmediato |
| 1 | `verificar_resolucion` | Hay observaciones abiertas de una revisión anterior | INT-002: cierre |
| 1 | `verificar_documentos` | Siempre | INT-001: documentos iniciales |
| 1 | `evaluar_requisitos_especiales` | Mercancía no catalogada | No suponer requisitos |
| 1 | `validar_concordancia` **reforzada** | La memoria trae un antecedente de riesgo del cliente | Aprendizaje de episodios previos |
| 2 | `validar_concordancia` | Sin antecedentes | INT-001 |
| 3 | `fundamentar` | Hay hallazgos | Respaldo documental (RAG) |
| 4 | `validar_nomenclatura` | Siempre | INT-003 (informativa) |
| 5 | `registrar_observaciones` | Hay hallazgos | Trazabilidad |
| 6 | `redactar_comunicacion` | Hay corregibles y ninguna crítica | El cliente debe actuar |
| 7 | `aprobar_comunicacion` | Hay un borrador | Supervisión humana |
| 9 | `actualizar_estado` | Siempre | Toda revisión termina con un estado |

## 2. Reglas de replanificación (nodo `evaluar`)

Se evalúan después de cada tarea. Cada regla que se cumple deja una decisión registrada con su condición y su regla de origen.

| # | Condición detectada | Decisión del agente | Fuente |
|---:|---|---|---|
| 1 | La tarea falló dos veces (por ejemplo, el LLM no responde) | Marcarla como fallida y escalar | Tolerancia a fallos |
| 2 | Hallazgo crítico | Registrar y escalar con prioridad 0; suspender la comunicación | INT-002 |
| 3 | El RAG no encontró evidencia o un hallazgo no tiene respaldo | Escalar en lugar de suponer | INT-003 |
| 4 | Hallazgo corregible y ninguna crítica | Fundamentar, registrar, redactar y pedir aprobación | INT-002 |
| 5 | Observaciones previas ya no se reproducen | Cerrarlas | INT-002 |
| 6 | Preferencia del cliente en memoria | Usar su destinatario y plazo en el borrador | Memoria de largo plazo |
| 7 | El ejecutivo rechaza el borrador | No enviar; mantener la operación con observaciones | Supervisión humana |

## 3. Estado final de la operación (la primera regla que se cumple)

Mismo patrón que `decidir_accion` de la guía: se evalúa de arriba hacia abajo y se detiene en la primera regla que se cumple (`determinar_estado_final`).

| # | Condición | Estado (INT-001) |
|---:|---|---|
| 1 | Falta un documento obligatorio | Pendiente de documentación |
| 2 | Hay hallazgos u observaciones abiertas corregibles o críticas | Con observaciones |
| 3 | Solo hallazgos informativos o ninguno | Derivada a revisión |

## 4. Clasificación de hallazgos (INT-002)

| Tipo de hallazgo | Nivel | Acción |
|---|---|---|
| `permiso_faltante`, `importador_inconsistente`, `operacion_distinta`, `diferencia_valor` (> 5 %), `requisito_no_determinado` | Crítica | Escalar al responsable |
| `documento_faltante`, `diferencia_bultos`, `diferencia_peso`, `diferencia_descripcion`, `documento_ilegible`, `dato_faltante`, `requisito_por_confirmar` | Corregible | Pedir aclaración o un documento corregido |
| `nomenclatura` | Informativa | Registrar |
| Tipo desconocido | Crítica | Criterio conservador: no se resuelve por suposición |

## Ejercicio de comprensión (como en la guía)

1. La OP1004 trae alimentos sin permiso del SAG **y** un RUT distinto en el documento de transporte. ¿Qué se ejecuta primero y por qué?
   → `verificar_permisos` (prioridad 0, mercancía regulada). El RUT distinto se detecta después en la concordancia y también se escala.
2. ¿Qué pasaría si `actualizar_estado` tuviera prioridad 0?
   → Fijaría el estado antes de conocer los hallazgos: siempre quedaría "Derivada a revisión".
