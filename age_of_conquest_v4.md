# Age of Conquest: Formalización Cuantitativa y Lógica del Sistema

**Grupo 3** — Ballesteros María, Morillo Gustavo, Juan Paredes

**Fase del proyecto:** Diseño Lógico y Matemático + Motor de Aleatoriedad
**Versión 4** — corrige inconsistencias dimensionales, de trazabilidad y de terminación detectadas en la revisión de la v3, e incorpora la formalización estocástica requerida para la fase de implementación.

---

## Abstract

Este documento formaliza matemáticamente las entidades, atributos y eventos definidos en el Modelo Conceptual (Parcial I): `Partida`, `Imperio`, `Provincia` y `OrdenMilitar`, junto con los eventos `Ev_InicioTurno`, `Ev_LlegadaOrden`, `Ev_ResolucionCombate`, `Ev_CrisisFinanciera` y `Ev_FinSimulacion`. Toda notación es trazable a un atributo o método declarado en el Parcial I. La versión 4 añade la especificación completa del generador de números pseudoaleatorios, la partición en streams por subsistema y los contrastes empíricos que validan la secuencia, de modo que el documento sea programable sin decisiones implícitas.

### Registro de cambios respecto a la v3

| # | Sección | Corrección |
|---|---------|------------|
| 1 | 1.3 / 1.4 | β estaba declarado como variable auxiliar **y** como parámetro fijo. Se conserva únicamente como parámetro. |
| 2 | 1.4 | `k_c` tenía unidad `1/turno` pero se usa como escalar de una probabilidad. Corregido a adimensional. |
| 3 | 1.4 | `K_j` estaba en "parámetros fijos" con subíndice de provincia. Reclasificado como parámetro estructural indexado. |
| 4 | 2.1 | La saturación poblacional se enunciaba en prosa. Ahora es función por partes (ec. 1). |
| 5 | 2.5 | Indeterminación 0/0 en la ec. 8 cuando `A_k = D_eff = 0`. Resuelta explícitamente. |
| 6 | 2.6 | La deserción producía soldados fraccionarios y no garantizaba terminación. Corregida con función piso y cota de iteraciones. |
| 7 | 3.1 | La recaudación usaba la población **ya actualizada**, contradiciendo las ecs. 2 y 4. Corregido con snapshot. |
| 8 | 3.1 | Numeración de pasos duplicada (dos pasos "3"). Renumerada. |
| 9 | 3.2 | El árbol de decisión de la IA usaba umbrales sin definir. Ahora tiene parámetros numéricos. |
| 10 | 3.4 | `Ev_LlegadaOrden` se prometía en el abstract pero no se desarrollaba. Añadido. |
| 11 | 1.1 / 5 | `σ_k,t` y `L_k` estaban declaradas sin uso; `estadoActivo` y `estadoProvincia` se usaban sin declarar. Ambas cosas resueltas. |
| 12 | 6 (nueva) | Formalización del generador, streams, generación de variables aleatorias y validación empírica. |
| 13 | 3.2 | La política `EXPANSIVO` no tenía mecanismo de reclutamiento: sólo podía atacar con la guarnición inicial, que nunca crece. **Deadlock estructural** detectado en implementación. Añadida fase de acumulación. |
| 14 | 2.5 | La conquista exigía $S_{j,t+1}=0$ en un único intercambio, inalcanzable con $k_c=0.3$ (16 combates → 0 conquistas). El asalto ahora se resuelve por rondas. |
| 15 | 2.5 | La ec. 10 dejaba $A'_k$ **indefinido** cuando no hay conquista: los supervivientes desaparecían del sistema. Añadida regla de retirada. |
| 16 | 3.5 | `Ev_FinSimulacion` dejaba órdenes en vuelo con $\sigma_k = $ `EN_TRANSITO`, un estado no terminal. Ahora se cancelan al cierre. |

---

# 1. Diccionario Formal de Variables y Parámetros

## 1.1 Variables de Estado (Niveles / Acumuladores)

Persisten entre turnos y sólo son modificadas por los eventos de la LEF.

| Símbolo | Nombre (Parcial I) | Entidad | Unidad teórica | Descripción |
|---------|--------------------|---------|----------------|-------------|
| $t$ | `relojSimulacion` | Partida | turno (entero) | Instante discreto de la simulación |
| $E_{i,t}$ | `oroDisponible` | Imperio $i$ | oro | Reserva de oro del imperio $i$ al inicio del turno $t$ |
| $\Phi_{i,t}$ | `estadoFinanciero` | Imperio $i$ | enum | `SOLVENTE` \| `BANCARROTA` |
| $\Psi_{i,t}$ | `estadoActivo` | Imperio $i$ | booleano | `True` mientras el imperio controle ≥ 1 provincia |
| $P_{j,t}$ | `poblacion` | Provincia $j$ | habitantes | Población de la provincia $j$ en el turno $t$ |
| $S_{j,t}$ | `tropasEstacionadas` | Provincia $j$ | soldados | Tropas presentes en la provincia $j$ |
| $F_{j,t}$ | `nivelFortificacion` | Provincia $j$ | nivel $(0..F_{max})$ | Estado defensivo de la provincia $j$ |
| $O_{j,t}$ | `idPropietario` | Provincia $j$ | idImperio | Imperio que controla la provincia $j$ |
| $\Omega_{j,t}$ | `estadoProvincia` | Provincia $j$ | enum | `POBLADA` \| `ABANDONADA` |
| $\sigma_{k,t}$ | `estadoOrden` | OrdenMilitar $k$ | enum | `EMITIDA` \| `EN_TRANSITO` \| `RESUELTA` \| `CANCELADA` |

> **Corrección 11.** $\Psi_{i,t}$ y $\Omega_{j,t}$ se usaban en la Sección 4 de la v3 sin haber sido declaradas. Quedan formalizadas aquí. $\sigma_{k,t}$ era una variable huérfana: ahora gobierna el ciclo de vida de las órdenes en §3.4.

## 1.2 Variables de Flujo (Tasas por turno)

| Símbolo | Método (Parcial I) | Unidad | Descripción |
|---------|--------------------|--------|-------------|
| $\dot{P}_{j,t}$ | `actualizarDemografia` | hab./turno | Crecimiento neto de población |
| $R_{j,t}$ | `calcularProduccionOro` | oro/turno | Recaudación tributaria de la provincia $j$ |
| $R^{tot}_{i,t}$ | `calcularProduccionOro` | oro/turno | Recaudación agregada del imperio $i$ |
| $G_{i,t}$ | `pagarMantenimiento` | oro/turno | Gasto de mantenimiento militar |
| $B^{A}_{k,t}$, $B^{D}_{k,t}$ | `resolverCombate` | sold./evento | Bajas del atacante y del defensor |
| $\Delta S^{des}_{i,t}$ | `Ev_CrisisFinanciera` | sold./turno | Tropas perdidas por deserción |

> **Corrección 11 (cont.).** En la v3, $\Delta S^{des}_{i,t}$ se declaraba aquí pero la ecuación de deserción usaba otra notación. En §2.6 el símbolo ya aparece en su propia fórmula.

## 1.3 Variables Auxiliares (Control / Lógica de decisión)

| Símbolo | Nombre (Parcial I) | Unidad | Descripción |
|---------|--------------------|--------|-------------|
| $\pi_i$ | `politicaEstrategica` | enum | `EXPANSIVO` \| `DEFENSIVO` \| `ECONOMICO` |
| $\tau_k$ | `tiempoViaje` | turnos | Retardo entre emisión y llegada de la orden $k$ |
| $L_k$ | `turnoLlegada` | turno | $L_k = t_{emisión} + \tau_k$. Marca temporal de encolado en la LEF |
| $A_k$ | `fuerzaMilitar` | soldados | Tropas en tránsito asociadas a la orden $k$ |
| $D^{eff}_{j,t}$ | (en `resolverCombate`) | soldados | Fuerza defensiva efectiva de la provincia $j$ |

