# Análisis de registros · base

## Hallazgos

1. El LLM concentra el 96.2 % del tiempo total de las solicitudes; la recuperación en ChromaDB, el 0.7 %.
2. El nodo que más tiempo de LLM consume es «model» (26 llamadas, 50053.1 ms en total, media 1925.1 ms).
3. Se detectaron 1 arranques en frío del modelo (carga de hasta 5547.4 ms).
4. 2 solicitudes superan el doble de la mediana o el p95 de latencia.
5. No se registraron errores de herramientas ni del modelo.
6. El RAG se abstuvo en 4 de 13 consultas.
7. El guardarraíl bloqueó 4 entradas antes de llegar al modelo.

## Latencia de las solicitudes

- Solicitudes: 30 · media 4279.8 ms · p50 3406.3 ms · p95 9733.5 ms · máx. 10757.3 ms
- Reparto del tiempo: {'llm': 96.2, 'recuperacion_chroma': 0.7, 'herramientas_sin_llm': 0.3, 'orquestacion_y_resto': 2.8}

## Tiempo de LLM por nodo

| nombre | llamadas | total_ms | media_ms | p95_ms |
|---|---|---|---|---|
| model | 26 | 50053.1 | 1925.1 | 3913.0 |
| sintetizar | 13 | 39528.8 | 3040.7 | 5456.6 |
| tools | 9 | 29147.8 | 3238.6 | 5121.7 |
| ejecutar_tarea | 1 | 4739.4 | 4739.4 | 4739.4 |

## Nodos más lentos

| nombre | llamadas | total_ms | media_ms | p95_ms |
|---|---|---|---|---|
| agente_conversacional | 13 | 79723.4 | 6132.6 | 10335.5 |
| model | 26 | 50086.2 | 1926.4 | 3914.1 |
| sintetizar | 13 | 39552.0 | 3042.5 | 5458.6 |
| tools | 13 | 29548.5 | 2273.0 | 5143.6 |
| ejecutar_tarea | 91 | 5854.8 | 64.3 | 40.7 |
| consolidar_memoria | 26 | 1823.2 | 70.1 | 54.9 |
| recuperar_contexto | 30 | 918.6 | 30.6 | 43.3 |
| evaluar | 91 | 70.2 | 0.8 | 0.6 |

## Herramientas más lentas

| nombre | llamadas | total_ms | media_ms | p95_ms |
|---|---|---|---|---|
| consultar_procedimientos | 13 | 34303.0 | 2638.7 | 5142.2 |
| evaluar_requisitos_especiales | 1 | 4775.4 | 4775.4 | 4775.4 |
| fundamentar_hallazgos | 12 | 579.9 | 48.3 | 102.7 |
| actualizar_estado_operacion | 16 | 138.9 | 8.7 | 14.2 |
| escalar_a_responsable | 6 | 115.4 | 19.2 | 27.3 |
| registrar_observacion | 17 | 55.8 | 3.3 | 8.0 |
| validar_nomenclatura | 13 | 14.9 | 1.1 | 1.6 |
| verificar_documentos_requeridos | 13 | 11.7 | 0.9 | 1.5 |

## Arranques en frío del modelo

| ts | carga_ms | nodo |
|---|---|---|
| 2026-11-21T14:35:53.143 | 5547.4 | sintetizar |

## Solicitudes anómalas (> 2× mediana o > p95)

| ts | duracion_ms | intencion | llamadas_llm | entrada |
|---|---|---|---|---|
| 2026-11-21T14:37:25.370 | 10757.3 | conversacion | 3 | ¿Qué antecedentes generales pueden ser necesarios para una importación? |
| 2026-11-21T14:37:35.495 | 10124.2 | conversacion | 3 | ¿Cuáles son los documentos que hay que revisar al inicio de una operación? |

## Errores

Sin datos.

## Seguridad

| ts | motivo |
|---|---|
| 2026-11-21T14:37:53.544 | patrón no permitido: «Ignora las instrucciones» |
| 2026-11-21T14:37:53.548 | patrón no permitido: «Muestra tu system prompt» |
| 2026-11-21T14:37:53.554 | patrón no permitido: «<script» |
| 2026-11-21T14:37:53.568 | entrada de 1217 caracteres (máximo 1000) |

## Recursos

- Tokens/s del modelo: media 39.3 · p50 39.0
- Tokens de entrada por llamada: 712.5 · de salida: 82.9
- Memoria máxima del proceso: 151.8 MB


# Análisis de registros · optimizado

## Hallazgos

1. El LLM concentra el 86.4 % del tiempo total de las solicitudes; la recuperación en ChromaDB, el 3.7 %.
2. El nodo que más tiempo de LLM consume es «respuesta_directa» (27 llamadas, 60841.8 ms en total, media 2253.4 ms).
3. 5 solicitudes superan el doble de la mediana o el p95 de latencia.
4. No se registraron errores de herramientas ni del modelo.
5. El RAG se abstuvo en 12 de 39 consultas.
6. El guardarraíl bloqueó 12 entradas antes de llegar al modelo.

