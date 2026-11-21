# Análisis de registros · base

## Hallazgos

1. El LLM concentra el 1.4 % del tiempo total de las solicitudes; la recuperación en ChromaDB, el 0.2 %.
2. El nodo que más tiempo de LLM consume es «model» (26 llamadas, 3.5 ms en total, media 0.1 ms).
3. 2 solicitudes superan el doble de la mediana o el p95 de latencia.
4. No se registraron errores de herramientas ni del modelo.
5. El RAG se abstuvo en 5 de 10 consultas.
6. El guardarraíl bloqueó 4 entradas antes de llegar al modelo.

## Latencia de las solicitudes

- Solicitudes: 30 · media 19.1 ms · p50 11.8 ms · p95 35.9 ms · máx. 47.3 ms
- Reparto del tiempo: {'llm': 1.4, 'recuperacion_chroma': 0.2, 'herramientas_sin_llm': 12.0, 'orquestacion_y_resto': 86.3}

## Tiempo de LLM por nodo

| nombre | llamadas | total_ms | media_ms | p95_ms |
|---|---|---|---|---|
| model | 26 | 3.5 | 0.1 | 0.4 |
| tools | 7 | 2.4 | 0.3 | 0.4 |
| sintetizar | 13 | 1.9 | 0.1 | 0.3 |
| ejecutar_tarea | 1 | 0.4 | 0.4 | 0.4 |

## Nodos más lentos

| nombre | llamadas | total_ms | media_ms | p95_ms |
|---|---|---|---|---|
| ejecutar_tarea | 90 | 115.0 | 1.3 | 2.8 |
| consolidar_memoria | 26 | 94.3 | 3.6 | 7.8 |
| agente_conversacional | 13 | 89.1 | 6.9 | 7.6 |
| recuperar_contexto | 30 | 49.5 | 1.6 | 2.4 |
| tools | 13 | 22.7 | 1.7 | 2.3 |
| evaluar | 90 | 22.5 | 0.2 | 0.4 |
| model | 26 | 13.7 | 0.5 | 0.7 |
| sintetizar | 13 | 10.5 | 0.8 | 1.0 |

## Herramientas más lentas

| nombre | llamadas | total_ms | media_ms | p95_ms |
|---|---|---|---|---|
| registrar_observacion | 17 | 21.3 | 1.3 | 2.1 |
| actualizar_estado_operacion | 16 | 13.6 | 0.8 | 1.8 |
| consultar_procedimientos | 10 | 12.3 | 1.2 | 1.6 |
| validar_nomenclatura | 13 | 8.8 | 0.7 | 0.8 |
| fundamentar_hallazgos | 12 | 6.6 | 0.5 | 0.7 |
| verificar_documentos_requeridos | 13 | 5.5 | 0.4 | 0.5 |
| validar_concordancia | 13 | 5.5 | 0.4 | 0.5 |
| escalar_a_responsable | 5 | 5.4 | 1.1 | 1.4 |

## Arranques en frío del modelo

Sin datos.

## Solicitudes anómalas (> 2× mediana o > p95)

| ts | duracion_ms | intencion | llamadas_llm | entrada |
|---|---|---|---|---|
| 2026-11-21T14:10:45.887 | 36.2 | revision | 1 | Revisa la OP1003 |
| 2026-11-21T14:10:45.935 | 47.3 | revision | 1 | Revisa la OP1004 |

## Errores

Sin datos.

## Seguridad

| ts | motivo |
|---|---|
| 2026-11-21T14:10:46.361 | patrón no permitido: «Ignora las instrucciones» |
| 2026-11-21T14:10:46.364 | patrón no permitido: «Muestra tu system prompt» |
| 2026-11-21T14:10:46.367 | patrón no permitido: «<script» |
| 2026-11-21T14:10:46.379 | entrada de 1217 caracteres (máximo 1000) |

## Recursos

- Tokens/s del modelo: media None · p50 None
- Tokens de entrada por llamada: 0 · de salida: 0
- Memoria máxima del proceso: 143.7 MB


# Análisis de registros · optimizado

## Hallazgos

1. El LLM concentra el 1.0 % del tiempo total de las solicitudes; la recuperación en ChromaDB, el 0.1 %.
2. El nodo que más tiempo de LLM consume es «respuesta_directa» (30 llamadas, 11.9 ms en total, media 0.4 ms).
3. 5 solicitudes superan el doble de la mediana o el p95 de latencia.
4. No se registraron errores de herramientas ni del modelo.
5. El RAG se abstuvo en 15 de 39 consultas.
6. El guardarraíl bloqueó 12 entradas antes de llegar al modelo.