> **Corrección 1.** β fue eliminado de esta tabla: es una constante del juego, no una variable de control. Su única declaración está en §1.4.

## 1.4 Parámetros Fijos (Constantes del sistema)

| Símbolo | Descripción | Unidad | Valor |
|---------|-------------|--------|-------|
| $I$ | Tasa impositiva | oro/(hab·turno) | 0.02 |
| $r$ | `tasaCrecimiento` | 1/turno | 0.05 |
| $c_m$ | Costo de mantenimiento | oro/(sold·turno) | 0.5 |
| $c_{mov}$ | Costo de movilización | oro/soldado | 2.0 |
| $c_{fort}$ | Costo de un nivel de fortificación | oro/nivel | 500 |
| $k_c$ | Letalidad de combate | **adimensional** | 0.3 |
| $\beta$ | Bono defensivo por nivel de fortificación | adimensional/nivel | 0.25 |
| $\delta$ | Fracción de deserción por iteración | adimensional $(0,1)$ | 0.10 |
| $\rho_{atk}$ | Ratio mínimo de superioridad para atacar | adimensional | 1.5 |
| $S_{min}$ | Guarnición mínima defensiva | soldados | 50 |
| $n_{max}^{des}$ | Cota de iteraciones de deserción | iteraciones | 200 |
| $n_{rondas}$ | Rondas máximas por asalto | rondas | 20 |
| $F_{max}$ | Fortificación máxima | nivel | 4 |
| $T_{max}$ | `tiempoMaximo` | turnos | 500 |

**Parámetros estructurales indexados** (fijos durante la partida, distintos por provincia; se leen de la configuración del mapa):

| Símbolo | Descripción | Unidad | Rango típico |
|---------|-------------|--------|--------------|
| $K_j$ | `capacidadSoporte` de la provincia $j$ | habitantes | $[10^4,\ 10^5]$ |
| $(a_\tau, c_\tau, b_\tau)$ | Mín., moda y máx. del tiempo de viaje | turnos | $(1,\ 2,\ 5)$ |

> **Corrección 2.** $k_c$ figuraba con unidad `1/turno`. Como $p_A = k_c \cdot \frac{A_k}{A_k + D^{eff}}$ es el parámetro de una Binomial, debe ser adimensional; de lo contrario $p_A$ tendría unidades y no sería una probabilidad válida. Con $k_c$ adimensional se garantiza además $p_A, p_D \in [0,\, k_c] \subset [0,1]$.
>
> **Corrección 3.** $K_j$ llevaba subíndice de provincia dentro de la tabla de constantes globales. Se reclasifica: es fijo en el tiempo pero variable en el espacio.

### Nota de coherencia

El Parcial I menciona "moral" como ejemplo genérico. Ese atributo **no existe** en las entidades formalizadas; su rol funcional (colapso de una facción) lo cumplen $\Phi_{i,t} = \texttt{BANCARROTA}$ y $\Psi_{i,t} = \texttt{False}$. Este documento no introduce "moral".

### 1.5 Sensibilidad de los parámetros clave

Los valores de §1.4 son valores de referencia razonados a partir del diseño (ver justificaciones puntuales en cada corrección), **no** una calibración contra datos reales de partidas de Age of Conquest, porque esos datos no existen. Ante la pregunta "¿por qué 0.3 y no 0.5?", la respuesta no es empírica sino de sensibilidad: `sensibilidad.py` corre un barrido de $k_c$, $\rho_{atk}$, $\beta$ y $S_{min}$ sobre un conjunto fijo de semillas impares ($T_{max}=200$) y mide el turno de victoria, el % de corridas sin ganador y el número de combates.

> **Revisión (N=10 → N=40).** La primera versión de esta sección usaba 10 semillas por valor de parámetro y comparaba solo las medias, concluyendo "el sistema es robusto a $\rho_{atk}$, $\beta$ y $S_{min}$". Esa lectura confundía "no se detectó tendencia" con "no hay efecto": con N=10 la varianza muestral es suficiente para enmascarar un efecto real. Se subió a N=40 (mismo orden que las réplicas de §7) y la conclusión para cada parámetro ahora se decide comparando los **intervalos de confianza al 95%** (t de Student, mismo criterio que en el análisis de réplicas) de cada par de valores del barrido, no la media a ojo. El resultado cambió para uno de los tres: **$\rho_{atk}$ sí tiene un efecto distinguible con N=40; $\beta$ y $S_{min}$ siguen sin mostrarlo.**
>
> **Revisión 2 (confirmación con t de Welch + Bonferroni).** Comparar si dos IC 95% se solapan es un criterio **conservador**: que se toquen no demuestra ausencia de diferencia, solo que ese criterio en particular no la detectó — es más estricto que una prueba de hipótesis de dos muestras propiamente dicha. Para $\beta$ y $S_{min}$, que el criterio de solapamiento declaró "sin efecto distinguible", se corrió además una prueba t de Welch (varianzas no asumidas iguales) entre cada par consecutivo del barrido, con el umbral de significancia corregido por Bonferroni ($\alpha=0.05$ dividido entre el número de pares consecutivos comparados en cada familia turno_victoria/combates) para no inflar el riesgo de falso positivo por comparaciones múltiples — el mismo estándar de rigor que llevó a revisar $\rho_{atk}$. **Esta vez el resultado no cambia**: ningún par consecutivo de $\beta$ ni de $S_{min}$ resulta significativo ($p$ entre 0.09 y 0.90, todos por encima del $\alpha$ corregido de 0.0125). La diferencia frente a la revisión anterior es metodológica, no de conclusión: "sin efecto distinguible" para $\beta$ y $S_{min}$ ahora está respaldado por una prueba diseñada para detectar el efecto y no lo encontró, no solo por ausencia de evidencia en contra. No se repitió para $k_c$ ni $\rho_{atk}$: el criterio de IC, ya más exigente, había mostrado efecto en ambos.

**$k_c$ sigue dominando el comportamiento agregado — confirmado con N=40.**

| $k_c$ | turno victoria (media, IC95%) | % sin ganador | combates (media, IC95%) |
|-------|-------------------------------|----------------|---------------------------|
| 0.1 | 46.0 (n=1 con ganador, sin IC) | 98% | 19.1 [16.8, 21.5] |
| 0.2 | 39.6 [36.3, 43.0] | 50% | 13.5 [12.3, 14.8] |
| 0.3 (ref.) | 28.9 [26.8, 31.1] | 52% | 8.0 [7.1, 8.9] |
| 0.4 | 25.7 [21.7, 29.8] | 62% | 5.8 [5.2, 6.3] |
| 0.5 | 24.8 [21.0, 28.6] | 62% | 5.3 [4.9, 5.7] |

Con N=40 el efecto es distinguible en la métrica de combates entre casi todos los pares de valores (IC95% disjuntos), y en turno de victoria entre 0.2 y el resto. A $k_c=0.1$ el 98% de las corridas no produce ganador en $T_{max}=200$ — la letalidad es tan baja que casi ninguna conquista se completa a tiempo, coherente con la Corrección 14 (conquista por rondas: menos letalidad por ronda, más rondas necesarias). Es coherente con la ec. 7 — $k_c$ escala directamente $p_A + p_D$ — y confirma que el sistema es sensible a este parámetro en todo el rango probado, no sólo cerca de 0.3.

**Hallazgo revisado — $\rho_{atk}$ sí tiene efecto distinguible; $\beta$ y $S_{min}$ no, incluso con N=40.**

