# Diagrama de orquestación del agente

Fase 10.2 de la guía. GitHub dibuja estos diagramas Mermaid automáticamente. Las versiones en imagen están en `documentacion/diagramas/`.

## 1. Orquestación de componentes

```mermaid
flowchart TD
    U[Ejecutivo<br/>Streamlit · CLI] -->|instrucción en lenguaje natural| MC

    subgraph AGENTE[Agente · LangGraph StateGraph]
        MC[gestionar_memoria_corta<br/>compacta el hilo] --> RC{recuperar_contexto<br/>intención + operación}
        RC -->|revisión| PL[planificar<br/>plan priorizado]
        PL --> EJ[ejecutar_tarea<br/>tarea de menor prioridad]
        EJ --> EV{evaluar<br/>¿cambian las condiciones?}
        EV -->|replanifica| EJ
        EV -->|hay borrador| HI[aprobacion_humana<br/>interrupt]
        HI --> EJ
        EV -->|plan terminado| SI[sintetizar<br/>informe + resumen LLM]
        RC -->|pregunta| RA[agente_conversacional<br/>ReAct: el LLM elige tools]
        RC -->|cola| PC[priorizar_cola]
        RC -->|OP inexistente| NX[operacion_inexistente]
        SI --> CM[consolidar_memoria<br/>episodio]
        RA --> CM
        PC --> CM
    end

    subgraph TOOLS[Herramientas @tool]
        TC[Consulta<br/>consultar_procedimientos · obtener_expediente<br/>listar_observaciones · buscar_memoria]
        TR[Razonamiento<br/>verificar_documentos · verificar_permisos<br/>validar_concordancia · fundamentar · priorizar]
        TE[Escritura<br/>registrar · redactar · escalar<br/>actualizar_estado · corrección · guardar_memoria]
    end

    subgraph MEM[Memoria y datos]
        M1[(Corto plazo<br/>SqliteSaver por hilo)]
        M2[(Largo plazo<br/>Chroma memoria_agente)]
        M3[(Conocimiento<br/>Chroma aduanarag · EP1)]
        M4[(Registros<br/>observaciones · estados · trazabilidad)]
    end

    LLM[LLM: Ollama llama3.2:3b<br/>u opcional Gemini Flash]

    EJ --> TR & TE
    RA --> TC
    TC --> M2 & M3
    TR --> M3
    TE --> M4 & M2
    AGENTE <--> M1
    RA & SI & TC -.-> LLM
    SI --> U
    HI -.->|¿aprobar?| U

    style PL fill:#ffe1b3
    style EV fill:#ffb3b3
    style HI fill:#b3d9ff
```

## 2. Grafo real exportado desde el código

`python src/exportar_diagrama.py` genera `documentacion/diagramas/grafo_langgraph.mmd` directamente desde el grafo compilado. Este diagrama es exactamente lo que se ejecuta.

## 3. Flujo de una revisión con replanificación

```mermaid
flowchart LR
    A([Revisa OPxxxx]) --> B[Contexto:<br/>expediente + recuerdos]
    B --> C[Plan priorizado]
    C --> D[Ejecutar tarea]
    D --> E{Evaluar}
    E -->|crítico| F[registrar + escalar p0<br/>sin comunicación]
    E -->|corregible| G[fundamentar · registrar<br/>borrador · aprobación]
    E -->|sin evidencia| H[escalar]
    E -->|falla| D
    F & G & H --> I{¿Quedan tareas?}
    E -->|sin hallazgos| I
    I -->|sí| D
    I -->|no| K[Estado INT-001<br/>informe + episodio]
```

## 4. Secuencia del caso OP1003 (incluye condición cambiante)

Ver `documentacion/diagramas/secuencia_op1003.mmd` o la imagen `secuencia_op1003.png`.
