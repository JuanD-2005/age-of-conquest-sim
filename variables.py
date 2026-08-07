"""
Generacion de variables aleatorias a partir de los U(0,1) del GCL propio.

Enfoque general de todo algoritmo de generacion de v.a. (Unidad III):
    1. Generar uno o mas numeros aleatorios U(0,1)
    2. Aplicar una transformacion que depende de la distribucion
    3. Retornar el valor de la variable aleatoria

Aqui se implementan solo las distribuciones que el modelo de Age of Conquest
declara explicitamente, ninguna de adorno.
"""

import math


def bernoulli(gen, p):
    """Ensayo Bernoulli(p) por comparacion directa. Consume 1 U(0,1)."""
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"p fuera de [0,1]: {p}")
    return 1 if gen.u() < p else 0


def binomial(gen, n, p):
    """Binomial(n, p) como suma de n ensayos Bernoulli independientes.

    Usada para las bajas de combate: B^D ~ Binomial(S, pA).
    Interpretacion fisica directa: cada soldado es un ensayo independiente
    que "cae" con probabilidad p. Consume n numeros aleatorios.

    Se elige este metodo sobre la transformada inversa porque n (tropas en
    una provincia) es moderado y la equivalencia soldado-ensayo hace el
    modelo auditable en la defensa del proyecto.
    """
    if n < 0:
        raise ValueError(f"n negativo: {n}")
    if n == 0 or p <= 0.0:
        return 0
    if p >= 1.0:
        return n
    return sum(bernoulli(gen, p) for _ in range(n))


def triangular(gen, a, c, b):
    """Triangular(a, c, b) por transformada inversa. a=min, c=moda, b=max.

    Se usa para tau_k (tiempo de viaje de una orden militar), porque no
    existen datos historicos del sistema: la Unidad IV prescribe justamente
    el enfoque triangular cuando solo se pueden estimar subjetivamente el
    minimo, la moda y el maximo.

    F(x) = (x-a)^2 / ((b-a)(c-a))        si a <= x <= c
    F(x) = 1 - (b-x)^2 / ((b-a)(b-c))    si c <  x <= b
    """
    if not a <= c <= b:
        raise ValueError(f"se requiere a <= c <= b, recibido ({a}, {c}, {b})")
    if a == b:
        return a
    u = gen.u()
    punto_quiebre = (c - a) / (b - a)
    if u < punto_quiebre:
        return a + math.sqrt(u * (b - a) * (c - a))
    return b - math.sqrt((1 - u) * (b - a) * (b - c))


def triangular_entero(gen, a, c, b):
    """Version discreta de triangular para tau_k, que se mide en turnos."""
    return max(1, int(round(triangular(gen, a, c, b))))


def exponencial(gen, media):
    """Exponencial(media) por transformada inversa: x = -media * ln(1-u).

    No la usa el modelo actual, pero queda disponible por si se decide
    modelar tiempos entre eventos a tasa constante en Parcial III.
    """
    if media <= 0:
        raise ValueError(f"media debe ser positiva: {media}")
    return -media * math.log(1.0 - gen.u())


def uniforme_discreta(gen, i, j):
    """UD(i, j) inclusiva. Util para desempates y seleccion de objetivos."""
    if i > j:
        raise ValueError(f"se requiere i <= j, recibido ({i}, {j})")
    return i + int(gen.u() * (j - i + 1))
