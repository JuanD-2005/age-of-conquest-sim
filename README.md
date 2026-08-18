# Age of Conquest — Modelo de Simulación de Eventos Discretos

Grupo 3 — Ballesteros María, Morillo Gustavo, Juan Paredes

## Estructura del repositorio

Los `.py` del motor viven en la raíz a propósito: los imports son planos
(`from rng import ...`) y no dependen de la estructura de carpetas.

```
SIMU/
├── README.md                          este archivo
├── main.py                            (pendiente) interfaz de consola — Juan
│
├── entidades.py                       Partida, Imperio, Provincia, OrdenMilitar, Parámetros
├── lef.py                             Lista de Eventos Futuros
├── eventos.py                         los cinco eventos + IA
├── simulacion.py                      bucle principal e invariantes
├── rng.py                             GCL, generador combinado, banco de streams
├── pruebas.py                         corridas, chi-cuadrado, K-S
├── variables.py                       generación de variables aleatorias
│
├── test_modelo.py                     verificación de fronteras F1–F10
├── validar.py                         batería del generador
├── sensibilidad.py                    barrido de k_c, rho_atk, beta, S_min
├── replicas.py                        análisis de salida por réplicas (N=40)
├── visualizar.py                      gráficas de la bitácora (requiere matplotlib)
│
├── resultados/                        salidas generadas (CSV + figuras)
│   ├── replicas.csv
│   ├── bitacora_semilla7.csv
│   ├── historial_semilla7.csv
│   └── figuras/*.png                  (no versionadas — se regeneran)
│
├── docs/
│   ├── parcial2_anexo/                documento formal del Parcial II
│   │   ├── age_of_conquest_v4.md
│   │   ├── age_of_conquest_v4.pdf
│   │   └── diagramas/*.mermaid        3 diagramas de flujo
│   └── parcial3_informe/
│       ├── README.md
│       └── informe_p3.md              (pendiente) — María
│
└── entrega_p3/                        planificación de la entrega del Parcial III
    ├── 01_simulador/README.md         → entregable: main.py
    ├── 02_informe/README.md           → entregable: docs/parcial3_informe/informe_p3.md
    └── 03_defensa/
        ├── README.md
        ├── DEFENSA.md
        ├── notas_defensa.md           notas de apoyo (cada quien llena su sección)
        ├── estrategia_validacion.md   (pendiente) — Gustavo
        └── escenarios_demo.py         (pendiente) — Gustavo
```

## Ejecutar

Requiere Python 3.8+. El motor no tiene **dependencias externas**.

```bash
python3 validar.py       # batería del generador (§6 del documento)
python3 test_modelo.py   # condiciones de frontera F1-F10 (§4)
python3 -c "from simulacion import correr; p,s,st = correr(semilla=7, turnos_max=200); print(st)"
```

### Análisis complementario (Parcial III)

Estos scripts NO forman parte del motor validado — no tocan `eventos.py` /
`simulacion.py` / `rng.py` — son análisis externos sobre corridas del modelo.
El motor (`entidades.py`, `lef.py`, `eventos.py`, `simulacion.py`, `rng.py`,
`pruebas.py`, `variables.py`) no necesita nada fuera de la librería estándar
de Python, y eso no cambia: los scripts de análisis pueden depender de
paquetes externos si hace falta, pero cada uno declara lo que realmente usa.

```bash
python3 sensibilidad.py  # barrido de k_c, rho_atk, beta, S_min (§1.5) -- stdlib-only
python3 replicas.py      # 40 réplicas, IC 95% de turno_final y conquistas -> resultados/replicas.csv -- stdlib-only
python3 visualizar.py    # bitácora de la semilla 7 -> resultados/figuras/*.png -- REQUIERE matplotlib instalado
```

## Correspondencia módulo ↔ documento

Las secciones citadas son de
[`docs/parcial2_anexo/age_of_conquest_v4.md`](docs/parcial2_anexo/age_of_conquest_v4.md).

| Archivo | Responsabilidad | Secciones del documento |
|---------|-----------------|-------------------------|
| `rng.py` | GCL, generador combinado, streams | §6.2, §6.3 |
| `pruebas.py` | Corridas, Chi-cuadrado, K-S | §6.5 |
| `variables.py` | Generación de variables aleatorias | §6.4 |
| `entidades.py` | Entidades y parámetros | §1 |
| `lef.py` | Lista de Eventos Futuros | §3.3 |
| `eventos.py` | Los cinco eventos + IA | §2, §3 |
| `simulacion.py` | Bucle principal e invariantes | §3.3, §4 |
| `validar.py` | Validación del generador | §6 |
| `test_modelo.py` | Verificación de fronteras | §4 |
| `sensibilidad.py` | Sensibilidad de parámetros | §1.5 |
| `replicas.py` | Análisis de salida por réplicas | §1.5 |

## Dependencias entre módulos

```
entidades.py ──┐
lef.py ────────┼──> eventos.py ──> simulacion.py ──> test_modelo.py
rng.py ────────┤          │
variables.py ──┘          │
pruebas.py ──> validar.py ┘
```

Ningún módulo importa a `simulacion.py`, así que se pueden trabajar en paralelo.

## Reproducibilidad

Toda corrida queda determinada por la semilla maestra. `correr(semilla=7)` produce
siempre la misma partida. Las semillas deben ser **impares y no nulas**: el
constructor rechaza las pares (§6.2.4).
