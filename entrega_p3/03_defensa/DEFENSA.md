# Age of Conquest — Notas de Defensa

Grupo 3 — Ballesteros María, Morillo Gustavo, Juan Paredes

## Qué se implementó

El motor completo de `docs/parcial2_anexo/age_of_conquest_v4.md`, en cuatro módulos que se importan en cadena
(`entidades.py` → `lef.py` → `eventos.py` → `simulacion.py`), más `rng.py`, `variables.py` y
`pruebas.py` como soporte de aleatoriedad. Los siete corren **sin dependencias externas** —
solo biblioteca estándar de Python — porque el criterio de defensa exige poder mostrar que
ningún resultado depende de una librería que "hace la magia". `entidades.py` declara las
cuatro entidades y los parámetros de §1; `lef.py` es la cola de prioridad `(turno, prioridad,
secuencia)` de §3.3; `eventos.py` implementa los cinco eventos y la IA de §2–§3; `simulacion.py`
une todo en el bucle de eventos discretos y verifica los invariantes de §4. `test_modelo.py`
(21 verificaciones sobre fronteras F1–F10) y `validar.py` (batería del generador) son la red
de seguridad: ningún cambio se acepta si dejan de pasar completos. Los scripts de análisis
(`sensibilidad.py`, `replicas.py`, `visualizar.py`) sí usan numpy/matplotlib donde hace falta,
pero están separados del motor a propósito.

## Cuatro correcciones que solo aparecieron al ejecutar el modelo

Las correcciones 1–12 del documento salieron de revisarlo en papel; las 13–16 no eran
detectables ahí porque las ecuaciones son consistentes por separado — lo que falla es el
comportamiento agregado en el tiempo, y eso solo se ve corriendo el modelo.

- **13 — Deadlock de la IA expansiva.** La política `EXPANSIVO` solo podía atacar con su
  guarnición inicial, que nunca crecía, mientras el umbral de ataque sí crecía con las
  fortificaciones enemigas: 0 ataques en 100 turnos, 180.000 de oro ocioso. Se corrigió
  con una fase 2 de reclutamiento cuando ningún objetivo es atacable.
- **14 — Conquista matemáticamente inalcanzable.** Con un solo intercambio de bajas, la
  condición de conquista $S_{j,t+1}=0$ nunca se cumplía: 16 combates, 0 conquistas. Se
  corrigió resolviendo el asalto por rondas dentro del mismo evento.
- **15 — Fuga silenciosa de soldados.** La ecuación de conquista no definía qué pasaba con
  los supervivientes de un asalto no concluyente; en la implementación literal desaparecían
  del sistema. Se corrigió con una regla explícita de retirada al origen.
- **16 — Orden en estado no terminal al cierre.** `Ev_FinSimulacion` purgaba la LEF sin
  resolver las órdenes en tránsito, dejándolas en `EN_TRANSITO` — un estado no terminal según
  el ciclo de vida declarado en §1.1. Se corrigió cancelándolas explícitamente al cierre.

## El hallazgo de §6.2.2: ninguna batería certifica un generador por sí sola

Dos streams de un mismo GCL, separados por un salto fijo $k$, cumplen $x^{(2)}_i = A_k \cdot
x^{(1)}_i + B_k \pmod m$ para **todo** $i$: el valor de un stream determina exactamente el
del otro. Es grave porque en el combate (ec. 8) las bajas del atacante y del defensor se
generan en paralelo, en lockstep, dentro del mismo evento — exactamente el escenario donde
esa dependencia importaría. Y sin embargo los contrastes empíricos estándar **no la
detectan**: correlación de Pearson entre pares alineados = 0.014, prueba de corridas sobre
las secuencias intercaladas Z = −0.198 (ninguna rechaza H0). La aritmética modular destruye
la correlación lineal, así que una dependencia determinista y total pasa desapercibida. Es
la demostración empírica propia — no solo citada del curso — de por qué el análisis
estructural es indispensable y ninguna batería certifica un generador por sí sola. Por eso
la simulación usa el generador combinado (§6.2.3) para producir, no el GCL simple.

## Resultados del análisis de réplicas

40 réplicas independientes (semillas impares generadas con el GCL propio, `replicas.py`),
$T_{max}=200$:

| Métrica | Media | IC 95% (t de Student, df=39) |
|---|---|---|
| Turno final | 111.55 | [83.94, 139.16] |
| Conquistas por partida | 5.17 | [4.81, 5.54] |

21 de 40 partidas (52%) terminan con un ganador antes de $T_{max}$; el resto llega al
límite de turnos sin dominación territorial total. El intervalo de turno final es ancho
porque mezcla ambos desenlaces — es información, no ruido: la varianza real del sistema
incluye la posibilidad de empate por tiempo.

El barrido de sensibilidad (`sensibilidad.py`, mismo criterio de semillas fijas, N=40 por
valor tras la revisión de §1.5) muestra que $k_c$ domina el ritmo de la partida — de
$k_c=0.1$ a $0.5$ el turno medio de victoria baja de 46 a 25 y los combates por partida caen
de 19.1 a 5.3, con IC95% que no se solapan entre casi todos los pares de valores. **Revisión
sobre la primera versión de este análisis:** con N=10 semillas se había concluido que
$\rho_{atk}$, $\beta$ y $S_{min}$ eran "robustos" por no mostrar tendencia a ojo; con N=40 y
comparando intervalos de confianza en vez de medias, $\rho_{atk}$ **sí** resulta distinguible
(un $\rho_{atk}$ bajo exige menos superioridad para atacar, así que la IA ataca más seguido
con fuerzas menores: más combates, partidas más largas). La lección para la defensa: "no se
detectó tendencia con N=10" no era evidencia de robustez, era falta de poder estadístico.

Pero comparar IC es en sí un criterio conservador — que se solapen no prueba que no haya
diferencia, solo que ese criterio no la detectó. Por eso $\beta$ y $S_{min}$, que el
solapamiento de IC declaró "sin efecto", se confirmaron con una prueba diseñada para eso: t
de Welch entre cada par consecutivo del barrido, con Bonferroni sobre $\alpha=0.05$ (mismo
estándar de rigor que llevó a revisar $\rho_{atk}$, aplicado en la otra dirección). Resultado:
ningún par resulta significativo ($p$ entre 0.09 y 0.90 contra un $\alpha$ corregido de
0.0125) — **esta vez el criterio conservador no estaba ocultando nada**, y "sin efecto
distinguible" para $\beta$ y $S_{min}$ queda respaldado por una prueba de hipótesis real, no
solo por ausencia de evidencia en contra. (La t de Welch está implementada a mano, sin scipy
— no disponible en este entorno gestionado por el sistema — vía la función beta incompleta
regularizada, verificada contra la tabla t de `replicas.py`.)

Detalle completo, las cuatro tablas con IC y la tabla de p-valores de Welch en §1.5 del
documento.

## Figura

![Provincias por imperio a lo largo del tiempo, semilla 7](../../resultados/figuras/provincias_por_imperio.png)

Semilla 7: el imperio 0 (EXPANSIVO) pasa de 3 a 9 provincias y gana en el turno 29,
absorbiendo primero al imperio 1 (DEFENSIVO) y luego al imperio 2 (ECONÓMICO). Más figuras
(oro por imperio, población total) en `resultados/figuras/`, generadas por `visualizar.py`.