| $\rho_{atk}$ | turno victoria (media, IC95%) | % sin ganador | combates (media, IC95%) |
|--------------|-------------------------------|----------------|---------------------------|
| 1.1 | 35.5 [33.4, 37.6] | 45% | 11.2 [10.2, 12.1] |
| 1.3 | 31.3 [29.5, 33.2] | 40% | 10.3 [9.5, 11.0] |
| 1.5 (ref.) | 28.9 [26.8, 31.1] | 52% | 8.0 [7.1, 8.9] |
| 1.8 | 27.8 [25.2, 30.5] | 52% | 7.2 [6.6, 7.8] |
| 2.2 | 27.5 [25.6, 29.4] | 62% | 5.8 [4.9, 6.7] |

Con N=10 esta tendencia no era distinguible del ruido; con N=40 el IC95% de turno de victoria en $\rho_{atk}=1.1$ ($[33.4, 37.6]$) ya no se solapa con el de $1.5$, $1.8$ ni $2.2$, y el de combates es distinguible entre casi todos los pares. La dirección tiene lectura causal: un $\rho_{atk}$ bajo exige menos superioridad para atacar (§3.2, ec. de `requerido`), así que la IA `EXPANSIVO` lanza ataques más chicos y más seguidos — más combates, cada uno menos decisivo, partidas más largas. Es exactamente el tipo de efecto que un barrido con N=10 puede no alcanzar a separar del ruido de semilla a semilla.

$\beta$ y $S_{min}$, en el mismo barrido con N=40, siguen **sin** mostrar un par de valores con IC95% disjuntos, ni en turno de victoria ni en combates (p.ej. $\beta \in [0, 0.6]$ mueve el turno de victoria medio entre 28.9 y 34.5, con IC que se solapan en todos los pares). Y a diferencia de $\rho_{atk}$, aquí la prueba diseñada específicamente para esto — t de Welch entre pares consecutivos, Bonferroni sobre $\alpha=0.05$ — **confirma** la lectura del IC en vez de contradecirla:

| Parámetro | Métrica | $p$ mínimo entre pares consecutivos | $\alpha$ corregido (Bonferroni, 4 pares) | ¿Significativo? |
|---|---|---|---|---|
| $\beta$ | turno_victoria | 0.091 ($\beta{=}0.0$ vs $0.1$) | 0.0125 | No |
| $\beta$ | combates | 0.391 | 0.0125 | No |
| $S_{min}$ | turno_victoria | 0.333 | 0.0125 | No |
| $S_{min}$ | combates | 0.313 | 0.0125 | No |

Ningún par consecutivo cruza el umbral corregido, así que **con N=40 no se detecta un efecto distinguible de $\beta$ ni de $S_{min}$ en los rangos probados**, y esta vez la afirmación está respaldada por una prueba de hipótesis propiamente dicha, no solo por el solapamiento (más conservador) de intervalos de confianza. Sigue siendo una afirmación más débil que "el sistema es robusto": no descarta que un N aún mayor, o un rango de valores más amplio, revele un efecto pequeño que esta potencia estadística no alcanza a separar del ruido.

**Resumen de método por parámetro** — cada conclusión de esta sección se decidió con una prueba distinta, explícita:

| Parámetro | Conclusión | Decidido por |
|---|---|---|
| $k_c$ | Efecto distinguible, domina el ritmo de partida | IC 95% no solapados entre pares de valores |
| $\rho_{atk}$ | Efecto distinguible (visible solo al subir a N=40) | IC 95% no solapados entre pares de valores |
| $\beta$ | Sin efecto distinguible en el rango probado | t de Welch + Bonferroni entre pares consecutivos (IC ya lo sugería; Welch lo confirma) |
| $S_{min}$ | Sin efecto distinguible en el rango probado | t de Welch + Bonferroni entre pares consecutivos (IC ya lo sugería; Welch lo confirma) |

La variable que un evaluador debería cuestionar primero si el ritmo de partida no se ajusta a lo esperado es $k_c$; en segundo lugar $\rho_{atk}$, cuyo efecto solo se hizo visible al subir la potencia estadística del barrido.

Detalle completo, código, generación de semillas con el GCL propio, tabla ejecutable y la implementación propia (sin scipy) de la t de Welch vía la función beta incompleta regularizada, en `sensibilidad.py`.

---

# 2. Formulación del Modelo Matemático

## 2.1 Dinámica Poblacional (`actualizarDemografia`)

Crecimiento logístico frenado por la capacidad de soporte, **con truncamiento explícito**:

$$
P_{j,t+1} =
\begin{cases}
0 & \text{si } \Omega_{j,t} = \texttt{ABANDONADA} \\[6pt]
\min\!\Big(K_j,\ \big\lfloor P_{j,t} + r\,P_{j,t}\big(1 - \tfrac{P_{j,t}}{K_j}\big) \big\rfloor\Big) & \text{en otro caso}
\end{cases}
\tag{1}
$$

> **Corrección 4.** La v3 enunciaba el truncamiento sólo en prosa (§4). Aquí es parte de la función, como exige el criterio de "funciones por partes" del rubro. Se añade la función piso porque la población se declaró en habitantes (unidad discreta).

Transición de estado de la provincia:

$$
\Omega_{j,t+1} =
\begin{cases}
\texttt{ABANDONADA} & \text{si } P_{j,t+1} = 0 \\
\texttt{POBLADA} & \text{si } P_{j,t+1} > 0
\end{cases}
\tag{1b}
$$

## 2.2 Producción de Oro por Provincia (`calcularProduccionOro`)

$$
R_{j,t} =
\begin{cases}
0 & \text{si } \Omega_{j,t} = \texttt{ABANDONADA} \\
I \cdot P_{j,t} & \text{en otro caso}
\end{cases}
\tag{2}
$$

$$
R^{tot}_{i,t} = \sum_{j\,\in\,\text{provs}(i)} R_{j,t}
\tag{2b}
$$

Nótese que $R_{j,t}$ se evalúa sobre $P_{j,t}$ — la población **del turno $t$**, antes del crecimiento. Este punto es el que el pseudocódigo de la v3 violaba (ver Corrección 7).

## 2.3 Gasto de Mantenimiento Militar (`pagarMantenimiento`)

$$
G_{i,t} = c_m \sum_{j\,\in\,\text{provs}(i)} S_{j,t}
\tag{3}
$$

## 2.4 Actualización del Tesoro

$$
E_{i,t+1} = E_{i,t} + R^{tot}_{i,t} - G_{i,t}
\tag{4}
$$

**Verificación dimensional:** $[\text{oro}] + \frac{\text{oro}}{\text{hab}\cdot\text{turno}}\cdot[\text{hab}]\cdot[\text{turno}] - \frac{\text{oro}}{\text{sold}\cdot\text{turno}}\cdot[\text{sold}]\cdot[\text{turno}] = [\text{oro}]$. ✓

Regla de estado financiero, evaluada al final de `Ev_InicioTurno`:

$$
\Phi_{i,t+1} =
\begin{cases}
\texttt{BANCARROTA} & \text{si } E_{i,t+1} < 0 \\
\texttt{SOLVENTE} & \text{si } E_{i,t+1} \ge 0
\end{cases}
\tag{5}
$$

Regla de actividad del imperio:

$$
\Psi_{i,t+1} =
\begin{cases}
\texttt{False} & \text{si } |\text{provs}(i)| = 0 \\
\texttt{True} & \text{en otro caso}
\end{cases}
\tag{5b}
$$

## 2.5 Modelo de Resolución de Combate (`resolverCombate`)

Fuerza defensiva efectiva:

$$
D^{eff}_{j,t} = S_{j,t}\,(1 + \beta \cdot F_{j,t})
\tag{6}
$$

Probabilidades de impacto (Lanchester estocástico), **con el caso degenerado resuelto**:

