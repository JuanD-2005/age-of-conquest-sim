"""
Analisis de salida por replicas (Unidad IV) -- estima el comportamiento medio
de una partida de Age of Conquest a partir de multiples corridas independientes
y reporta un intervalo de confianza, no solo un numero puntual.

Cada replica es una partida completa con una semilla maestra distinta. Las
semillas se generan con el GCL propio del proyecto (rng.py) para no introducir
un generador ajeno al motor ya validado, y se filtran a impares y no nulas
porque BancoDeStreams lo exige (Seccion 6.2.4 del documento).
"""

import csv
import math
import os
from statistics import mean, stdev

from rng import GCL
from simulacion import correr

SEP = "=" * 74

N_REPLICAS = 40           # dentro del rango 30-50 pedido
TURNOS_MAX = 200
SEMILLA_GENERADORA = 20260806   # solo genera la LISTA de semillas; no se usa en la simulacion
DIR_RESULTADOS = "resultados"
CSV_REPLICAS = os.path.join(DIR_RESULTADOS, "replicas.csv")

# ---------------------------------------------------------------------------
# t de Student, alfa=0.05 dos colas -- tabulado, misma convencion que
# pruebas.CHI2_CRIT_005: sin dependencias externas.
# ---------------------------------------------------------------------------

T_CRIT_0975 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
    8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
    15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056,
    27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042, 35: 2.030, 40: 2.021,
    45: 2.014, 50: 2.009, 60: 2.000, 120: 1.980,
}
Z_CRIT_0975 = 1.960   # limite de la t cuando df -> infinito (normal estandar)


def t_critico(df):
    """t_{0.975} para df grados de libertad, con interpolacion lineal entre
    las entradas tabuladas cuando df no cae exacto (tabla estandar de
    cualquier libro de la Unidad IV). Para df fuera de la tabla por arriba,
    converge a la normal (Z_CRIT_0975).
    """
    if df in T_CRIT_0975:
        return T_CRIT_0975[df]
    claves = sorted(T_CRIT_0975)
    if df > claves[-1]:
        return Z_CRIT_0975
    if df < claves[0]:
        return T_CRIT_0975[claves[0]]
    inferior = max(k for k in claves if k < df)
    superior = min(k for k in claves if k > df)
    frac = (df - inferior) / (superior - inferior)
    return T_CRIT_0975[inferior] + frac * (T_CRIT_0975[superior] - T_CRIT_0975[inferior])


def media_ic95(valores):
    """Media muestral e intervalo de confianza al 95% con la t de Student.

    Se usa t (no Z) porque sigma poblacional es DESCONOCIDA y se estima de la
    propia muestra (stdev con divisor n-1) -- ese es el criterio que separa
    "usar Z" de "usar t" en la Unidad IV, no el tamano de n por si solo. Con
    n>=30 la t ya esta muy cerca de la normal (ver nota impresa en main()),
    asi que el margen no cambiaria de forma material si se usara Z, pero t
    sigue siendo la eleccion tecnicamente correcta.
    """
    n = len(valores)
    m = mean(valores)
    if n < 2:
        return m, (m, m)
    s = stdev(valores)
    margen = t_critico(n - 1) * s / math.sqrt(n)
    return m, (m - margen, m + margen)


# ---------------------------------------------------------------------------
# Generacion de semillas y ejecucion de replicas
# ---------------------------------------------------------------------------

def generar_semillas(n, semilla_generadora=SEMILLA_GENERADORA):
    """n semillas maestras impares, no nulas y distintas, reproducibles.

    Se generan con el GCL del proyecto en vez de random.sample para mantener
    la reproducibilidad end-to-end: la MISMA semilla_generadora produce
    siempre la MISMA lista de semillas de replica.
    """
    if semilla_generadora % 2 == 0:
        semilla_generadora += 1
    gen = GCL(semilla_generadora)
    vistas = set()
    semillas = []
    while len(semillas) < n:
        candidata = gen.siguiente_entero()
        if candidata % 2 == 1 and candidata != 0 and candidata not in vistas:
            vistas.add(candidata)
            semillas.append(candidata)
    return semillas


def correr_replica(semilla):
    partida, _, stats = correr(semilla=semilla, turnos_max=TURNOS_MAX)
    ganador = stats["ganador"]
    politica_ganador = (partida.imperios[ganador].politica_estrategica.value
                         if ganador is not None else None)
    n_combates = sum(1 for b in partida.bitacora if b["evento"] == "COMBATE")
    n_conquistas = sum(1 for b in partida.bitacora
                       if b["evento"] == "COMBATE" and "CONQUISTA" in b["detalle"])
    return {
        "semilla": semilla,
        "turno_final": stats["turno_final"],
        "ganador": ganador if ganador is not None else "",
        "politica_ganador": politica_ganador or "",
        "n_combates": n_combates,
        "n_conquistas": n_conquistas,
    }


def exportar_csv(filas, ruta):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    campos = ["semilla", "turno_final", "ganador", "politica_ganador",
              "n_combates", "n_conquistas"]
    with open(ruta, "w", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(filas)


def main():
    semillas = generar_semillas(N_REPLICAS)
    filas = [correr_replica(s) for s in semillas]
    exportar_csv(filas, CSV_REPLICAS)

    turnos = [f["turno_final"] for f in filas]
    conquistas = [f["n_conquistas"] for f in filas]
    ganadores = [f for f in filas if f["ganador"] != ""]

    m_turno, ic_turno = media_ic95(turnos)
    m_conq, ic_conq = media_ic95(conquistas)

    print(f"\n{SEP}\nANALISIS DE SALIDA -- {N_REPLICAS} replicas, T_max={TURNOS_MAX}\n{SEP}")
    print(f"\nSemillas generadas con GCL(semilla_generadora={SEMILLA_GENERADORA}), "
          f"impares, distintas y reproducibles.")
    print(f"\nPartidas con ganador: {len(ganadores)}/{N_REPLICAS} "
          f"({100 * len(ganadores) / N_REPLICAS:.0f}%)")

    print(f"\nturno_final:   media = {m_turno:.2f}   "
          f"IC95% = [{ic_turno[0]:.2f}, {ic_turno[1]:.2f}]")
    print(f"n_conquistas:  media = {m_conq:.2f}   "
          f"IC95% = [{ic_conq[0]:.2f}, {ic_conq[1]:.2f}]")

    df = N_REPLICAS - 1
    print(f"\nNota metodologica: el IC usa la t de Student (df={df}) porque "
          f"sigma poblacional es desconocida y se estima de la muestra "
          f"(stdev con divisor n-1). Con n={N_REPLICAS} >= 30 la t ya esta "
          f"cerca de la normal: t_0.975(df={df})={t_critico(df):.3f} vs "
          f"Z_0.975={Z_CRIT_0975}. El margen no cambiaria de forma material "
          f"si se usara Z, pero t sigue siendo la eleccion correcta cuando "
          f"sigma se estima de los datos, sin importar n.")

    print(f"\nCSV exportado a {CSV_REPLICAS}\n")


if __name__ == "__main__":
    main()
