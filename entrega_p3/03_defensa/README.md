# 03 — Validación y Defensa Oral

**Responsable: Gustavo**
**Entregables:**
- `estrategia_validacion.md` en esta carpeta (insumo para el informe de María)
- `escenarios_demo.py` en esta carpeta (semillas verificadas para la sesión en vivo)
- `DEFENSA.md` en esta carpeta, actualizado

**La defensa vale 30 de los 60 puntos del parcial.**

---

## Qué pide el enunciado, literal

> "**Demostración en Vivo**: Los estudiantes compartirán pantalla para
> ejecutar su simulador en vivo."
> "**Sustentación Técnica**: Defensa del código y las decisiones de diseño."

Y sobre validación:

> "Pueden presentar tablas o gráficas comparativas que demuestren que los
> resultados arrojados por su simulador **coinciden con los resultados del
> juego real Age of Conquest** bajo las mismas condiciones iniciales."

---

## Tarea 1 — La estrategia de validación (la parte delicada)

### El problema

El enunciado pide validación **contra el juego real**. Nosotros validamos
el modelo **contra sí mismo**: invariantes formales, 31 verificaciones de
fronteras, contrastes estadísticos sobre el generador, análisis de
sensibilidad y de réplicas. Eso es validación **interna**, y es rigurosa —
pero no es lo mismo que comparar contra Age of Conquest.

De hecho, §1.5 del `v4.md` dice explícitamente que no existen datos reales
de partidas del juego, y por eso los parámetros son "valores de referencia
razonados", no calibrados.

### Lo que NO hay que hacer

No afirmar "nuestro simulador replica con alta fidelidad Age of Conquest".
Sería falso y no lo podemos sostener. Si el evaluador pregunta "¿contra qué
lo compararon?" y no hay respuesta, es peor que haberlo dicho de frente.

No inventar una tabla comparativa con números del juego que nadie midió.

### Lo que sí hay que hacer

Nota que el enunciado dice **"pueden presentar"**, no "deben". Hay margen
para argumentar. La estrategia:

1. **Ser explícito sobre qué tipo de validación se hizo.** Verificación de
   consistencia interna, no calibración empírica externa. Nombrarlo bien
   ya demuestra que se entiende la diferencia — que es contenido del curso.
2. **Presentar la evidencia que sí existe, que es mucha:**
   - 31 verificaciones automáticas de fronteras e invariantes, 0 fallos
   - Batería estadística sobre el generador (corridas, chi-cuadrado, K-S)
   - Reproducibilidad: misma semilla → misma partida
   - Análisis de sensibilidad con IC 95% y t de Welch + Bonferroni
   - Análisis de réplicas (N=40) con intervalos de confianza
3. **Explicar por qué la calibración externa no era viable** y qué haría
   falta para hacerla (acceso a partidas instrumentadas del juego).

### Plan salvavidas (solo si hace falta)

Si el evaluador presiona mucho en este punto, el grupo puede jugar unas
partidas de Age of Conquest y anotar datos básicos (población inicial,
oro por turno, resultado de un combate con fuerzas conocidas) para una
comparación mínima. **No lo hagas por defecto** — es trabajo costoso y
probablemente innecesario. Tenlo como carta bajo la manga y menciónalo en
la defensa como "línea de trabajo futura" si sale el tema.

---

## Tarea 2 — Escenarios verificados para la demo

**Entregable: `escenarios_demo.py`** — un script, no un libreto en markdown.

La idea es que la demo no dependa de improvisar ni de recordar qué semilla
servía: el script contiene semillas **ya probadas contra `main.py`** (cuando
Juan lo termine) que producen resultados demostrables en pocos turnos —
conquista, bancarrota, deserción, un asalto repelido. Cada escenario va con
un comentario que dice qué se supone que ocurre y en qué turno, para poder
verificar de antemano que sigue reproduciéndose. Las semillas deben ser
impares y no nulas (§6.2.4).

Una semilla que "más o menos servía" no sirve: si el evaluador pide correrlo
otra vez, tiene que dar exactamente lo mismo. Esa es la ventaja de tener la
reproducibilidad garantizada — conviene aprovecharla y decirlo en voz alta
durante la demo.

### Lo que antes iba a ser un guion aparte, ahora vive aquí

Estos puntos siguen siendo necesarios, pero son prosa de este README, no un
archivo adicional que mantener:

**Orden de la demo (5–10 minutos).** Definir qué se muestra y en qué
secuencia, y no improvisar frente al evaluador. Arrancar por una corrida
corta que termine en conquista deja ver el motor completo funcionando antes
de entrar en detalles.

**Qué caso borde mostrar en vivo.** La bancarrota es la mejor candidata: es
visual, rápida, y encadena con la deserción (ec. 11), que es una de las
correcciones que mejor se defienden.

**Plan B si algo falla en vivo.** Tener capturas o una corrida grabada
lista. Si el simulador no arranca en la máquina de quien comparte pantalla,
el plan B se ejecuta sin pausas incómodas.

**Quién habla en cada momento.** Los tres deben intervenir; lo natural es
que cada uno hable de los módulos que le tocan en el reparto de más abajo.

---

## Tarea 3 — Actualizar `DEFENSA.md`

El `DEFENSA.md` actual se escribió antes de saber que la defensa era real
y estructurada. Ahora que sabemos que hay demo en vivo + sustentación
técnica, actualizarlo con:

- Las preguntas probables y quién responde cada una
- Los 4 hallazgos de implementación (Correcciones 13–16) — es el argumento
  más fuerte que tenemos, hay que saber contarlo en 60 segundos
- El hallazgo de §6.2.2 (los streams del GCL pasan todas las pruebas
  empíricas siendo deterministas entre sí) — demostración propia de por
  qué una sola prueba no basta
- Preguntas incómodas y su respuesta honesta:
  - "¿Contra qué validaron?" → ver Tarea 1
  - "¿Por qué no hay moral?" → §1.4, nota de coherencia
  - "¿Por qué 0.3 y no 0.5 para k_c?" → §1.5, análisis de sensibilidad
  - "¿Quién escribió esta parte?" → cada uno debe conocer su módulo

---

## Reparto de módulos para la sustentación técnica

Para que cada uno pueda defender lo suyo sin titubear:

| Persona | Módulos que domina |
|---|---|
| Juan | `main.py`, `simulacion.py` |
| María | `entidades.py`, `lef.py` |
| Gustavo | `eventos.py`, `rng.py`, `pruebas.py`, `variables.py` |

Lee tus módulos a fondo antes de la defensa. Especialmente `eventos.py`:
ahí están la resolución de combate por rondas (Corrección 14) y la regla
de retirada (Corrección 15), que son las decisiones de diseño más
interesantes del proyecto.