$$
(p_A,\ p_D) =
\begin{cases}
(0,\ 0) & \text{si } A_k + D^{eff}_{j,t} = 0 \\[6pt]
\left( k_c \cdot \dfrac{A_k}{A_k + D^{eff}_{j,t}},\ \ k_c \cdot \dfrac{D^{eff}_{j,t}}{A_k + D^{eff}_{j,t}} \right) & \text{en otro caso}
\end{cases}
\tag{7}
$$

> **Corrección 5.** La ec. 8 de la v3 se indeterminaba cuando una fuerza nula atacaba una provincia sin guarnición ($A_k = S_{j,t} = 0$), un caso alcanzable tras una destrucción mutua. Se define el combate nulo: sin combatientes no hay bajas.

Propiedad garantizada: $p_A + p_D = k_c$ siempre que exista al menos un combatiente, y $p_A, p_D \in [0, k_c] \subseteq [0,1]$. Ambas son parámetros válidos de una Binomial.

Bajas simultáneas:

$$
B^{D}_{k,t} \sim \text{Binomial}(S_{j,t},\ p_A), \qquad
B^{A}_{k,t} \sim \text{Binomial}(A_k,\ p_D)
\tag{8}
$$

La simultaneidad es esencial: ambas bajas se calculan sobre los efectivos **previos** al intercambio, de modo que el orden de evaluación no altere el resultado.

Actualización de efectivos:

$$
S_{j,t+1} = \max(0,\ S_{j,t} - B^{D}_{k,t}), \qquad
A'_k = \max(0,\ A_k - B^{A}_{k,t})
\tag{9}
$$

### Resolución por rondas

> **Corrección 14 (detectada en implementación).** Con un único intercambio, la ec. 8 elimina en promedio una fracción $k_c \cdot \frac{D^{eff}}{A_k + D^{eff}} \approx 15\%$ del defensor. La condición $S_{j,t+1} = 0$ de la regla de conquista resulta entonces prácticamente inalcanzable: en la primera corrida completa se observaron **16 combates y 0 conquistas**, con los ejércitos rebotando indefinidamente. El asalto se resuelve por rondas dentro del mismo evento.

Sea $S^{(0)} = S_{j,t}$, $A^{(0)} = A_k$. Para $\rho = 0, 1, \dots, n_{rondas}-1$, mientras $A^{(\rho)} > 0 \wedge S^{(\rho)} > 0$:

$$
\begin{aligned}
D^{eff,(\rho)} &= S^{(\rho)}\,(1 + \beta F_{j,t}) \\
p_A^{(\rho)} &= k_c \cdot \tfrac{A^{(\rho)}}{A^{(\rho)} + D^{eff,(\rho)}}, \qquad
p_D^{(\rho)} = k_c \cdot \tfrac{D^{eff,(\rho)}}{A^{(\rho)} + D^{eff,(\rho)}} \\
S^{(\rho+1)} &= \max\!\big(0,\ S^{(\rho)} - \text{Binomial}(S^{(\rho)}, p_A^{(\rho)})\big) \\
A^{(\rho+1)} &= \max\!\big(0,\ A^{(\rho)} - \text{Binomial}(A^{(\rho)}, p_D^{(\rho)})\big)
\end{aligned}
\tag{9b}
$$

Sean $S^* , A^*$ los efectivos al terminar el bucle, en la ronda $\rho^*$.

### Regla de conquista y destino de los supervivientes

$$
O_{j,t+1} =
\begin{cases}
\text{emisor}(k) & \text{si } S^* = 0 \ \wedge\ A^* > 0 \\
O_{j,t} & \text{en otro caso}
\end{cases}
\tag{10}
$$

$$
\begin{cases}
S_{j,t+1} \leftarrow A^*,\quad F_{j,t+1} \leftarrow 0 & \text{si hay conquista} \\
S_{origen} \leftarrow S_{origen} + A^* & \text{si } A^* > 0 \text{ sin conquista (retirada)} \\
\text{sin efecto} & \text{si } A^* = 0 \text{ (asalto repelido)}
\end{cases}
\tag{10b}
$$

> **Corrección 15 (detectada en implementación).** La v3 sólo definía el caso de conquista y dejaba $A'_k$ **indefinido** en el resto. La implementación literal hacía desaparecer a los supervivientes: una fuga silenciosa que rompe la conservación de efectivos. La ec. 10b cierra el balance: los supervivientes de un asalto no concluyente se retiran a la provincia de origen. Si el origen cambió de dueño durante el viaje, la fuerza se dispersa (y ese caso queda declarado, no implícito).

En conquista, $F_{j,t+1} \leftarrow 0$: las fortificaciones se destruyen en el asalto.

## 2.6 Deserción Forzada (`Ev_CrisisFinanciera`)

Cuando $\Phi_{i,t} = \texttt{BANCARROTA}$, el imperio no puede sostener su ejército. Modelo iterativo con **función piso** y **cota de iteraciones**:

$$
S^{(n+1)}_{j,t} = \left\lfloor S^{(n)}_{j,t}\,(1-\delta) \right\rfloor, \qquad n = 0, 1, \dots, n_{max}^{des}
\tag{11}
$$

con $S^{(0)}_{j,t} = S_{j,t}$. Condición de paro:

$$
\text{detener cuando } \quad
c_m \sum_j S^{(n)}_{j,t} \ \le\ R^{tot}_{i,t}
\quad \vee \quad
\sum_j S^{(n)}_{j,t} = 0
\quad \vee \quad
n = n_{max}^{des}
\tag{12}
$$

Bajas totales por deserción:

$$
\Delta S^{des}_{i,t} = \sum_j \left( S^{(0)}_{j,t} - S^{(n^*)}_{j,t} \right)
\tag{13}
$$

donde $n^*$ es la iteración en que se cumplió (12).

> **Corrección 6.** La ec. 12 de la v3 producía soldados fraccionarios y, sin piso, $S^{(n)} \to 0$ sólo asintóticamente: si $R^{tot}_{i,t} = 0$ el bucle no terminaba nunca. Con $\lfloor \cdot \rfloor$, cada iteración reduce el entero en al menos 1 mientras $S \ge 10$, y por debajo de 10 la multiplicación por 0.9 seguida de piso también decrece estrictamente. La terminación queda garantizada; $n_{max}^{des}$ es una salvaguarda de implementación, no la condición de corte esperada.
>
> **Verificación numérica:** con $S = 1000$, $\delta = 0.1$, $c_m = 0.5$ y $R^{tot} = 400$, converge en **3 iteraciones** a 729 soldados (gasto 364.5 ≤ 400). ✓

---

# 3. Diseño Algorítmico y Lógica de Decisión

## 3.1 Ciclo de Resolución de Fin de Turno (`Ev_InicioTurno`)

