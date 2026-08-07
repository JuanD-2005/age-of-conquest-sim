"""
Barrido de sensibilidad de parametros clave -- complementa la Seccion 1.4.

No existen datos empiricos de partidas reales de Age of Conquest con los que
calibrar k_c, rho_atk, beta y S_min contra observaciones (ver nota en la
Seccion 1.4 del documento). En su lugar, este script mide como cambia el
COMPORTAMIENTO AGREGADO del sistema -- turno de victoria, tasa de partidas
sin ganador, numero de combates -- al variar cada parametro en un rango
razonable con el resto de la configuracion fija. Es la respuesta a la
pregunta que un evaluador va a hacer: "por que 0.3 y no 0.5".

No modifica el modelo ni su comportamiento: solo lo ejecuta repetidas veces
con distintos valores de Parametros y agrega estadisticas.

REVISION (N=10 -> N=40): la primera version corria 10 semillas por valor de
parametro y concluia "k_c domina, los otros tres son robustos" a partir de
comparar solo las medias. Eso confunde "no se detecto tendencia" con "no hay
efecto": con N=10 la varianza muestral es grande y puede enmascarar un efecto
real. Aqui se sube a N=40 (mismo orden que replicas.py) y la conclusion para
cada parametro se decide con el IC 95% de turno_victoria y de combates, no a
ojo sobre la media -- ver `pares_sin_solape()`. Reusa la generacion de
semillas y el calculo de IC de replicas.py en vez de duplicarlos.

REVISION 2 (confirmacion con t de Welch): comparar si dos IC 95% se solapan
es un criterio CONSERVADOR -- que se toquen no demuestra que no haya
diferencia, solo que ese criterio en particular no la detecto (es mas
estricto que una prueba de hipotesis de dos muestras propiamente dicha).
Para beta y S_min, que el criterio de solapamiento declaro "sin efecto
distinguible", se agrega una prueba t de Welch (varianzas no asumidas
iguales) entre cada par CONSECUTIVO de valores del barrido, con correccion
de Bonferroni sobre alfa=0.05 (dividido entre el numero de pares
consecutivos comparados EN ESA FAMILIA -- turno_victoria y combates se
corrigen por separado, no mezclados, porque son dos preguntas distintas).
No hace falta repetir esto para k_c y rho_atk: el criterio de IC, que ya es
mas exigente, ya mostro efecto para esos dos.

La prueba de Welch esta implementada a mano (sin scipy) via la funcion beta
incompleta regularizada (Numerical Recipes 6.4), en la misma linea que
pruebas.py tabula valores criticos en vez de importar un paquete externo:
el motor de aleatoriedad y sus contrastes se mantienen auditables sin caja
negra. Verificado contra la tabla T_CRIT_0975 de replicas.py: p_valor_t(t,
df) para los t criticos tabulados da ~0.0500 en todos los casos probados.
"""

import math
from statistics import mean, variance

from entidades import Parametros
from simulacion import correr
from replicas import generar_semillas, media_ic95

SEP = "=" * 74

# Semillas impares, no nulas, reproducibles y FIJAS entre valores de un mismo
# barrido: la unica fuente de variacion en cada fila es el valor del
# parametro, no el azar de la muestra de semillas -- comparacion controlada
# (Seccion 6.2.4). Se generan con el GCL propio del proyecto, mismo patron
# que replicas.py, con una semilla generadora propia para no acoplar los dos
# scripts de analisis entre si.
N_SEMILLAS = 40
SEMILLA_GENERADORA = 30260807
SEMILLAS = generar_semillas(N_SEMILLAS, SEMILLA_GENERADORA)
T_MAX = 200

# Rangos de barrido centrados en el valor de referencia de cada parametro.
BARRIDOS = {
    "k_c":     [0.1, 0.2, 0.3, 0.4, 0.5],
    "rho_atk": [1.1, 1.3, 1.5, 1.8, 2.2],
    "beta":    [0.0, 0.1, 0.25, 0.4, 0.6],
    "S_min":   [10, 30, 50, 80, 120],
}

