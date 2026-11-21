# Escenario 10: Modo conversacional (ReAct) y memoria entre sesiones

- Modo: **simulado** (modelo y embeddings deterministas, sin LLM)
- Fecha de ejecución: 2026-11-21 14:13
- Objetivo: Verificar que el modelo selecciona herramientas y que una preferencia guardada se recupera desde otro hilo.
- Entrada del usuario: `¿Qué debe hacer el ejecutivo si existen diferencias en cantidades o peso? / ¿Qué observaciones tiene registradas la OP1003? / Recuerda que el cliente Ferretería Central Ltda prefiere que las comunicaciones se dirijan a Jorge Díaz`
- Tiempo de ejecución: 0.0 s

## Memoria de largo plazo recuperada

- [preferencia] Preferencia: cliente Ferretería Central Ltda prefiere que las comunicaciones se dirijan a Jorge Díaz (distancia 0.9672)
- [episodio] Episodio OP1003 de Ferretería Central Ltda (2026-11-21): estado Derivada a revisión; hallazgos: ninguno. (distancia 1.2615)
- [episodio] Episodio OP1003 de Ferretería Central Ltda (2026-11-21): estado Con observaciones; hallazgos: diferencia_bultos, diferencia_peso, nomenclatura. (distancia 1.3876)
- [preferencia] Preferencia de Comercial Pacífico Ltda: las comunicaciones de observaciones deben dirigirse a Paula Rojas, encargada de comercio exterior, e indicar un plazo de respuesta de 48 horas. (distancia 1.4226)

## Respuesta del agente

Resultado de buscar_memoria:
[{"clave": "contacto_comunicaciones", "cliente": "Ferretería Central Ltda", "tipo": "preferencia", "operacion_id": "", "valor": "Jorge Díaz", "fecha": "2026-11-21T14:13:11", "texto": "Preferencia: cliente Ferretería Central Ltda prefiere que las comunicaciones se dirijan a Jorge Díaz", "distancia": 0.9672}, {"cliente": "Ferretería Central Ltda", "operacion_id": "OP1003", "valor": "", "clave": "", "tipo": "episodio", "fecha": "2026-11-21T14:13:11", "texto": "Episodio OP1003 de Ferretería Central Ltda (2026-11-21): estado Derivada a revisión; hallazgos: ninguno.", "distancia": 1.2615}, {"tipo": "episodio", "clave": "", "cliente": "Ferretería Central Ltda", "valor": "diferencia_bultos, diferenc

## Observaciones

- **¿Qué debe hacer el ejecutivo si existen diferencias en cantidades o peso?** → Ruta directa (sin ReAct): consultar_procedimientos

> Si existen diferencias en cantidades, valores, descripción, peso u otra información relevante, el ejecutivo no debe completar la preparación de la operación hasta obtener una aclaración o un documento corregido. Cantidad y peso informado.

Fuentes: procedimiento_recepcion_documentos.md, gestion_observaciones_operacion.md
- **¿Qué observaciones tiene registradas la OP1003?** → Ruta directa (sin ReAct): listar_observaciones

> Observaciones registradas de la OP1003:
- OBS-0003 [corregible · Cerrada] Bultos: factura indica 120 y lista de empaque indica 112.
- OBS-0004 [corregible · Cerrada] Peso (kg): factura indica 2400.0 y lista de empaque indica 2310.0.
- OBS-0005 [informativa · Cerrada] El archivo 'lista empaque final.pdf' no sigue la convención LISTAEMPAQUE_OP1003_V1.
- **Recuerda que el cliente Ferretería Central Ltda prefiere que las comunicaciones se dirijan a Jorge Díaz** → Herramientas elegidas por el modelo: guardar_memoria

> Resultado de guardar_memoria:
{"id": "mem-bf1e0bf9a00c", "tipo": "preferencia", "cliente": "Ferretería Central Ltda", "contacto": "Jorge Díaz"}
- **(nuevo hilo) ¿Qué antecedentes o preferencias tienes de Ferretería Central Ltda?** → Intención 'conversacion', 4 recuerdos de largo plazo recuperados

> Resultado de buscar_memoria:
[{"clave": "contacto_comunicaciones", "cliente": "Ferretería Central Ltda", "tipo": "preferencia", "operacion_id": "", "valor": "Jorge Díaz", "fecha": "2026-11-21T14:13:11", "texto": "Preferencia: cliente Ferretería Central Ltda prefiere que las comunicaciones se dirijan a Jorge Díaz", "distancia": 0.9672}, {"cliente": "Ferretería Central Ltda", "operacion_id": "OP1003", "valor": "", "clave": "", "tipo": "episodio", "fecha": "2026-11-21T14:13:11", "texto": "Episodio 
