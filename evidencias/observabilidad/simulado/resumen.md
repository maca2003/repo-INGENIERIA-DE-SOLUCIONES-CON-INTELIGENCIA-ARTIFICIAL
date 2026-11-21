# Métricas de observabilidad

- Proveedor: simulado (sin LLM)
- Fecha: 2026-11-21 14:10 · Python 3.13.18 · linux

| Métrica | base | optimizado |
|---|---:|---:|
| Precisión (%) | 76.7 | 80.0 |
| Consistencia entre repeticiones (%) | None | 100.0 |
| Similitud textual entre repeticiones (%) | None | 97.2 |
| Frecuencia de errores (%) | 0.0 | 0.0 |
| Latencia media (ms) | 19.6 | 15.1 |
| Latencia p50 (ms) | 12.3 | 4.7 |
| Latencia p95 (ms) | 36.3 | 33.7 |
| Primera consulta (ms) | 28.7 | 21.2 |
| Llamadas al LLM por caso | 1.57 | 0.37 |
| Tokens por caso | 0 | 0 |
| CPU por caso (ms) | 17.7 | 13.3 |
| Memoria máx. del proceso (MB) | 143.7 | 160.8 |

## Latencia media por tipo · base

- revision: 32.2 ms (p95 41.0 ms)
- seguimiento: 12.5 ms (p95 12.5 ms)
- consulta: 11.4 ms (p95 12.2 ms)
- seguridad: 5.2 ms (p95 10.9 ms)
- Casos incorrectos: C01, C03, C04, C05, C06, C08, C09

## Latencia media por tipo · optimizado

- revision: 29.0 ms (p95 34.7 ms)
- seguimiento: 3.8 ms (p95 4.0 ms)
- consulta: 4.1 ms (p95 4.8 ms)
- seguridad: 5.9 ms (p95 14.7 ms)
- Casos incorrectos: C01, C04, C05, C06, C08, C09

## Optimizado vs base

- Reducción de latencia media: 23.0 %
- Reducción de latencia p95: 7.2 %
- Reducción de llamadas al LLM: 76.4 %
- Diferencia de precisión: 3.3 puntos
- Por tipo: revision 9.9 %, seguimiento 69.6 %, consulta 64.0 %, seguridad -13.5 %