# Parametros donde el criterio de IC (mas conservador) ya declaro "sin
# efecto distinguible" y por eso se confirman con una prueba disenada para
# eso. k_c y rho_atk ya mostraron efecto por IC -- no hace falta repetirlo.
PARAMETROS_A_CONFIRMAR_CON_WELCH = ("beta", "S_min")


# ---------------------------------------------------------------------------
# t de Welch sin scipy: beta incompleta regularizada (Numerical Recipes 6.4)
# ---------------------------------------------------------------------------

def _betacf(a, b, x, itmax=200, eps=3e-9, fpmin=1e-30):
    """Fraccion continua de la funcion beta incompleta (Numerical Recipes)."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betai(a, b, x):
    """I_x(a, b): funcion beta incompleta regularizada."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) +
                  a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def p_valor_t(t_stat, df):
    """P-valor de dos colas para el estadistico t con df grados de libertad.

    P(|T| > |t|) = I_x(df/2, 1/2) con x = df/(df+t^2) -- relacion estandar
    entre la t de Student y la beta incompleta regularizada. Verificado
    contra T_CRIT_0975 (replicas.py): da ~0.0500 en los t criticos tabulados.
    """
    x = df / (df + t_stat ** 2)
    return _betai(df / 2.0, 0.5, x)


def welch_t_test(a, b):
    """t de Welch (varianzas no asumidas iguales) entre dos muestras
    independientes. Devuelve (t, df, p_valor); None si falta variabilidad
    para estimarla (n<2 en algun grupo).
    """
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return None
    m1, m2 = mean(a), mean(b)
    v1, v2 = variance(a), variance(b)
    se2 = v1 / n1 + v2 / n2
    if se2 == 0.0:
        # las dos muestras son constantes: diferencia perfecta o nula.
        return (0.0, None, 1.0) if m1 == m2 else (math.inf, None, 0.0)
    t_stat = (m1 - m2) / math.sqrt(se2)
    df = se2 ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1))
    return t_stat, df, p_valor_t(t_stat, df)


def comparaciones_welch_consecutivas(filas, campo_raw, alfa=0.05):
    """t de Welch entre cada par CONSECUTIVO de valores del barrido, con el
    umbral de significancia corregido por Bonferroni: alfa / numero de pares
    consecutivos comparados en esta familia (mismo parametro, misma metrica).
    """
    pares_validos = [(filas[i], filas[i + 1]) for i in range(len(filas) - 1)
                     if len(filas[i][campo_raw]) >= 2 and len(filas[i + 1][campo_raw]) >= 2]
    if not pares_validos:
        return [], alfa
    alfa_corregido = alfa / len(pares_validos)
    resultados = []
    for f1, f2 in pares_validos:
        t_stat, df, p = welch_t_test(f1[campo_raw], f2[campo_raw])
        resultados.append({
            "v1": f1["valor"], "v2": f2["valor"],
            "t": t_stat, "df": df, "p": p,
            "significativo": p < alfa_corregido,
        })
    return resultados, alfa_corregido


def _guardar_parametros():
    return {nombre: getattr(Parametros, nombre) for nombre in BARRIDOS}


def _restaurar_parametros(snapshot):
    for nombre, valor in snapshot.items():
        setattr(Parametros, nombre, valor)


