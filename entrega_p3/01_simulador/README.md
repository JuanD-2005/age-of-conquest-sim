# 01 — Simulador: interfaz de consola

**Responsable: Juan**
**Entregable: `main.py` en la raíz del repo**

---

## Qué pide el enunciado, literal

> "Un programa funcional... Debe permitir la **interacción básica** (por
> consola o una interfaz gráfica mínima) para ejecutar **al menos cinco (5)
> fases consecutivas** del juego."

> "...el objetivo es construir el 'motor lógico' (back-end) donde se puedan
> **ingresar variables de entrada** o simular (ej. **número de tropas, nivel
> de impuestos**) y el sistema calcule correctamente el estado del siguiente
> turno."

Este es el único requisito **obligatorio** del enunciado que el código
actual no cumple. Sin esto no hay demostración en vivo, y la demo es parte
de los 30 puntos de defensa.

---

## Estado actual

Hoy la única forma de correr el modelo es desde Python:

```python
from simulacion import correr
partida, streams, stats = correr(semilla=7, turnos_max=200)
```

No hay ningún `input()`, `argparse` ni `if __name__ == "__main__"` en todo
el repo (verificado). En la defensa hay que **compartir pantalla y ejecutar
en vivo** — no se puede hacer eso escribiendo imports en un REPL.

---

## Qué construir

Un menú de consola, **stdlib-only** (sin librerías externas), con:

### 1. Configurar escenario
Antes de arrancar la partida, poder ajustar:
- Número de imperios y provincias por imperio
- Tropas iniciales por provincia
- Oro inicial por imperio
- **Tasa impositiva (`I`)** — el enunciado menciona "nivel de impuestos"
  explícitamente, tiene que ser ajustable
- Semilla maestra (validando impar y no nula, como exige `rng.py`)

Todos con valores por defecto que coincidan con `construir_escenario()`,
para poder arrancar dando Enter a todo.

### 2. Ejecutar turno a turno
- Avanzar 1 turno
- Avanzar N turnos
- Correr hasta el final

Tras cada avance, mostrar el estado legible: por imperio (oro, provincias,
tropas totales, política, estado financiero) y los eventos de ese turno
(están en `partida.bitacora`).

### 3. Inspeccionar estado
- Detalle de una provincia (población, tropas, fortificación, dueño)
- Órdenes militares en tránsito
- Estado de la LEF (cuántos eventos encolados, de qué tipo)

### 4. Salir

---

## Restricciones importantes

- **No dupliques lógica.** `main.py` importa y usa lo que ya existe. Si
  necesitas ejecutar un evento a la vez en vez del bucle completo, extrae
  eso de `bucle_de_simulacion()` en una función reutilizable — no
  copies-pegues el cuerpo del bucle.
- **Manejo de errores.** Si alguien mete una semilla par, letras donde va
  un número, o un valor absurdo: avisar y volver a preguntar, nunca un
  traceback. En la defensa alguien va a teclear mal, garantizado.
- **Salida legible sin librerías externas**: f-strings con ancho fijo.
- Comentarios en español, mismo estilo del resto del proyecto.

---

## Cómo verificar que está listo

Antes de commitear, comprobar tú mismo:

- [ ] Corre `main.py` y ejecuta 5 turnos consecutivos con valores por
      defecto, sin errores
- [ ] Repite con parámetros distintos (más tropas, otra tasa impositiva) y
      el estado cambia coherentemente
- [ ] Mete entradas inválidas a propósito (semilla par, letras) y no truena
- [ ] `python3 test_modelo.py` sigue verde
- [ ] `python3 validar.py` sigue verde

---

## Para la defensa

Vas a ser quien maneje el teclado en la demo. Prepárate para responder:
- ¿Por qué el menú permite avanzar turno a turno y no solo correr todo?
- ¿Qué pasa si subo la tasa impositiva al máximo? (El enunciado menciona
  "impuestos al máximo" como caso borde en el punto de Análisis de Casos
  Borde — vale la pena probarlo antes.)