```
PROCEDIMIENTO Ev_InicioTurno(t):

  PASO 1 — Snapshot fiscal (antes de cualquier mutación)
    PARA CADA provincia j EN mapaGlobal:
        pob_fiscal[j] ← j.poblacion          # = P_{j,t}, ecuaciones 2 y 4

  PASO 2 — Fase demográfica
    PARA CADA provincia j EN mapaGlobal:
        SI j.estadoProvincia = ABANDONADA ENTONCES
            j.poblacion ← 0
        SINO
            crec ← r · j.poblacion · (1 − j.poblacion / K[j])
            j.poblacion ← min(K[j], floor(j.poblacion + crec))     # ec. 1
        FIN SI
        SI j.poblacion = 0 ENTONCES
            j.estadoProvincia ← ABANDONADA                          # ec. 1b
        FIN SI

  PASO 3 — Recaudación (sobre el snapshot, NO sobre la población nueva)
    PARA CADA imperio i EN listaImperios DONDE i.estadoActivo:
        ingreso[i] ← 0
        PARA CADA provincia j EN provs(i):
            SI j.estadoProvincia ≠ ABANDONADA ENTONCES
                ingreso[i] ← ingreso[i] + I · pob_fiscal[j]          # ec. 2
            FIN SI

  PASO 4 — Mantenimiento militar
    PARA CADA imperio i EN listaImperios DONDE i.estadoActivo:
        gasto[i] ← c_m · Σ_{j ∈ provs(i)} j.tropasEstacionadas       # ec. 3

  PASO 5 — Actualización del tesoro
    PARA CADA imperio i EN listaImperios DONDE i.estadoActivo:
        i.oroDisponible ← i.oroDisponible + ingreso[i] − gasto[i]    # ec. 4

  PASO 6 — Evaluación de estado financiero
    PARA CADA imperio i EN listaImperios DONDE i.estadoActivo:
        SI i.oroDisponible < 0 ENTONCES
            i.estadoFinanciero ← BANCARROTA                          # ec. 5
            LEF.encolar(Ev_CrisisFinanciera, imperio=i, turno=t)
        SINO
            i.estadoFinanciero ← SOLVENTE
        FIN SI

  PASO 7 — Decisiones de la IA
    PARA CADA imperio i EN listaImperios DONDE i.estadoActivo:
        evaluarOpcionesEstocasticas(i, t)                            # §3.2

  PASO 8 — Verificación de actividad
    PARA CADA imperio i EN listaImperios:
        i.estadoActivo ← (|provs(i)| > 0)                            # ec. 5b

  PASO 9 — Auto-reprogramación cíclica
    SI t + 1 ≤ T_max ENTONCES
        LEF.encolar(Ev_InicioTurno, turno = t + 1)
    SINO
        LEF.encolar(Ev_FinSimulacion, turno = t + 1)
    FIN SI
FIN PROCEDIMIENTO
```

> **Corrección 7 (bug funcional).** En la v3, el paso demográfico mutaba `j.poblacion` y el paso de recaudación leía esa misma variable ya actualizada, cobrando impuestos sobre $P_{j,t+1}$ mientras las ecs. 2 y 4 especifican $P_{j,t}$. Con $r = 0.05$ eso sobrestimaba la recaudación hasta un 5% por turno de forma acumulativa. El `PASO 1` congela el valor fiscal antes de cualquier mutación.
>
> **Corrección 8.** La v3 tenía dos pasos numerados "3". La secuencia ahora es 1–9 sin colisiones.

## 3.2 Árbol de Decisión de la IA (`evaluarOpcionesEstocasticas`)

```
PROCEDIMIENTO evaluarOpcionesEstocasticas(imperio i, turno t):

  # --- Regla de override: la bancarrota anula la agresividad ---
  SI i.estadoFinanciero = BANCARROTA ENTONCES
      i.politicaEstrategica ← ECONOMICO
      RETORNAR
  FIN SI

  # --- Tirada de agresividad (consume stream 'decision_ia') ---
  p_agr ← { EXPANSIVO: 0.70, DEFENSIVO: 0.30, ECONOMICO: 0.00 }[i.politicaEstrategica]
  u ← U_decision_ia()
  SI u ≥ p_agr ENTONCES
      RETORNAR                        # este turno no actúa militarmente
  FIN SI

  # --- Reserva mínima: nunca gastar por debajo de un turno de mantenimiento ---
  reserva ← c_m · Σ_{j ∈ provs(i)} j.tropasEstacionadas
  presupuesto ← i.oroDisponible − reserva
  SI presupuesto ≤ 0 ENTONCES
      RETORNAR
  FIN SI

  SEGÚN i.politicaEstrategica:

    CASO EXPANSIVO:
        objetivos ← provincias fronterizas con O[j] ≠ i
        PARA CADA j EN objetivos ORDENADO POR D_eff(j) ASCENDENTE:
            origen ← provincia propia adyacente a j con más tropas
            disponibles ← origen.tropasEstacionadas − S_min
            requerido ← ceil(ρ_atk · D_eff(j))              # ρ_atk = 1.5
            SI disponibles ≥ requerido
               Y presupuesto ≥ c_mov · requerido ENTONCES
                emitirOrden(origen, j, A_k = requerido)     # §3.4
                RETORNAR
            FIN SI
        FIN PARA

    CASO DEFENSIVO:
        débiles ← { j ∈ provs(i) : j.tropasEstacionadas < S_min }
        SI débiles ≠ ∅ ENTONCES
            j* ← argmin_{j ∈ débiles} j.tropasEstacionadas
            faltante ← S_min − j*.tropasEstacionadas
            SI presupuesto ≥ c_mov · faltante ENTONCES
                reclutar(j*, faltante)
                i.oroDisponible ← i.oroDisponible − c_mov · faltante
            FIN SI
        SINO SI presupuesto ≥ c_fort ENTONCES
            j* ← provincia fronteriza propia con menor F[j] y F[j] < F_max
            SI j* existe ENTONCES
                j*.nivelFortificacion ← j*.nivelFortificacion + 1
                i.oroDisponible ← i.oroDisponible − c_fort
            FIN SI
        FIN SI

    CASO ECONOMICO:
        # No emite órdenes militares. Reinvierte en infraestructura.
        # K_j es parámetro estructural: la reinversión se modela como
        # un bono de crecimiento, no como una mutación de K_j.
        RETORNAR
  FIN SEGÚN
FIN PROCEDIMIENTO
```

> **Corrección 13 (detectada en implementación).** La v3 daba capacidad de reclutamiento **únicamente** a la política `DEFENSIVO`. Un imperio `EXPANSIVO` sólo podía atacar con su guarnición inicial, que nunca crece, mientras el umbral $\rho_{atk} \cdot D^{eff}$ del objetivo sí crece con las fortificaciones enemigas. Resultado medido en la primera corrida: **0 ataques en 100 turnos** y 180.000 de oro acumulado sin uso. Es un deadlock estructural, no un problema de parámetros. Se añade la **fase 2 de acumulación**: si ningún objetivo es atacable, el imperio invierte en reclutar hasta alcanzar el umbral. Análogamente, `DEFENSIVO` engrosa guarniciones cuando ya alcanzó $F_{max}$ en toda su frontera.
>
> **Corrección 9.** La v3 decía "ataca si su fuerza supera a $D^{eff}$ y hay oro suficiente" y "refuerza provincias bajo umbral mínimo", sin definir ni la superioridad ni el umbral ni "suficiente". Ahora son $\rho_{atk} = 1.5$, $S_{min} = 50$ y la regla de reserva $\ge c_m \sum S$. Un programador externo puede codificar esto sin consultar al equipo, que es el criterio explícito del enunciado.
>
> **Nota sobre `ECONOMICO`.** La v3 decía "reinvierte el superávit en $K_j$". Como $K_j$ quedó reclasificado a parámetro estructural (Corrección 3), mutarlo rompería la coherencia. La política económica se limita a acumular reservas.

## 3.3 Lógica de la LEF y Reloj de Simulación

```
PROCEDIMIENTO bucleDeSimulacion():
    inicializarEstado()
    LEF.encolar(Ev_InicioTurno, turno = 0)

    MIENTRAS estadoPartida = EN_CURSO Y NO LEF.vacia() HACER:
        evento ← LEF.extraerMinimo()        # menor turno; empates por prioridad
        relojSimulacion ← evento.turno
        procesarEvento(evento)
        evaluarCondicionVictoria()
    FIN MIENTRAS
FIN PROCEDIMIENTO
```

**Regla de desempate** (cuando dos eventos comparten turno), en orden de prioridad descendente:

$$
\texttt{Ev\_CrisisFinanciera} \to \texttt{Ev\_ResolucionCombate} \to \texttt{Ev\_LlegadaOrden} \to \texttt{Ev\_InicioTurno} \to \texttt{Ev\_FinSimulacion}
$$