def correr_con(parametro, valor, semillas=SEMILLAS, turnos_max=T_MAX):
    """Corre el conjunto fijo de semillas con Parametros.<parametro> = valor.

    Devuelve una fila con media + IC 95% de turno_victoria (solo sobre las
    corridas CON ganador) y de numero de combates (sobre las N corridas).
    """
    anterior = getattr(Parametros, parametro)
    setattr(Parametros, parametro, valor)
    try:
        turnos_ganador = []
        sin_ganador = 0
        combates = []
        for semilla in semillas:
            partida, _, stats = correr(semilla=semilla, turnos_max=turnos_max)
            n_combates = sum(1 for b in partida.bitacora if b["evento"] == "COMBATE")
            combates.append(n_combates)
            if stats["ganador"] is not None:
                turnos_ganador.append(stats["turno_final"])
            else:
                sin_ganador += 1

        if len(turnos_ganador) >= 2:
            m_turno, ic_turno = media_ic95(turnos_ganador)
        elif len(turnos_ganador) == 1:
            m_turno, ic_turno = turnos_ganador[0], None
        else:
            m_turno, ic_turno = None, None

        m_comb, ic_comb = media_ic95(combates)

        return {
            "parametro": parametro,
            "valor": valor,
            "n_con_ganador": len(turnos_ganador),
            "turno_victoria_medio": m_turno,
            "turno_victoria_ic95": ic_turno,
            "turno_victoria_raw": turnos_ganador,
            "pct_sin_ganador": 100 * sin_ganador / len(semillas),
            "combates_medio": m_comb,
            "combates_ic95": ic_comb,
            "combates_raw": combates,
            "n_semillas": len(semillas),
        }
    finally:
        setattr(Parametros, parametro, anterior)


def ejecutar_barrido(parametro, valores):
    return [correr_con(parametro, v) for v in valores]


# ---------------------------------------------------------------------------
# Decision de la conclusion a partir de los IC, no de la media a ojo
# ---------------------------------------------------------------------------

def pares_sin_solape(filas, campo_ic):
    """Pares de valores del barrido cuyos IC 95% (campo_ic) NO se solapan.

    Un par sin solape es evidencia de una diferencia real entre esos dos
    niveles del parametro, al 95% de confianza. Una lista vacia significa
    que, con N=len(SEMILLAS) semillas, ningun par de niveles es
    distinguible en esa metrica -- lo cual es una afirmacion mas debil que
    "el sistema es robusto" (que implicaria que sabemos que no hay efecto).
    """
    puntos = [(f["valor"], f[campo_ic]) for f in filas if f[campo_ic] is not None]
    pares = []
    for i in range(len(puntos)):
        for j in range(i + 1, len(puntos)):
            v1, (lo1, hi1) = puntos[i]
            v2, (lo2, hi2) = puntos[j]
            if hi1 < lo2 or hi2 < lo1:
                pares.append((v1, v2))
    return pares


def conclusion_parametro(parametro, filas):
    pares_turno = pares_sin_solape(filas, "turno_victoria_ic95")
    pares_comb = pares_sin_solape(filas, "combates_ic95")

    lineas = []
    if pares_turno:
        lineas.append(
            f"  turno_victoria: efecto DISTINGUIBLE (IC95%, N={len(SEMILLAS)}) "
            f"entre {parametro}=" +
            ", ".join(f"{{{a}}} vs {{{b}}}" for a, b in pares_turno))
    else:
        sufijo = (" Criterio conservador -- se confirma abajo con t de Welch."
                  if parametro in PARAMETROS_A_CONFIRMAR_CON_WELCH else
                  " No implica ausencia de efecto, implica que este barrido no lo detecta.")
        lineas.append(
            f"  turno_victoria: SIN efecto distinguible entre los valores "
            f"probados (IC95% se solapan en todos los pares, N={len(SEMILLAS)})." + sufijo)

    if pares_comb:
        lineas.append(
            f"  combates:       efecto DISTINGUIBLE (IC95%, N={len(SEMILLAS)}) "
            f"entre {parametro}=" +
            ", ".join(f"{{{a}}} vs {{{b}}}" for a, b in pares_comb))
    else:
        sufijo = (" Criterio conservador -- se confirma abajo con t de Welch."
                  if parametro in PARAMETROS_A_CONFIRMAR_CON_WELCH else "")
        lineas.append(
            f"  combates:       SIN efecto distinguible entre los valores "
            f"probados (IC95% se solapan en todos los pares, N={len(SEMILLAS)})." + sufijo)

    return "\n".join(lineas)