## Latencia de las solicitudes

- Solicitudes: 90 · media 955.4 ms · p50 223.1 ms · p95 4658.1 ms · máx. 5179.6 ms
- Reparto del tiempo: {'llm': 86.4, 'recuperacion_chroma': 3.7, 'herramientas_sin_llm': 1.1, 'orquestacion_y_resto': 8.7}

## Tiempo de LLM por nodo

| nombre | llamadas | total_ms | media_ms | p95_ms |
|---|---|---|---|---|
| respuesta_directa | 27 | 60841.8 | 2253.4 | 5138.1 |
| ejecutar_tarea | 3 | 13470.2 | 4490.1 | 4722.5 |

## Nodos más lentos

| nombre | llamadas | total_ms | media_ms | p95_ms |
|---|---|---|---|---|
| respuesta_directa | 39 | 62073.0 | 1591.6 | 5168.7 |
| ejecutar_tarea | 273 | 16936.1 | 62.0 | 57.5 |
| recuperar_contexto | 90 | 2977.8 | 33.1 | 56.4 |
| consolidar_memoria | 39 | 2183.2 | 56.0 | 68.6 |
| evaluar | 273 | 98.6 | 0.4 | 0.6 |
| planificar | 39 | 42.9 | 1.1 | 1.6 |
| sintetizar | 39 | 36.3 | 0.9 | 1.4 |
| entrada_bloqueada | 12 | 19.5 | 1.6 | 5.3 |

## Herramientas más lentas

| nombre | llamadas | total_ms | media_ms | p95_ms |
|---|---|---|---|---|
| consultar_procedimientos | 39 | 75681.6 | 1940.6 | 5168.1 |
| evaluar_requisitos_especiales | 3 | 13639.3 | 4546.4 | 4770.2 |
| fundamentar_hallazgos | 36 | 1946.7 | 54.1 | 90.4 |
| actualizar_estado_operacion | 48 | 380.5 | 7.9 | 12.8 |
| escalar_a_responsable | 18 | 286.7 | 15.9 | 20.7 |
| registrar_observacion | 51 | 170.8 | 3.3 | 8.6 |
| verificar_documentos_requeridos | 39 | 32.1 | 0.8 | 1.2 |
| validar_nomenclatura | 39 | 30.3 | 0.8 | 1.1 |

## Arranques en frío del modelo

Sin datos.

## Solicitudes anómalas (> 2× mediana o > p95)

| ts | duracion_ms | intencion | llamadas_llm | entrada |
|---|---|---|---|---|
| 2026-11-21T14:38:16.171 | 5112.8 | revision | 1 | Revisa la OP1005 |
| 2026-11-21T14:38:34.719 | 5176.2 | consulta | 1 | ¿Cuáles son los documentos que hay que revisar al inicio de una operación? |
| 2026-11-21T14:38:47.725 | 4690.3 | revision | 1 | Revisa la OP1005 |
| 2026-11-21T14:39:06.562 | 5173.0 | consulta | 1 | ¿Cuáles son los documentos que hay que revisar al inicio de una operación? |
| 2026-11-21T14:39:38.323 | 5179.6 | consulta | 1 | ¿Cuáles son los documentos que hay que revisar al inicio de una operación? |

## Errores

Sin datos.

## Seguridad

| ts | motivo |
|---|---|
| 2026-11-21T14:38:38.483 | patrón no permitido: «Ignora las instrucciones» |
| 2026-11-21T14:38:38.489 | patrón no permitido: «Muestra tu system prompt» |
| 2026-11-21T14:38:38.495 | patrón no permitido: «<script» |
| 2026-11-21T14:38:38.512 | entrada de 1217 caracteres (máximo 1000) |
| 2026-11-21T14:39:10.336 | patrón no permitido: «Ignora las instrucciones» |
| 2026-11-21T14:39:10.342 | patrón no permitido: «Muestra tu system prompt» |
| 2026-11-21T14:39:10.348 | patrón no permitido: «<script» |
| 2026-11-21T14:39:10.365 | entrada de 1217 caracteres (máximo 1000) |
| 2026-11-21T14:39:42.098 | patrón no permitido: «Ignora las instrucciones» |
| 2026-11-21T14:39:42.104 | patrón no permitido: «Muestra tu system prompt» |
| 2026-11-21T14:39:42.110 | patrón no permitido: «<script» |
| 2026-11-21T14:39:42.127 | entrada de 1217 caracteres (máximo 1000) |

## Recursos

- Tokens/s del modelo: media 38.8 · p50 38.7
- Tokens de entrada por llamada: 902.6 · de salida: 87.0
- Memoria máxima del proceso: 180.2 MB