**Justificación del orden:** la crisis financiera se resuelve primero porque la deserción altera $S_{j,t}$, que es entrada del combate. El combate precede a la llegada de órdenes para que refuerzos que llegan el mismo turno no participen en una batalla ya iniciada. `Ev_InicioTurno` va después porque cierra el turno y reprograma el siguiente.

**Implementación:** la LEF es una cola de prioridad sobre la clave compuesta $(\text{turno},\ \text{prioridad},\ \text{secuencia})$, donde `secuencia` es un contador monótono que garantiza orden FIFO determinista entre eventos idénticos. Sin ese tercer campo, el orden dependería de detalles internos de la estructura de datos y la simulación dejaría de ser reproducible.

## 3.4 Ciclo de Vida de una Orden Militar (`Ev_LlegadaOrden`)

> **Corrección 10.** El abstract prometía formalizar este evento; la v3 no lo desarrollaba en ninguna sección. Aquí se cierra, y con él quedan en uso $\sigma_{k,t}$, $\tau_k$ y $L_k$.

**Emisión** (invocada desde §3.2):

```
PROCEDIMIENTO emitirOrden(origen, destino, A_k):
    k ← nuevaOrdenMilitar()
    k.fuerzaMilitar ← A_k
    k.origen ← origen ; k.destino ← destino ; k.emisor ← O[origen]
    origen.tropasEstacionadas ← origen.tropasEstacionadas − A_k
    emisor.oroDisponible ← emisor.oroDisponible − c_mov · A_k

    k.tiempoViaje  ← τ_k ~ Triangular(a_τ, c_τ, b_τ)        # §6.4
    k.turnoLlegada ← t + k.tiempoViaje                      # L_k
    k.estadoOrden  ← EN_TRANSITO                            # σ_k

    LEF.encolar(Ev_LlegadaOrden, orden=k, turno=k.turnoLlegada)
FIN PROCEDIMIENTO
```

**Llegada:**

```
PROCEDIMIENTO Ev_LlegadaOrden(orden k, turno t):
    SI k.estadoOrden ≠ EN_TRANSITO ENTONCES
        RETORNAR                                # ya resuelta o cancelada
    FIN SI

    # El emisor pudo colapsar mientras la orden viajaba
    SI NO emisor(k).estadoActivo ENTONCES
        k.estadoOrden ← CANCELADA
        RETORNAR
    FIN SI

    j ← k.destino

    SI O[j] = k.emisor ENTONCES
        # Refuerzo: el destino ya es propio (fue conquistado en el ínterin)
        j.tropasEstacionadas ← j.tropasEstacionadas + k.fuerzaMilitar
        k.estadoOrden ← RESUELTA
    SINO
        # Invasión: se agenda el combate en este mismo turno
        k.estadoOrden ← RESUELTA
        LEF.encolar(Ev_ResolucionCombate, orden=k, provincia=j, turno=t)
    FIN SI
FIN PROCEDIMIENTO
```

Las tropas en tránsito **no** pagan mantenimiento (el `PASO 4` de §3.1 sólo suma `tropasEstacionadas`), lo cual es consistente: se descontaron del origen al emitir y se pagó $c_{mov}$ por movilizarlas.

## 3.5 Cierre de la Simulación (`Ev_FinSimulacion`)

```
PROCEDIMIENTO Ev_FinSimulacion(t, causa):
    estadoPartida ← FINALIZADA
    activos ← { i : i.estadoActivo }
    ganador ← activos[0] SI |activos| = 1, SINO ninguno

    # Cierre del ciclo de vida de las órdenes en vuelo
    PARA CADA orden k CON σ_k = EN_TRANSITO:
        σ_k ← CANCELADA

    LEF.purgar()
FIN PROCEDIMIENTO
```

> **Corrección 16 (detectada en implementación).** Purgar la LEF descarta los `Ev_LlegadaOrden` pendientes, dejando sus órdenes con $\sigma_k = $ `EN_TRANSITO` **al cierre de la partida**. El ciclo de vida declarado en §1.1 exige que toda orden termine en `RESUELTA` o `CANCELADA`; un estado no terminal al final es una inconsistencia de la máquina de estados. El bucle de cancelación la cierra.

---

# 4. Condiciones de Frontera y Puntos Críticos

| # | Escenario | Condición | Respuesta del sistema |
|---|-----------|-----------|-----------------------|
| F1 | Saturación poblacional | $P_{j,t} \ge K_j$ | $P$ se trunca en $K_j$ (ec. 1). El término logístico se anula o vuelve negativo; el `min` impide sobrepasar. |
| F2 | Provincia despoblada | $P_{j,t} = 0$ | $\Omega_j \leftarrow$ `ABANDONADA` (ec. 1b). No genera oro, pero conserva $S_j$ y $F_j$: puede seguir defendiéndose. |
| F3 | Déficit económico | $E_{i,t} < 0$ | `BANCARROTA` (ec. 5) → `Ev_CrisisFinanciera` → deserción (ec. 11) hasta equilibrar o quedar sin tropas. |
| F4 | Deserción sin ingresos | $R^{tot}_{i,t} = 0$ | El piso de la ec. 11 lleva $S \to 0$ en un número finito de pasos. Verificado: no hay bucle infinito. |
| F5 | Combate degenerado | $A_k + D^{eff}_{j,t} = 0$ | $p_A = p_D = 0$ (ec. 7). No se invoca la Binomial. Sin bajas, sin conquista. |
| F6 | Destrucción mutua | $S_{j,t+1} = 0 \wedge A'_k = 0$ | La soberanía se mantiene: $O_{j,t+1} = O_{j,t}$ (ec. 10). La provincia queda indefensa pero no cambia de dueño. |
| F7 | Imperio sin territorios | $\lvert\text{provs}(i)\rvert = 0$ | $\Psi_i \leftarrow$ `False` (ec. 5b). Se excluye de todos los bucles de `Ev_InicioTurno`. |
| F8 | Orden huérfana | Emisor inactivo al llegar $L_k$ | $\sigma_k \leftarrow$ `CANCELADA`. Las tropas se pierden (§3.4). |
| F9 | Fortificación máxima | $F_{j,t} = F_{max}$ | La IA `DEFENSIVA` no puede invertir más en esa provincia. |
| F10 | Condición de parada | $t \ge T_{max}$, o un solo imperio activo | `Ev_FinSimulacion`. |

**Invariantes que deben cumplirse en todo instante** (útiles como aserciones en la implementación):

$$
\begin{aligned}
&0 \le P_{j,t} \le K_j &&\forall j, t \\
&0 \le F_{j,t} \le F_{max} &&\forall j, t \\
&S_{j,t} \ge 0 \ \wedge\ S_{j,t} \in \mathbb{Z} &&\forall j, t \\
&p_A, p_D \in [0,\ k_c] &&\forall \text{ combate} \\
&\textstyle\sum_i |\text{provs}(i)| = |\text{mapaGlobal}| &&\forall t
\end{aligned}
$$

---

# 5. Trazabilidad (Coherencia Sistémica)

Auditoría **exhaustiva**: cada símbolo declarado en la Sección 1 se rastrea hasta su punto de uso. Un símbolo sin uso es un error de diseño, no un detalle cosmético.

