# Escenario 10: Modo conversacional (ReAct) y memoria entre sesiones

- Modo: **simulado** (modelo y embeddings deterministas, sin LLM)
- Fecha de ejecución: 2026-11-03 00:35
- Objetivo: Verificar que el modelo selecciona herramientas y que una preferencia guardada se recupera desde otro hilo.
- Entrada del usuario: `¿Qué debe hacer el ejecutivo si existen diferencias en cantidades o peso? / ¿Qué observaciones tiene registradas la OP1003? / Recuerda que el cliente Ferretería Central Ltda prefiere que las comunicaciones se dirijan a Jorge Díaz`
- Tiempo de ejecución: 0.0 s

## Memoria de largo plazo recuperada

- [preferencia] Preferencia: cliente Ferretería Central Ltda prefiere que las comunicaciones se dirijan a Jorge Díaz (distancia 0.9672)
- [episodio] Episodio OP1003 de Ferretería Central Ltda (2026-11-03): estado Derivada a revisión; hallazgos: ninguno. (distancia 1.2615)
- [episodio] Episodio OP1003 de Ferretería Central Ltda (2026-11-03): estado Con observaciones; hallazgos: diferencia_bultos, diferencia_peso, nomenclatura. (distancia 1.3876)
- [preferencia] Preferencia de Comercial Pacífico Ltda: las comunicaciones de observaciones deben dirigirse a Paula Rojas, encargada de comercio exterior, e indicar un plazo de respuesta de 48 horas. (distancia 1.4226)

## Respuesta del agente

Resultado de buscar_memoria:
[{"tipo": "preferencia", "clave": "contacto_comunicaciones", "fecha": "2026-11-03T00:35:35", "valor": "Jorge Díaz", "operacion_id": "", "cliente": "Ferretería Central Ltda", "texto": "Preferencia: cliente Ferretería Central Ltda prefiere que las comunicaciones se dirijan a Jorge Díaz", "distancia": 0.9672}, {"tipo": "episodio", "cliente": "Ferretería Central Ltda", "valor": "", "clave": "", "fecha": "2026-11-03T00:35:35", "operacion_id": "OP1003", "texto": "Episodio OP1003 de Ferretería Central Ltda (2026-11-03): estado Derivada a revisión; hallazgos: ninguno.", "distancia": 1.2615}, {"operacion_id": "OP1003", "tipo": "episodio", "fecha": "2026-11-03T00:35:35", "clave": "", "cliente": "Ferre

## Observaciones

- **¿Qué debe hacer el ejecutivo si existen diferencias en cantidades o peso?** → Herramientas elegidas por el modelo: consultar_procedimientos

> Resultado de consultar_procedimientos:
{"respuesta": "Si existen diferencias en cantidades, valores, descripción, peso u otra información relevante, el ejecutivo no debe completar la preparación de la operación hasta obtener una aclaración o un documento corregido. Cantidad y peso informado.", "suficiente": true, "motivo": "respuesta respaldada", "fuentes": [{"fuente": "procedimiento_recepcion_documentos.md", "tipo": "interna_simulada", "distancia": 0.0}, {"fuente": "gestion_observaciones_operac
- **¿Qué observaciones tiene registradas la OP1003?** → Herramientas elegidas por el modelo: listar_observaciones

> Resultado de listar_observaciones:
[{"id": "OBS-0003", "operacion_id": "OP1003", "documento": "lista_empaque", "nivel": "corregible", "estado": "Cerrada", "descripcion": "Bultos: factura indica 120 y lista de empaque indica 112.", "accion_requerida": "Solicitar aclaración o documento corregido."}, {"id": "OBS-0004", "operacion_id": "OP1003", "documento": "lista_empaque", "nivel": "corregible", "estado": "Cerrada", "descripcion": "Peso (kg): factura indica 2400.0 y lista de empaque indica 2310.0.
- **Recuerda que el cliente Ferretería Central Ltda prefiere que las comunicaciones se dirijan a Jorge Díaz** → Herramientas elegidas por el modelo: guardar_memoria

> Resultado de guardar_memoria:
{"id": "mem-16c8825d8b94", "tipo": "preferencia", "cliente": "Ferretería Central Ltda", "contacto": "Jorge Díaz"}
- **(nuevo hilo) ¿Qué antecedentes o preferencias tienes de Ferretería Central Ltda?** → Intención 'conversacion', 4 recuerdos de largo plazo recuperados

> Resultado de buscar_memoria:
[{"tipo": "preferencia", "clave": "contacto_comunicaciones", "fecha": "2026-11-03T00:35:35", "valor": "Jorge Díaz", "operacion_id": "", "cliente": "Ferretería Central Ltda", "texto": "Preferencia: cliente Ferretería Central Ltda prefiere que las comunicaciones se dirijan a Jorge Díaz", "distancia": 0.9672}, {"tipo": "episodio", "cliente": "Ferretería Central Ltda", "valor": "", "clave": "", "fecha": "2026-11-03T00:35:35", "operacion_id": "OP1003", "texto": "Episodio 
