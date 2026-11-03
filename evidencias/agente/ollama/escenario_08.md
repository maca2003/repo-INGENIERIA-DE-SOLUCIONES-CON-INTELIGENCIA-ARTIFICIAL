# Escenario 8: Continuidad de un flujo prolongado

- Modo: **ollama** (llama3.2:3b · qwen3-embedding:0.6b)
- Fecha de ejecución: 2026-11-03 01:03
- Objetivo: Pausar en la aprobación humana, reiniciar el grafo con el mismo checkpointer SQLite y retomar el flujo en el punto exacto.
- Entrada del usuario: `Revisa nuevamente la OP1002`
- Tiempo de ejecución: - s

## Memoria de largo plazo recuperada

- [preferencia] Preferencia de Comercial Pacífico Ltda: las comunicaciones de observaciones deben dirigirse a Paula Rojas, encargada de comercio exterior, e indicar un plazo de respuesta de 48 horas. (distancia 0.7823)
- [episodio] Episodio OP1002 de Comercial Pacífico Ltda (2026-11-03): estado Pendiente de documentación; hallazgos: documento_faltante. (distancia 0.7998)

## Plan ejecutado (ordenado por ejecución)

| Orden | Tarea | Acción | Prioridad | Estado | Resultado |
|---:|---|---|---:|---|---|
| 1 | T01 | verificar_resolucion | 1 | completada | 0 resueltas, 2 vigentes |
| 2 | T02 | verificar_documentos | 1 | completada | verificar_documentos_requeridos: documento_faltante(corregible), documento_faltante(corregible) |
| 3 | T03 | validar_concordancia | 2 | completada | validar_concordancia: sin hallazgos |
| 4 | T06 | fundamentar | 3 | completada | 1/1 hallazgos con respaldo documental |
| 5 | T04 | validar_nomenclatura | 4 | completada | validar_nomenclatura: sin hallazgos |
| 6 | T07 | registrar_observaciones | 5 | completada | Observaciones registradas: OBS-0001, OBS-0002 |
| 7 | T08 | redactar_comunicacion | 6 | completada | Borrador con 2 puntos (preferencia recuperada de memoria); plazo 48 horas |
| 8 | T09 | aprobar_comunicacion | 7 | completada | Rechazada por el ejecutivo |
| 9 | T05 | actualizar_estado | 9 | completada | Estado final: Pendiente de documentación |

## Decisiones adaptativas

| Paso | Condición detectada | Decisión | Regla |
|---|---|---|---|
| planificar | 2 observaciones abiertas en el registro | Verificar si fueron resueltas antes de continuar | INT-002: cierre de observaciones |
| planificar | Categoría 'textiles' sin control previo conocido | Omitir verificación de permisos | EXT-001 |
| planificar | Operación marcada como urgente | Asunto [URGENTE] y plazo de 24 horas, salvo preferencia registrada del cliente | Priorización |
| T02 verificar_documentos | Hay hallazgos que deben respaldarse en la base documental | Agregar T06 'fundamentar' con prioridad 3 |  |
| T02 verificar_documentos | Toda inconsistencia debe registrarse (INT-001) | Agregar T07 'registrar_observaciones' con prioridad 5 |  |
| T02 verificar_documentos | Hay antecedentes que el cliente debe aclarar o enviar | Agregar T08 'redactar_comunicacion' con prioridad 6 |  |
| T02 verificar_documentos | Toda comunicación al cliente requiere aprobación humana | Agregar T09 'aprobar_comunicacion' con prioridad 7 |  |
| T08 redactar_comunicacion | Preferencia del cliente recuperada de memoria: Paula Rojas (encargada de comercio exterior); plazo de respuesta 48 horas | Dirigir la comunicación a ese contacto y usar plazo 48 horas | Memoria de largo plazo prevalece |
| T09 aprobar_comunicacion | Borrador listo para el cliente | No enviar (rechazada) | Supervisión humana obligatoria |

## Respuesta del agente

**Revisión OP1002 – Pendiente de documentación**

Resumen:

La operación OP1002 se encuentra en estado final de pendiente de documentación debido a la falta de recepción de la lista de empaque y el certificado de origen. Se han agregado tareas para fundamentar, registrar observaciones, redactar una comunicación y aprobarla. Se ha decidido dirigir la comunicación a un contacto específico y establecer un plazo de 48 horas para su resolución.

Informe: salidas/demo_real/OP1002/informe_revision.md

## Observaciones

- Interrupción detectada: True
- Nodo pendiente tras reiniciar: ('aprobacion_humana',)
- Se respondió 'rechazar': el borrador no se envía y la operación sigue con observaciones.
- Observaciones en el registro: 2

**Criterio de aceptación:** El nuevo proceso retoma en 'aprobacion_humana' y termina el flujo → CUMPLE