| Símbolo | Declarado | Usado en | Estado |
|---------|-----------|----------|--------|
| $t$ | 1.1 | ecs. 1–13, §3.1, §3.3, §3.4 | ✓ |
| $E_{i,t}$ | 1.1 | ecs. 4, 5; §3.1 P5–P6; §3.2 | ✓ |
| $\Phi_{i,t}$ | 1.1 | ec. 5; §3.1 P6; §3.2 override | ✓ |
| $\Psi_{i,t}$ | 1.1 | ec. 5b; §3.1 P8; §3.4; F7 | ✓ *(nuevo)* |
| $P_{j,t}$ | 1.1 | ecs. 1, 1b, 2; §3.1 P1–P3 | ✓ |
| $S_{j,t}$ | 1.1 | ecs. 3, 6, 8, 9, 11; §3.2; §3.4 | ✓ |
| $F_{j,t}$ | 1.1 | ec. 6; §3.2 `DEFENSIVO`; F9 | ✓ |
| $O_{j,t}$ | 1.1 | ec. 10; §3.2; §3.4 | ✓ |
| $\Omega_{j,t}$ | 1.1 | ecs. 1, 1b, 2; §3.1 P2–P3; F2 | ✓ *(nuevo)* |
| $\sigma_{k,t}$ | 1.1 | §3.4 (emisión, llegada, cancelación); F8 | ✓ *(era huérfano)* |
| $\dot{P}_{j,t}$ | 1.2 | ec. 1 (término $r P(1-P/K)$) | ✓ |
| $R_{j,t}$, $R^{tot}_{i,t}$ | 1.2 | ecs. 2, 2b, 4, 12; §3.1 P3 | ✓ |
| $G_{i,t}$ | 1.2 | ecs. 3, 4; §3.1 P4 | ✓ |
| $B^{A}_{k,t}$, $B^{D}_{k,t}$ | 1.2 | ecs. 8, 9; §6.4 | ✓ |
| $\Delta S^{des}_{i,t}$ | 1.2 | ec. 13 | ✓ *(antes no aparecía en su fórmula)* |
| $\pi_i$ | 1.3 | §3.2 (selecciona rama y $p_{agr}$) | ✓ |
| $\tau_k$ | 1.3 | §3.4 emisión; §6.4 | ✓ *(era huérfano)* |
| $L_k$ | 1.3 | §3.4 emisión y encolado | ✓ *(era huérfano)* |
| $A_k$ | 1.3 | ecs. 7–10; §3.2; §3.4 | ✓ |
| $D^{eff}_{j,t}$ | 1.3 | ecs. 6, 7; §3.2 | ✓ |
| Parámetros §1.4 | 1.4 | Todos referenciados en ecs. o pseudocódigo | ✓ |

**Símbolos usados sin declarar: ninguno.** (En la v3 eran `estadoActivo` y `estadoProvincia`.)
**Símbolos declarados sin usar: ninguno.** (En la v3 eran $\sigma_{k,t}$, $L_k$ y $\Delta S^{des}_{i,t}$.)

---

# 6. Motor de Aleatoriedad y Generación de Variables

Esta sección es nueva. Sin ella, las ecs. 8 y §3.4 no son implementables: declaran distribuciones pero no cómo obtener muestras de ellas.

## 6.1 Requisitos

1. **Reproducibilidad.** Una misma semilla debe producir una partida idéntica. Sin esto no se pueden depurar ni validar los resultados.
2. **Independencia entre subsistemas.** El combate, las decisiones de la IA y los tiempos de viaje son independientes por diseño; la implementación no debe introducir correlación entre ellos.
3. **Periodo suficiente.** Una partida de $T_{max} = 500$ turnos con múltiples imperios y combates consume del orden de $10^6$–$10^7$ variables aleatorias.

## 6.2 Generador de números pseudoaleatorios

### 6.2.1 Generador Congruencial Lineal (referencia)

$$x_n = (a\,x_{n-1} + b) \bmod m$$

Con $m = 2^{31}$, $a = 1103515245$, $b = 12345$. Se cumplen las condiciones de Hull–Dobell para periodo completo:

| Condición | Verificación |
|-----------|--------------|
| $\gcd(b, m) = 1$ | $b$ impar y $m = 2^k$ → único primo de $m$ es 2 → ✓ |
| $(a-1)$ divisible por todo primo de $m$ | $a - 1 = 1103515244$ es par → ✓ |
| $(a-1)$ divisible por 4, pues $4 \mid m$ | $a = 4c+1$ con $c = 275878811$ → ✓ |

Comprobación empírica con $m = 16,\ a = 5,\ b = 1$: periodo observado **16 de 16**. ✓

### 6.2.2 Hallazgo: por qué el GCL no basta para este modelo

Un GCL admite salto adelante en forma cerrada, lo que lo hace atractivo para partir el periodo en streams disjuntos. Pero si dos streams se separan por un salto fijo $k$, entonces **para todo $i$**:

$$x^{(2)}_i = A_k \cdot x^{(1)}_i + B_k \pmod m$$

es decir, el $i$-ésimo valor de un stream determina exactamente el $i$-ésimo del otro. **Verificado: 500 de 500 pares cumplen la relación.**

En el combate (ec. 8), las bajas del atacante y del defensor se generan en paralelo dentro del mismo evento, un ensayo Bernoulli por soldado de cada bando: es decir, **en lockstep**. Con streams de GCL, la suerte de un bando quedaría determinada por la del otro.

Lo grave es que **los contrastes empíricos no detectan este defecto**:

| Prueba sobre los dos streams del GCL | Resultado | ¿Detecta? |
|--------------------------------------|-----------|-----------|
| Batería completa sobre stream 1 | Aceptado | ✗ |
| Batería completa sobre stream 2 | Aceptado | ✗ |
| Correlación de Pearson entre pares alineados | 0.014 | ✗ |
| Corridas sobre las secuencias intercaladas | $Z = -0.198$ | ✗ |

La aritmética modular destruye la correlación lineal, de modo que una dependencia **determinista y total** pasa desapercibida. Esto confirma en la práctica el principio de la Unidad III: *ninguna batería de pruebas empíricas es suficiente para certificar un generador*; el análisis estructural es indispensable.

### 6.2.3 Generador combinado (motor de producción)

$$
\begin{aligned}
x^{(1)}_n &= 40014 \cdot x^{(1)}_{n-1} \bmod 2147483563 \\
x^{(2)}_n &= 40692 \cdot x^{(2)}_{n-1} \bmod 2147483399 \\
z_n &= \left(x^{(1)}_n - x^{(2)}_n\right) \bmod (m_1 - 1) \\
u_n &= z_n / m_1 \quad (\text{con } z_n = 0 \mapsto (m_1-1)/m_1)
\end{aligned}
\tag{14}
$$

Dos generadores multiplicativos de módulo primo combinados por resta. Rompe la relación afín porque un mapa afín en cada componente **no** produce un mapa afín en la diferencia cuando los módulos son distintos.

| Propiedad | GCL simple | Combinado |
|-----------|-----------|-----------|
| Periodo | $2.1 \times 10^9$ | $2.3 \times 10^{18}$ |
| Streams en lockstep | Deterministas entre sí | Independientes |
| Semilla nula | Admisible ($b \ne 0$) | Prohibida (punto fijo absorbente) |

El periodo importa: la transcripción del curso advierte que un ciclo corto puede agotarse durante la simulación y repetirse, invalidando los resultados. Con $2.3\times10^{18}$ el margen es holgado.

### 6.2.4 Política de semillas

Siguiendo las recomendaciones de la Unidad III:

- **No usar cero.** En un generador multiplicativo, $x = 0$ es punto fijo absorbente. El constructor lo rechaza.
- **No usar valores pares** para la semilla maestra.
- **No usar semillas aleatorias** (reloj del sistema): impiden reproducir la corrida y no garantizan que los streams no se solapen.
- **Reusar la semilla** en réplicas para comparación controlada.

## 6.3 Partición en streams

Cada fuente de aleatoriedad recibe un bloque disjunto del periodo, obtenido por salto de $2^{40}$ posiciones (el salto en un generador multiplicativo es $a^k \bmod m$, calculable en tiempo logarítmico).

