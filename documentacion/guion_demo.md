# Guion de la demostración (10 minutos)

Fase 11 de la guía: no se muestra todo lo que se hizo, sino una historia en **cuatro escenas** que prueban los indicadores. Cada escena tiene un punto clave para que el evaluador lo recuerde.

## Preparación (antes de exponer)

```cmd
.venv\Scripts\activate
python src\probar_modelos.py                 :: el modelo responde
rmdir /s /q salidas                          :: memoria y registros limpios
streamlit run src\app_agente.py              :: elegir "real" y presionar "Nuevo hilo"
```

## Minuto 0–1 · Contexto (Macarena)

- Quiénes somos y qué problema resolvemos: la revisión documental de una agencia de aduanas.
- Mostrar Streamlit: "Este es nuestro agente de revisión de expedientes".

## Minutos 1–4 · Escena 1: caso con observaciones (IE1, IE2, IE3) — Macarena

- Escribir: `Revisa la OP1003`
- Mostrar la pestaña **Plan**: el orden de ejecución sigue las prioridades. Después mostrar **Decisiones**: el agente agregó tareas al ver las diferencias de bultos y peso.
- Aparece el borrador y el botón **Aprobar envío**: es el `interrupt()`; el agente no escribe al cliente sin una persona.
- Aprobar. Luego preguntar `¿Qué observaciones quedaron?`: responde sobre OP1003 sin que se la nombren (memoria corta).
- **Punto clave:** varias herramientas encadenadas sin intervención, más la supervisión humana.

## Minutos 4–6 · Escena 2: memoria de largo plazo (IE3, IE4) — Roberto

- Escribir: `Revisa la OP1004`
- Pestaña **Memoria**: aparece el antecedente OP0950 de Distribuidora Sur SpA.
- Pestaña **Plan**: la concordancia **reforzada** se adelanta. Mencionar la prueba de control: sin memoria el plan es otro (`evidencias/agente/<proveedor>/escenario_05.md`).
- **Punto clave:** lo que el agente recuerda cambia lo que hace.

## Minutos 6–8 · Escena 3: condición cambiante y replanificación (IE5, IE7) — Roberto

- Escribir: `Llegó la lista de empaque corregida de la OP1003, reprocésala`
- El plan nuevo empieza con `incorporar_correccion` → `verificar_resolucion` → `cerrar_observaciones`.
- El estado pasa de "Con observaciones" a "Derivada a revisión".
- **Punto clave:** el agente ajustó su plan porque cambió el entorno.

## Minutos 8–9 · Escena 4: escalamiento justificado (IE5, IE7) — Macarena

- Volver a la OP1004: verificó permisos primero (prioridad 0), escaló y **no** redactó un correo.
- Si hay tiempo, `Revisa la OP1005` (drones): consulta el RAG antes de suponer requisitos.
- **Punto clave:** cuando no corresponde decidir, el agente escala y explica por qué.

## Minuto 9–10 · Cierre (ambos, IE8, IE9, IE10)

- Diagrama de orquestación y README reproducible en GitHub.
- Resultados: pruebas automatizadas aprobadas y 10/10 escenarios ([completar con su ejecución real]).
- Límites declarados (`documentacion/alcance.md`).

## Plan B (si falla el modelo o internet)

1. El flujo de revisión no depende del LLM para decidir: si el modelo no responde, la síntesis pasa a modo degradado y la revisión igual termina.
2. Mostrar las capturas de `evidencias/capturas/<proveedor>/` y los informes de `evidencias/agente/<proveedor>/`.
3. Video de respaldo (2 minutos) grabado con la grabadora de pantalla del sistema.
4. Si nada de lo anterior funciona: `streamlit run src\app_agente.py` en modo **simulado** muestra la misma orquestación sin LLM. Hay que decirlo explícitamente.

## Roles (participación equitativa)

| Integrante | Escenas | Tiempo aproximado |
|---|---|---|
| Macarena Muñoz | Contexto, escena 1, escena 4 | ~5 min |
| Roberto González | Escena 2, escena 3, arquitectura y justificación | ~5 min |
| Ambos | Cierre y preguntas | — |
