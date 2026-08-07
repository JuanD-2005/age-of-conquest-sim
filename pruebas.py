"""
Contrastes empiricos para validar el generador (Unidad III / IV).

Antes de conectar el generador al motor de simulacion hay que demostrar dos
propiedades sobre la secuencia U(0,1) producida:

  - INDEPENDENCIA  -> prueba de corridas (runs test)
  - UNIFORMIDAD    -> chi-cuadrado y Kolmogorov-Smirnov

Nota conceptual importante (sale en el quiz): la prueba de corridas NO mide
uniformidad, mide independencia/aleatoriedad. Y una sola prueba nunca es
suficiente para declarar bueno un generador: por eso se corren las tres.

Valores criticos tabulados -> sin dependencias externas.
"""

import math

# chi-cuadrado, alfa = 0.05, cola derecha, por grados de libertad
CHI2_CRIT_005 = {
    1: 3.841, 2: 5.991, 3: 7.815, 4: 9.488, 5: 11.070, 6: 12.592,
    7: 14.067, 8: 15.507, 9: 16.919, 10: 18.307, 11: 19.675, 12: 21.026,
    13: 22.362, 14: 23.685, 15: 24.996, 16: 26.296, 17: 27.587, 18: 28.869,
    19: 30.144, 20: 31.410, 24: 36.415, 29: 42.557, 39: 54.572, 49: 66.339,
}

Z_CRIT_005 = 1.96          # normal estandar, dos colas
KS_COEF_005 = 1.36         # d_{n,0.95} ~ 1.36/sqrt(n) para n grande


# ---------------------------------------------------------------------------
# Independencia
# ---------------------------------------------------------------------------

def prueba_corridas(u):
    """Corridas arriba-abajo. H0: la secuencia es independiente.

    Se compara cada valor con el anterior y se cuenta cuantas veces cambia
    el sentido de la racha. Bajo independencia:
        E[corridas]   = (2n - 1) / 3
        Var[corridas] = (16n - 29) / 90
    y Z = (corridas - E) / sqrt(Var) ~ N(0,1).
    """
    n = len(u)
    if n < 3:
        raise ValueError("se requieren al menos 3 observaciones")

    corridas = 1
    signo_previo = None
    for i in range(1, n):
        if u[i] == u[i - 1]:
            continue
        signo = u[i] > u[i - 1]
        if signo_previo is not None and signo != signo_previo:
            corridas += 1
        signo_previo = signo

    esperado = (2 * n - 1) / 3
    varianza = (16 * n - 29) / 90
    z = (corridas - esperado) / math.sqrt(varianza)

    return {
        "prueba": "Corridas arriba-abajo (independencia)",
        "n": n,
        "corridas_observadas": corridas,
        "corridas_esperadas": round(esperado, 2),
        "Z": round(z, 4),
        "Z_critico": Z_CRIT_005,
        "rechaza_H0": abs(z) > Z_CRIT_005,
    }


# ---------------------------------------------------------------------------
# Uniformidad
# ---------------------------------------------------------------------------

def prueba_chi_cuadrado(u, k=10, m_parametros_estimados=0):
    """Chi-cuadrado con k intervalos equiprobables sobre [0,1].

    H0: los U_i provienen de una U(0,1).
    Intervalos equiprobables -> E_j = n/k para todo j (recomendacion de la
    Unidad IV: preferir equiprobables y mantener E_j >= 5).
    gl = k - 1 - m, con m = numero de parametros estimados de los datos.
    Aqui m = 0 porque U(0,1) no tiene parametros que estimar.
    """
    n = len(u)
    esperado = n / k
    if esperado < 5:
        raise ValueError(f"frecuencia esperada {esperado:.1f} < 5: reducir k o subir n")

    frec = [0] * k
    for valor in u:
        idx = min(int(valor * k), k - 1)
        frec[idx] += 1

    chi2 = sum((o - esperado) ** 2 / esperado for o in frec)
    gl = k - 1 - m_parametros_estimados
    critico = CHI2_CRIT_005.get(gl)

    return {
        "prueba": "Chi-cuadrado (uniformidad)",
        "n": n,
        "k_intervalos": k,
        "frecuencia_esperada_por_intervalo": esperado,
        "frecuencias_observadas": frec,
        "chi2_calculado": round(chi2, 4),
        "grados_libertad": gl,
        "chi2_critico_0.05": critico,
        "rechaza_H0": chi2 > critico if critico else None,
    }


def prueba_ks(u):
    """Kolmogorov-Smirnov contra la acumulada teorica F(x) = x en [0,1].

    D_n = max |F_empirica - F_teorica|. Ventaja sobre chi-cuadrado: no
    requiere agrupar en intervalos. Valido aqui en su forma original porque
    los parametros de U(0,1) son CONOCIDOS, no estimados de los datos.
    """
    n = len(u)
    orden = sorted(u)
    d_mas = max((i + 1) / n - orden[i] for i in range(n))
    d_menos = max(orden[i] - i / n for i in range(n))
    d = max(d_mas, d_menos)
    critico = KS_COEF_005 / math.sqrt(n)

    return {
        "prueba": "Kolmogorov-Smirnov (uniformidad)",
        "n": n,
        "D_mas": round(d_mas, 5),
        "D_menos": round(d_menos, 5),
        "D_n": round(d, 5),
        "d_critico_0.05": round(critico, 5),
        "rechaza_H0": d > critico,
    }


def bateria_completa(u, k=10):
    """Corre las tres pruebas. Un generador se acepta solo si pasa TODAS."""
    resultados = [prueba_corridas(u), prueba_chi_cuadrado(u, k), prueba_ks(u)]
    return {
        "resultados": resultados,
        "generador_aceptado": not any(r["rechaza_H0"] for r in resultados),
    }
