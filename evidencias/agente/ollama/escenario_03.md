# Escenario 3: Inconsistencias corregibles

- Modo: **ollama** (llama3.2:3b · qwen3-embedding:0.6b)
- Fecha de ejecución: 2026-11-03 01:03
- Objetivo: Detectar diferencias de bultos y peso y comunicar al cliente.
- Entrada del usuario: `Revisa la OP1003`
- Tiempo de ejecución: 2.6 s

## Plan ejecutado (ordenado por ejecución)

| Orden | Tarea | Acción | Prioridad | Estado | Resultado |
|---:|---|---|---:|---|---|
| 1 | T01 | verificar_documentos | 1 | completada | verificar_documentos_requeridos: sin hallazgos |
| 2 | T02 | validar_concordancia | 2 | completada | validar_concordancia: diferencia_bultos(corregible), diferencia_peso(corregible) |
| 3 | T05 | fundamentar | 3 | completada | 2/2 hallazgos con respaldo documental |
| 4 | T03 | validar_nomenclatura | 4 | completada | validar_nomenclatura: nomenclatura(informativa) |
| 5 | T09 | fundamentar | 3 | completada | 1/1 hallazgos con respaldo documental |
| 6 | T06 | registrar_observaciones | 5 | completada | Observaciones registradas: OBS-0003, OBS-0004, OBS-0005 |
| 7 | T07 | redactar_comunicacion | 6 | completada | Borrador con 2 puntos (sin preferencia registrada); plazo 5 días hábiles |
| 8 | T08 | aprobar_comunicacion | 7 | completada | Aprobada por el ejecutivo |
| 9 | T04 | actualizar_estado | 9 | completada | Estado final: Con observaciones |

## Decisiones adaptativas

| Paso | Condición detectada | Decisión | Regla |
|---|---|---|---|
| planificar | Categoría 'herramientas' sin control previo conocido | Omitir verificación de permisos | EXT-001 |
| T02 validar_concordancia | Hay hallazgos que deben respaldarse en la base documental | Agregar T05 'fundamentar' con prioridad 3 |  |
| T02 validar_concordancia | Toda inconsistencia debe registrarse (INT-001) | Agregar T06 'registrar_observaciones' con prioridad 5 |  |
| T02 validar_concordancia | Hay antecedentes que el cliente debe aclarar o enviar | Agregar T07 'redactar_comunicacion' con prioridad 6 |  |
| T02 validar_concordancia | Toda comunicación al cliente requiere aprobación humana | Agregar T08 'aprobar_comunicacion' con prioridad 7 |  |
| T03 validar_nomenclatura | Hay hallazgos que deben respaldarse en la base documental | Agregar T09 'fundamentar' con prioridad 3 |  |
| T08 aprobar_comunicacion | Borrador listo para el cliente | Enviar (aprobada) | Supervisión humana obligatoria |

## Pausa human-in-the-loop

```text
Asunto: Observaciones de la operación OP1003

Estimados/as Ferretería Central Ltda:

Durante la revisión documental de la operación OP1003 (Herramientas eléctricas manuales) se identificaron los siguientes puntos:

1. Documento afectado: Lista de empaque
   Inconsistencia detectada: Bultos: factura indica 120 y lista de empaque indica 112.
   Acción necesaria: Solicitar aclaración o documento corregido.

2. Documento afectado: Lista de empaque
   Inconsistencia detectada: Peso (kg): factura indica 2400.0 y lista de empaque indica 2310.0.
   Acción necesaria: Solicitar aclaración o documento corregido.

Agradeceremos su respuesta dentro de un plazo de 5 días hábiles.
La operación no continuará su preparación hasta recibir los antecedentes indicados.

Saludos cordiales,
Agencia de Aduanas del Norte (borrador generado por AduanaAgent, sujeto a revisión del ejecutivo)
```

## Respuesta del agente

**Revisión OP1003 – Con observaciones**

Resumen de revisión:

La operación OP1003 ha sido revisada y se requieren correcciones. Se identifican dos errores en la lista de empaque y peso de los bultos. Además, se requiere agregar tareas para fundamentar, registrar observaciones, redactar comunicación y aprobar comunicación. Se enviará la operación con las correcciones y recomendaciones.

Informe: salidas/demo_real/OP1003/informe_revision.md

**Criterio de aceptación:** Con observaciones y comunicación generada → CUMPLE