# Age of Conquest — Modelo de Simulación de Eventos Discretos

Grupo 3 — Ballesteros María, Morillo Gustavo, Juan Paredes

## Ejecutar

Requiere Python 3.8+. **Sin dependencias externas.**

```bash
python3 validar.py       # batería del generador (§6 del documento)
python3 test_modelo.py   # condiciones de frontera F1-F10 (§4)
python3 -c "from simulacion import correr; p,s,st = correr(semilla=7, turnos_max=200); print(st)"
```

### Análisis complementario (Parcial III)

Estos scripts NO forman parte del motor validado — no tocan `eventos.py` /
`simulacion.py` / `rng.py` — son análisis externos sobre corridas del modelo.
Pueden usar numpy/matplotlib si hace falta (el motor sigue siendo stdlib-only).

```bash
python3 sensibilidad.py  # barrido de k_c, rho_atk, beta, S_min (§1.5 del documento)
python3 replicas.py      # 40 réplicas, IC 95% de turno_final y conquistas -> resultados/replicas.csv
python3 visualizar.py    # bitácora de la semilla 7 -> resultados/figuras/*.png
```

## Estructura

| Archivo | Responsabilidad | Secciones del documento |
|---------|-----------------|-------------------------|
| `age_of_conquest_v4.md` | Documento formal | todas |
| `rng.py` | GCL, generador combinado, streams | §6.2, §6.3 |
| `pruebas.py` | Corridas, Chi-cuadrado, K-S | §6.5 |
| `variables.py` | Generación de variables aleatorias | §6.4 |
| `entidades.py` | Entidades y parámetros | §1 |
| `lef.py` | Lista de Eventos Futuros | §3.3 |
| `eventos.py` | Los cinco eventos + IA | §2, §3 |
| `simulacion.py` | Bucle principal e invariantes | §3.3, §4 |
| `validar.py` | Validación del generador | §6 |
| `test_modelo.py` | Verificación de fronteras | §4 |

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