def imprimir_welch(parametro, filas):
    """Confirma (o contradice) la lectura de pares_sin_solape() con una
    prueba de hipotesis propiamente dicha: t de Welch entre pares
    consecutivos, con Bonferroni sobre el umbral de significancia.
    """
    print(f"\n  --- Confirmacion con t de Welch (Bonferroni) para {parametro} ---")
    for etiqueta, campo_raw in (("turno_victoria", "turno_victoria_raw"),
                                ("combates", "combates_raw")):
        resultados, alfa_corr = comparaciones_welch_consecutivas(filas, campo_raw)
        if not resultados:
            print(f"  {etiqueta}: datos insuficientes para t de Welch")
            continue
        print(f"\n  {etiqueta}  (alfa Bonferroni = 0.05 / {len(resultados)} "
              f"pares consecutivos = {alfa_corr:.4f})")
        significativos = []
        for r in resultados:
            marca = "SIGNIFICATIVO" if r["significativo"] else "no significativo"
            df_txt = f"{r['df']:.1f}" if r["df"] is not None else "--"
            print(f"    {parametro}={r['v1']} vs {parametro}={r['v2']}: "
                  f"t={r['t']:.3f}  df={df_txt}  p={r['p']:.4f}  -> {marca}")
            if r["significativo"]:
                significativos.append((r["v1"], r["v2"]))

        if significativos:
            print(f"    CONCLUSION ({etiqueta}): el t de Welch con Bonferroni SI "
                  f"encuentra diferencia significativa entre " +
                  ", ".join(f"{{{a}}} vs {{{b}}}" for a, b in significativos) +
                  f" -- el criterio de IC (mas conservador) la estaba ocultando. "
                  f"Efecto real, no ausencia de efecto.")
        else:
            print(f"    CONCLUSION ({etiqueta}): el t de Welch con Bonferroni NO "
                  f"encuentra diferencia significativa entre ningun par consecutivo. "
                  f"Esta vez 'sin efecto distinguible' esta respaldado por una prueba "
                  f"disenada para detectarlo, no solo por ausencia de evidencia en contra.")


def imprimir_tabla(filas):
    print(f"\n  {'valor':>8} | {'turno_victoria (IC95%)':>26} | {'%sin_ganador':>13} | "
          f"{'combates (IC95%)':>24}")
    print("  " + "-" * 82)
    for f in filas:
        if f["turno_victoria_medio"] is None:
            tv = "        --        "
        elif f["turno_victoria_ic95"] is None:
            tv = f"{f['turno_victoria_medio']:.1f} (n={f['n_con_ganador']}, sin IC)"
        else:
            lo, hi = f["turno_victoria_ic95"]
            tv = f"{f['turno_victoria_medio']:.1f} [{lo:.1f}, {hi:.1f}]"

        lo_c, hi_c = f["combates_ic95"]
        cb = f"{f['combates_medio']:.1f} [{lo_c:.1f}, {hi_c:.1f}]"

        print(f"  {f['valor']:>8} | {tv:>26} | {f['pct_sin_ganador']:>12.0f}% | {cb:>24}")


def main():
    snapshot = _guardar_parametros()
    try:
        for parametro, valores in BARRIDOS.items():
            print(f"\n{SEP}\nSENSIBILIDAD: {parametro}  "
                  f"(valor de referencia = {snapshot[parametro]}, "
                  f"{len(SEMILLAS)} semillas, T_max={T_MAX})\n{SEP}")
            filas = ejecutar_barrido(parametro, valores)
            imprimir_tabla(filas)
            print()
            print(conclusion_parametro(parametro, filas))
            if parametro in PARAMETROS_A_CONFIRMAR_CON_WELCH:
                imprimir_welch(parametro, filas)
    finally:
        _restaurar_parametros(snapshot)
    print()


if __name__ == "__main__":
    main()
