# Escenario 2: Documentos faltantes y preferencia del cliente

- Modo: **simulado** (modelo y embeddings deterministas, sin LLM)
- Fecha de ejecución: 2026-11-21 14:13
- Objetivo: Detectar faltantes (incluye certificado de origen por preferencia arancelaria) y usar la preferencia de contacto guardada en memoria.
- Entrada del usuario: `Revisa la OP1002`
- Tiempo de ejecución: 0.1 s

## Memoria de largo plazo recuperada

- [preferencia] Preferencia de Comercial Pacífico Ltda: las comunicaciones de observaciones deben dirigirse a Paula Rojas, encargada de comercio exterior, e indicar un plazo de respuesta de 48 horas. (distancia 0.8074)

## Plan ejecutado (ordenado por ejecución)

| Orden | Tarea | Acción | Prioridad | Estado | Resultado |
|---:|---|---|---:|---|---|
| 1 | T01 | verificar_documentos | 1 | completada | verificar_documentos_requeridos: documento_faltante(corregible), documento_faltante(corregible) |
| 2 | T02 | validar_concordancia | 2 | completada | validar_concordancia: sin hallazgos |
| 3 | T05 | fundamentar | 3 | completada | 1/1 hallazgos con respaldo documental |
| 4 | T03 | validar_nomenclatura | 4 | completada | validar_nomenclatura: sin hallazgos |
| 5 | T06 | registrar_observaciones | 5 | completada | Observaciones registradas: OBS-0001, OBS-0002 |
| 6 | T07 | redactar_comunicacion | 6 | completada | Borrador con 2 puntos (preferencia recuperada de memoria); plazo 48 horas |
| 7 | T08 | aprobar_comunicacion | 7 | completada | Aprobada por el ejecutivo |
| 8 | T04 | actualizar_estado | 9 | completada | Estado final: Pendiente de documentación |

## Decisiones adaptativas

| Paso | Condición detectada | Decisión | Regla |
|---|---|---|---|
| planificar | Categoría 'textiles' sin control previo conocido | Omitir verificación de permisos | EXT-001 |
| planificar | Operación marcada como urgente | Asunto [URGENTE] y plazo de 24 horas, salvo preferencia registrada del cliente | Priorización |
| T01 verificar_documentos | Hay hallazgos que deben respaldarse en la base documental | Agregar T05 'fundamentar' con prioridad 3 |  |
| T01 verificar_documentos | Toda inconsistencia debe registrarse (INT-001) | Agregar T06 'registrar_observaciones' con prioridad 5 |  |
| T01 verificar_documentos | Hay antecedentes que el cliente debe aclarar o enviar | Agregar T07 'redactar_comunicacion' con prioridad 6 |  |
| T01 verificar_documentos | Toda comunicación al cliente requiere aprobación humana | Agregar T08 'aprobar_comunicacion' con prioridad 7 |  |
| T07 redactar_comunicacion | Preferencia del cliente recuperada de memoria: Paula Rojas (encargada de comercio exterior); plazo de respuesta 48 horas | Dirigir la comunicación a ese contacto y usar plazo 48 horas | Memoria de largo plazo prevalece |
| T08 aprobar_comunicacion | Borrador listo para el cliente | Enviar (aprobada) | Supervisión humana obligatoria |

## Pausa human-in-the-loop

```text
Asunto: [URGENTE] Observaciones de la operación OP1002

Estimado/a Paula Rojas (encargada de comercio exterior):

Durante la revisión documental de la operación OP1002 (Prendas de vestir de algodón) se identificaron los siguientes puntos:

1. Documento afectado: Lista de empaque
   Inconsistencia detectada: No se recibió: Lista de empaque.
   Acción necesaria: Solicitar al cliente el antecedente pendiente.

2. Documento afectado: Certificado de origen
   Inconsistencia detectada: No se recibió: Certificado de origen (preferencia arancelaria).
   Acción necesaria: Solicitar al cliente el antecedente pendiente.

Agradeceremos su respuesta dentro de un plazo de 48 horas.
La operación no continuará su preparación hasta recibir los antecedentes indicados.

Saludos cordiales,
Agencia de Aduanas del Norte (borrador generado por AduanaAgent, sujeto a revisión del ejecutivo)
```

## Respuesta del agente

**Revisión OP1002 – Pendiente de documentación**

2 hallazgos: 0 críticos, 2 corregibles y 0 informativos.
- [corregible] No se recibió: Lista de empaque.
- [corregible] No se recibió: Certificado de origen (preferencia arancelaria).
Comunicación al cliente: aprobada.

Informe: salidas/demo_simulado/OP1002/informe_revision.md

**Criterio de aceptación:** Pendiente de documentación, comunicación a Paula Rojas aprobada por humano → CUMPLE