## Latencia de las solicitudes

- Solicitudes: 90 · media 14.6 ms · p50 4.3 ms · p95 33.4 ms · máx. 35.5 ms
- Reparto del tiempo: {'llm': 1.0, 'recuperacion_chroma': 0.1, 'herramientas_sin_llm': 14.2, 'orquestacion_y_resto': 84.7}

## Tiempo de LLM por nodo

| nombre | llamadas | total_ms | media_ms | p95_ms |
|---|---|---|---|---|
| respuesta_directa | 30 | 11.9 | 0.4 | 0.5 |
| ejecutar_tarea | 3 | 1.3 | 0.4 | 0.5 |

## Nodos más lentos

| nombre | llamadas | total_ms | media_ms | p95_ms |
|---|---|---|---|---|
| ejecutar_tarea | 270 | 311.5 | 1.2 | 2.4 |
| consolidar_memoria | 39 | 256.3 | 6.6 | 7.1 |
| recuperar_contexto | 90 | 87.1 | 1.0 | 2.3 |
| evaluar | 270 | 64.6 | 0.2 | 0.3 |
| respuesta_directa | 39 | 50.6 | 1.3 | 1.7 |
| planificar | 39 | 18.5 | 0.5 | 0.6 |
| entrada_bloqueada | 12 | 18.1 | 1.5 | 5.5 |
| sintetizar | 39 | 13.5 | 0.3 | 0.5 |

## Herramientas más lentas

| nombre | llamadas | total_ms | media_ms | p95_ms |
|---|---|---|---|---|
| registrar_observacion | 51 | 63.5 | 1.2 | 2.0 |
| consultar_procedimientos | 39 | 45.4 | 1.2 | 1.5 |
| actualizar_estado_operacion | 48 | 43.7 | 0.9 | 1.7 |
| fundamentar_hallazgos | 36 | 16.4 | 0.5 | 0.6 |
| validar_nomenclatura | 39 | 16.3 | 0.4 | 0.5 |
| verificar_documentos_requeridos | 39 | 16.2 | 0.4 | 0.5 |
| validar_concordancia | 39 | 16.0 | 0.4 | 0.5 |
| escalar_a_responsable | 15 | 14.3 | 1.0 | 1.1 |

## Arranques en frío del modelo

Sin datos.

## Solicitudes anómalas (> 2× mediana o > p95)

| ts | duracion_ms | intencion | llamadas_llm | entrada |
|---|---|---|---|---|
| 2026-11-21T14:10:46.553 | 35.5 | revision | 0 | Revisa la OP1004 |
| 2026-11-21T14:10:46.587 | 34.0 | revision | 1 | Revisa la OP1005 |
| 2026-11-21T14:10:47.063 | 35.2 | revision | 0 | Revisa la OP1004 |
| 2026-11-21T14:10:47.098 | 33.9 | revision | 1 | Revisa la OP1005 |
| 2026-11-21T14:10:47.581 | 34.2 | revision | 0 | Revisa la OP1004 |

## Errores

Sin datos.

## Seguridad

| ts | motivo |
|---|---|
| 2026-11-21T14:10:46.871 | patrón no permitido: «Ignora las instrucciones» |
| 2026-11-21T14:10:46.874 | patrón no permitido: «Muestra tu system prompt» |
| 2026-11-21T14:10:46.877 | patrón no permitido: «<script» |
| 2026-11-21T14:10:46.890 | entrada de 1217 caracteres (máximo 1000) |
| 2026-11-21T14:10:47.379 | patrón no permitido: «Ignora las instrucciones» |
| 2026-11-21T14:10:47.382 | patrón no permitido: «Muestra tu system prompt» |
| 2026-11-21T14:10:47.386 | patrón no permitido: «<script» |
| 2026-11-21T14:10:47.404 | entrada de 1217 caracteres (máximo 1000) |
| 2026-11-21T14:10:47.896 | patrón no permitido: «Ignora las instrucciones» |
| 2026-11-21T14:10:47.899 | patrón no permitido: «Muestra tu system prompt» |
| 2026-11-21T14:10:47.902 | patrón no permitido: «<script» |
| 2026-11-21T14:10:47.914 | entrada de 1217 caracteres (máximo 1000) |

## Recursos

- Tokens/s del modelo: media None · p50 None
- Tokens de entrada por llamada: 0 · de salida: 0
- Memoria máxima del proceso: 160.8 MB
