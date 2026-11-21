# Escenario 6: Mercancía no catalogada

- Modo: **simulado** (modelo y embeddings deterministas, sin LLM)
- Fecha de ejecución: 2026-11-21 14:13
- Objetivo: Consultar la base documental antes de asumir requisitos y actuar según exista o no evidencia suficiente.
- Entrada del usuario: `Revisa la OP1005`
- Tiempo de ejecución: 0.1 s

## Plan ejecutado (ordenado por ejecución)

| Orden | Tarea | Acción | Prioridad | Estado | Resultado |
|---:|---|---|---:|---|---|
| 1 | T01 | evaluar_requisitos_especiales | 1 | completada | evaluar_requisitos_especiales: requisito_por_confirmar(corregible) |
| 2 | T02 | verificar_documentos | 1 | completada | verificar_documentos_requeridos: documento_ilegible(corregible) |
| 3 | T03 | validar_concordancia | 2 | completada | validar_concordancia: sin hallazgos |
| 4 | T06 | fundamentar | 3 | completada | 2/2 hallazgos con respaldo documental |
| 5 | T04 | validar_nomenclatura | 4 | completada | validar_nomenclatura: sin hallazgos |
| 6 | T07 | registrar_observaciones | 5 | completada | Observaciones registradas: OBS-0009, OBS-0010 |
| 7 | T08 | redactar_comunicacion | 6 | completada | Borrador con 2 puntos (sin preferencia registrada); plazo 5 días hábiles |
| 8 | T09 | aprobar_comunicacion | 7 | completada | Aprobada por el ejecutivo |
| 9 | T05 | actualizar_estado | 9 | completada | Estado final: Con observaciones |

## Decisiones adaptativas

| Paso | Condición detectada | Decisión | Regla |
|---|---|---|---|
| planificar | Categoría 'no_catalogada' desconocida para las reglas | Consultar RAG antes de asumir requisitos | INT-002: no resolver por suposiciones |
| T01 evaluar_requisitos_especiales | RAG con evidencia suficiente (respuesta respaldada) | Solicitar confirmación al cliente | INT-003: respuesta ante información insuficiente |
| T01 evaluar_requisitos_especiales | Hay hallazgos que deben respaldarse en la base documental | Agregar T06 'fundamentar' con prioridad 3 |  |
| T01 evaluar_requisitos_especiales | Toda inconsistencia debe registrarse (INT-001) | Agregar T07 'registrar_observaciones' con prioridad 5 |  |
| T01 evaluar_requisitos_especiales | Hay antecedentes que el cliente debe aclarar o enviar | Agregar T08 'redactar_comunicacion' con prioridad 6 |  |
| T01 evaluar_requisitos_especiales | Toda comunicación al cliente requiere aprobación humana | Agregar T09 'aprobar_comunicacion' con prioridad 7 |  |
| T09 aprobar_comunicacion | Borrador listo para el cliente | Enviar (aprobada) | Supervisión humana obligatoria |

## Pausa human-in-the-loop

```text
Asunto: Observaciones de la operación OP1005

Estimados/as Tecnología Austral SpA:

Durante la revisión documental de la operación OP1005 (Drones de uso recreativo con control remoto) se identificaron los siguientes puntos:

1. Documento afectado: mercancia
   Inconsistencia detectada: Las fuentes sugieren posible control previo para 'Drones de uso recreativo con control remoto': Las autorizaciones deben obtenerse ante el organismo competente cuando la legislación establezca un control previo a la importación. Dependiendo de su naturaleza, algunas mercancías pueden estar sujetas a autorización, certificación, visto bueno o control previo de otro organismo del Estado.
   Acción necesaria: Confirmar con el cliente y la fuente oficial si la mercancía requiere control previo.

2. Documento afectado: Factura comercial
   Inconsistencia detectada: El archivo FACTURA_OP1005_V1.pdf no es legible.
   Acción necesaria: Solicitar una copia legible del documento.

Agradeceremos su respuesta dentro de un plazo de 5 días hábiles.
La operación no continuará su preparación hasta recibir los antecedentes indicados.

Saludos cordiales,
Agencia de Aduanas del Norte (borrador generado por AduanaAgent, sujeto a revisión del ejecutivo)
```

## Respuesta del agente

**Revisión OP1005 – Con observaciones**

2 hallazgos: 0 críticos, 2 corregibles y 0 informativos.
- [corregible] Las fuentes sugieren posible control previo para 'Drones de uso recreativo con control remoto': Las autorizaciones deben obtenerse ante el organismo competente cuando la legislación establezca un control previo a la importación. Dependiendo de su naturaleza, algunas mercancías pueden estar sujetas a autorización, certificación, visto bueno o control previo de otro organismo del Estado.
- [corregible] El archivo FACTURA_OP1005_V1.pdf no es legible.
Comunicación al cliente: aprobada.

Informe: salidas/demo_simulado/OP1005/informe_revision.md

**Criterio de aceptación:** Requisito por confirmar o escalado + documento ilegible → CUMPLE