| Stream | Consumido por | Variable generada |
|--------|---------------|-------------------|
| `combate_atacante` | `Ev_ResolucionCombate` | $B^{D}_{k,t} \sim \text{Binomial}(S_{j,t}, p_A)$ |
| `combate_defensor` | `Ev_ResolucionCombate` | $B^{A}_{k,t} \sim \text{Binomial}(A_k, p_D)$ |
| `decision_ia` | `evaluarOpcionesEstocasticas` | $u \sim U(0,1)$ para la tirada de agresividad |
| `tiempo_viaje` | `emitirOrden` | $\tau_k \sim \text{Triangular}(a_\tau, c_\tau, b_\tau)$ |
| `desercion` | `Ev_CrisisFinanciera` | (reservado; el modelo actual es determinista) |

## 6.4 Generación de variables aleatorias

Todo algoritmo sigue el mismo enfoque general: generar uno o más $U(0,1)$, aplicar una transformación que depende de la distribución, retornar el valor.

**Binomial$(n, p)$ — bajas de combate.** Suma de $n$ ensayos Bernoulli independientes: cada soldado es un ensayo que "cae" con probabilidad $p$. Consume $n$ números aleatorios. Se prefiere a la transformada inversa porque la correspondencia soldado↔ensayo hace el modelo auditable en la defensa del proyecto.

**Triangular$(a, c, b)$ — tiempo de viaje.** Por transformada inversa:

$$
\tau =
\begin{cases}
a + \sqrt{u\,(b-a)(c-a)} & \text{si } u < \frac{c-a}{b-a} \\[6pt]
b - \sqrt{(1-u)(b-a)(b-c)} & \text{en otro caso}
\end{cases}
\tag{15}
$$

seguida de redondeo a entero $\ge 1$, porque $\tau_k$ se mide en turnos. **Justificación de la familia:** no existen datos históricos del sistema; la Unidad IV prescribe exactamente el enfoque triangular cuando sólo pueden estimarse subjetivamente el mínimo, la moda y el máximo. Esto sustituye el valor mágico que la v3 dejaba sin especificar.

## 6.5 Validación empírica del generador

Batería sobre $n = 10\,000$ valores, $\alpha = 0.05$:

| Prueba | Propiedad | Estadístico | Crítico | Decisión |
|--------|-----------|-------------|---------|----------|
| Corridas arriba-abajo | **Independencia** | $Z = -0.7195$ | $\pm 1.96$ | No rechaza $H_0$ ✓ |
| Chi-cuadrado ($k=10$ equiprobables, $gl = 9$) | **Uniformidad** | $\chi^2 = 12.008$ | 16.919 | No rechaza $H_0$ ✓ |
| Kolmogorov–Smirnov | **Uniformidad** | $D_n = 0.01046$ | 0.0136 | No rechaza $H_0$ ✓ |

Los cinco streams superan la batería completa de forma individual. Independencia cruzada entre los dos streams de combate, evaluada en el escenario de consumo en lockstep: $Z = 0.7452$ (no rechaza $H_0$), correlación de Pearson $= 0.015$, cero valores en común.

**Precisión de la generación** (1000 réplicas, $A_k = 800$, $S_{j,t} = 500$, $F_{j,t} = 2$, $\beta = 0.25$, $k_c = 0.3$):

| Variable | Media simulada | Media teórica | Error |
|----------|----------------|---------------|-------|
| $B^{D}$ (bajas defensor) | 77.26 | $S \cdot p_A = 77.42$ | 0.20% |
| $B^{A}$ (bajas atacante) | 116.03 | $A_k \cdot p_D = 116.13$ | 0.09% |
| $\tau_k$ | 2.664 | $(a+c+b)/3 = 2.667$ | 0.11% |

**Nota metodológica.** No rechazar $H_0$ **no demuestra** que la secuencia sea uniforme e independiente; sólo indica que estas pruebas no detectaron desviaciones a este tamaño de muestra. §6.2.2 es un ejemplo concreto de lo que la batería puede dejar pasar.

## 6.6 Trazabilidad de aleatoriedad

| Evento | Variable | Distribución | Stream | Método de generación |
|--------|----------|--------------|--------|----------------------|
| `Ev_ResolucionCombate` | $B^{D}_{k,t}$ | $\text{Binomial}(S_{j,t}, p_A)$ | `combate_atacante` | Bernoulli acumulado |
| `Ev_ResolucionCombate` | $B^{A}_{k,t}$ | $\text{Binomial}(A_k, p_D)$ | `combate_defensor` | Bernoulli acumulado |
| `emitirOrden` | $\tau_k$ | $\text{Triangular}(1, 2, 5)$ | `tiempo_viaje` | Transformada inversa (ec. 15) |
| `evaluarOpcionesEstocasticas` | $u$ | $U(0,1)$ | `decision_ia` | Directo del generador |
| `Ev_CrisisFinanciera` | $\Delta S^{des}_{i,t}$ | — (determinista) | `desercion` (reservado) | Recurrencia ec. 11 |

---

# 7. Estado de Implementación

| Módulo | Contenido | Secciones | Estado |
|--------|-----------|-----------|--------|
| `rng.py` | GCL, generador combinado, banco de streams | §6.2, §6.3 | Validado |
| `pruebas.py` | Corridas, Chi-cuadrado, K-S con valores críticos tabulados | §6.5 | Validado |
| `variables.py` | Bernoulli, Binomial, Triangular, Exponencial, Uniforme discreta | §6.4 | Validado |
| `entidades.py` | Partida, Imperio, Provincia, OrdenMilitar, Mapa, Parámetros | §1 | Validado |
| `lef.py` | Cola de prioridad con desempate `(turno, prioridad, secuencia)` | §3.3 | Validado |
| `eventos.py` | Los cinco eventos + `evaluarOpcionesEstocasticas` | §2, §3 | Validado |
| `simulacion.py` | Bucle principal, verificador de invariantes, escenario | §3.3, §4 | Validado |
| `validar.py` | Batería del generador; reproduce las tablas de §6.5 | §6 | Ejecutable |
| `test_modelo.py` | Verifica las fronteras F1–F10 sobre corridas reales | §4 | Ejecutable |

Sin dependencias externas: sólo biblioteca estándar de Python.

## 7.1 Resultados de verificación

Barrido de 7 semillas (3, 7, 11, 101, 999, 12345, 60013), $T_{max} = 200$:

| Verificación | Resultado |
|--------------|-----------|
| Violaciones de invariantes I1–I6 | **0** en todas las corridas |
| Reloj monótono (nunca retrocede) | ✓ en todas |
| LEF completamente drenada | ✓ en todas |
| Corridas que terminan sin abortar | 7 de 7 |
| Misma semilla → corrida idéntica | ✓ |
| Distinta semilla → corrida distinta | ✓ |

Condiciones de frontera verificadas sobre escenarios construidos a propósito: F1 (saturación), F2 (provincia despoblada conserva tropas y fortificación), F4 (deserción con ingreso cero converge a 0 sin bucle infinito), F5 (combate degenerado sin división por cero), F6 (asaltos repelidos observados), F8 (orden huérfana cancelada), F9 ($F \le F_{max}$), F10 (parada respetada). **Las 21 verificaciones pasan.**

Conservación de efectivos: los supervivientes de asaltos no concluyentes se retiran al origen (ec. 10b), no quedan órdenes en estado no terminal al cierre, y ninguna provincia registra tropas negativas.

## 7.2 Nota metodológica sobre las Correcciones 13–16

Las correcciones 1–12 salieron de una revisión del documento. Las **13, 14, 15 y 16 sólo aparecieron al ejecutar el modelo**: un deadlock de la IA expansiva, una condición de conquista inalcanzable, una fuga silenciosa de soldados y un estado no terminal al cierre. Ninguna es detectable leyendo las ecuaciones, porque todas son consistentes en el papel; lo que falla es el comportamiento agregado en el tiempo.

Esto ilustra el punto del enunciado del parcial: un documento es programable cuando un tercero puede codificarlo sin consultar al equipo. El recíproco también se cumple — sólo al codificarlo se descubre qué quedó sin especificar.
