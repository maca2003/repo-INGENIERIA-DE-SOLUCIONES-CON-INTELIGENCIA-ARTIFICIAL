# Contrato de las herramientas

Fase 1.3 de la guía: qué recibe y qué devuelve cada herramienta. Todas están definidas con `@tool` de LangChain en `src/agente/herramientas/`, tienen docstring en español (es lo que lee el LLM) y se prueban en `tests/test_herramientas.py`.

La guía pide 7 herramientas; AduanaAgent tiene 20, agrupadas en tres capacidades.

## Consulta (leen sin modificar) — `consulta.py`

| Herramienta | Entrada | Salida | Para qué la usa el agente |
|---|---|---|---|
| `consultar_procedimientos` | `pregunta: str` | `{respuesta, suficiente, motivo, fuentes[]}` | RAG sobre la base de la EP1, con umbral de distancia y abstención |
| `obtener_expediente` | `operacion_id: str` | expediente + `estado_actual` + `observaciones_abiertas` | Conocer la operación (o `{error}` si no existe) |
| `listar_observaciones` | `operacion_id: str = ""` | `list[{id, nivel, estado, descripcion, ...}]` | Responder "¿qué quedó pendiente?" |
| `buscar_memoria` | `consulta: str, cliente: str = ""` | `list[recuerdo]` con distancia | Memoria semántica de largo plazo |

## Razonamiento (analizan y clasifican) — `razonamiento.py`

| Herramienta | Entrada | Salida | Regla que aplica |
|---|---|---|---|
| `verificar_documentos_requeridos` | `operacion_id` | `{requeridos, faltantes, hallazgos[]}` | INT-001: documentos iniciales; certificado de origen si hay preferencia |
| `verificar_permisos` | `operacion_id` | `{regulada, organismos_requeridos, hallazgos[]}` | EXT-001: control previo por categoría |
| `validar_concordancia` | `operacion_id, reforzada: bool` | `{ejecutada, hallazgos[]}` | INT-001: bultos, peso, descripción, valor, importador |
| `validar_nomenclatura` | `operacion_id` | `{hallazgos[]}` | INT-003: `TIPO_OPERACION_VERSION` |
| `clasificar_observacion` | `tipo_hallazgo` | `{nivel, accion, regla}` | INT-002: informativa / corregible / crítica |
| `evaluar_requisitos_especiales` | `operacion_id` | `{consulta, hallazgos[]}` | Mercancía no catalogada: consulta el RAG antes de suponer |
| `fundamentar_hallazgos` | `tipos: list[str]` | `list[{tipo, respaldado, fuente_recuperada, distancia}]` | Cada hallazgo debe tener respaldo documental |
| `verificar_resolucion_observaciones` | `operacion_id` | `{resueltas[], pendientes[]}` | INT-002: cierre de observaciones |
| `priorizar_operaciones` | `fecha_referencia: str = ""` | `list[{orden, operacion_id, puntaje, motivos}]` | Urgencia, cercanía del arribo y riesgo |

Cada hallazgo tiene la misma forma: `{tipo, documento, descripcion, clave, nivel, accion, regla}`. Así cualquier herramienta de escritura puede consumirlo.

## Escritura (cambian el estado del mundo) — `escritura.py`

| Herramienta | Entrada | Salida | Trazabilidad |
|---|---|---|---|
| `registrar_observacion` | `operacion_id, tipo, documento, descripcion, clave` | observación con `id` (sin duplicar) | "Detecta una inconsistencia" |
| `cerrar_observacion` | `id_observacion, resolucion` | observación cerrada | "Cierra una observación" |
| `redactar_comunicacion_cliente` | `operacion_id, observaciones[], destinatario, plazo_respuesta, urgente` | `{ruta, texto, estado: borrador}` | "Redacta comunicación al cliente" |
| `actualizar_estado_operacion` | `operacion_id, estado, motivo` | `{estado, estado_anterior}` | "Modifica el estado de una operación" |
| `escalar_a_responsable` | `operacion_id, motivo, ids_observaciones[]` | `{ruta, escaladas}` | "Escala una observación" |
| `recibir_documento_corregido` | `ruta_correccion` | `{version_nueva, version_anterior}` | "Agrega o reemplaza un archivo" |
| `guardar_memoria` | `texto, tipo, cliente, operacion_id, contacto` | `{id}` | "Guarda memoria de largo plazo" |

## Cómo se encadenan

```text
obtener_expediente ─┬─> verificar_documentos / verificar_permisos / validar_concordancia ─> hallazgos[]
                    │                                                                        │
buscar_memoria ─────┘ (cambia el plan)                                 fundamentar_hallazgos ┤ (RAG)
                                                                                             ▼
                                         registrar_observacion ─> escalar | redactar_comunicacion
                                                                                             ▼
                                                                         actualizar_estado_operacion
```

Cada salida alimenta una entrada. Es la recomendación de la guía para evitar herramientas que necesitan datos que ninguna otra entrega.
