"""
Motor de generacion de numeros pseudoaleatorios para Age of Conquest.

Contiene DOS generadores:

  1. GCL  -- Generador Congruencial Lineal mixto de periodo completo.
            Se conserva porque es el generador canonico de la Unidad III y
            permite verificar las condiciones de Hull-Dobell. NO se usa para
            la simulacion de produccion (ver nota abajo).

  2. GeneradorCombinado -- dos generadores multiplicativos con modulos primos
            distintos, combinados por resta. Es el que alimenta la simulacion.

POR QUE NO SE USA UN SOLO GCL PARA TODA LA SIMULACION
-----------------------------------------------------
Un GCL admite salto adelante en forma cerrada: x_(n+k) = A_k*x_n + B_k mod m.
Eso es comodo para particionar el periodo en streams no solapados, PERO tiene
una consecuencia que invalida la independencia entre subsistemas: si dos
streams se separan por un salto fijo k, entonces para todo i se cumple

        x2_i = A_k * x1_i + B_k   (mod m)

es decir, el i-esimo valor de un stream determina exactamente el i-esimo valor
del otro. Se verifico empiricamente: 500 de 500 pares cumplian la relacion.

En Age of Conquest las bajas del atacante y del defensor se generan en
paralelo (un ensayo Bernoulli por soldado de cada bando dentro del mismo
evento de combate), o sea EN LOCKSTEP. Con streams de GCL, la suerte del
defensor quedaria determinada por la del atacante. La prueba de corridas
sobre las dos secuencias intercaladas lo detecta: Z = -2.60 (rechaza H0).

El generador combinado rompe esa relacion porque los dos componentes tienen
modulos distintos y la salida es (x1 - x2) mod (m1-1): un mapa afin en cada
componente por separado NO produce un mapa afin en la diferencia.

Beneficio adicional: la transcripcion del curso advierte que el ciclo de un
GCL de 2^31 "se ha tornado inadecuado, ya que se corre un riesgo de que en
unas cuantas horas de simulacion la secuencia se agote". El combinado tiene
periodo ~2.3x10^18 en lugar de 2.1x10^9.

Sin dependencias externas: solo biblioteca estandar de Python.
"""

# ---------------------------------------------------------------------------
# 1. GCL mixto (referencia teorica / verificacion Hull-Dobell)
# ---------------------------------------------------------------------------

K_BITS = 31
M = 2 ** K_BITS          # modulo potencia de 2 -> mod eficiente
A = 1103515245           # = 4*275878811 + 1  -> a = 4c+1
B = 12345                # impar -> mcd(b, m) = 1


def verificar_periodo_completo(a=A, b=B, k=K_BITS):
    """Condiciones de Hull-Dobell para periodo maximo con m = 2^k.

    1. mcd(b, m) = 1            -> b impar (unico factor primo de 2^k es 2)
    2. (a-1) divisible por 2    -> todo primo que divide m divide (a-1)
    3. (a-1) divisible por 4    -> porque 4 | m
    Las tres se resumen en: m = 2^k, a = 4c+1, b impar.
    """
    return {
        "b impar -> mcd(b,m)=1": b % 2 == 1,
        "(a-1) divisible por 2": (a - 1) % 2 == 0,
        "(a-1) divisible por 4 -> a=4c+1": (a - 1) % 4 == 0,
        "periodo maximo teorico": 2 ** k,
    }


class GCL:
    """Generador Congruencial Lineal mixto: x_n = (a*x_(n-1) + b) mod m."""

    def __init__(self, semilla, a=A, b=B, m=M):
        if b == 0 and semilla % m == 0:
            raise ValueError("semilla 0 en generador multiplicativo colapsa a 0")
        self.a, self.b, self.m = a, b, m
        self.semilla_inicial = semilla % m
        self.x = self.semilla_inicial
        self.n_generados = 0

    def siguiente_entero(self):
        self.x = (self.a * self.x + self.b) % self.m
        self.n_generados += 1
        return self.x

    def u(self):
        """U(0,1) abierto: se usa (x+0.5)/m para excluir 0 y 1 exactos.

        Un 0 rompe transformadas inversas del tipo ln(u); un 1 rompe
        -media*ln(1-u).
        """
        return (self.siguiente_entero() + 0.5) / self.m

    def reiniciar(self):
        self.x = self.semilla_inicial
        self.n_generados = 0

    def _componer_salto(self, k):
        """(A_k, B_k) tal que x_(n+k) = A_k*x_n + B_k mod m.

        Exponenciacion binaria sobre la funcion afin f(x)=ax+b. Evita dividir
        entre (a-1), que no es invertible modulo 2^k.
        """
        a_ac, b_ac = 1, 0
        a_p, b_p = self.a, self.b
        while k > 0:
            if k & 1:
                a_ac, b_ac = (a_ac * a_p) % self.m, (a_ac * b_p + b_ac) % self.m
            a_p, b_p = (a_p * a_p) % self.m, (a_p * b_p + b_p) % self.m
            k >>= 1
        return a_ac, b_ac

    def semilla_saltada(self, k):
        a_k, b_k = self._componer_salto(k)
        return (a_k * self.semilla_inicial + b_k) % self.m


# ---------------------------------------------------------------------------
# 2. Generador combinado (motor de produccion)
# ---------------------------------------------------------------------------

M1, A1 = 2147483563, 40014
M2, A2 = 2147483399, 40692
M1_MENOS_1 = M1 - 1


class GeneradorCombinado:
    """Dos generadores multiplicativos de modulo primo, combinados por resta.

        x1_n = a1 * x1_(n-1) mod m1
        x2_n = a2 * x2_(n-1) mod m2
        z_n  = (x1_n - x2_n) mod (m1 - 1)
        u_n  = z_n / m1        (con z_n = 0 mapeado a (m1-1)/m1)

    Periodo aproximado: (m1-1)(m2-1)/2 ~ 2.3 x 10^18.
    Las semillas deben ser NO NULAS: en un generador multiplicativo el cero
    es un punto fijo absorbente (recomendacion "no usar cero", Unidad III).
    """

    def __init__(self, s1, s2):
        if s1 % M1 == 0 or s2 % M2 == 0:
            raise ValueError("semilla nula: colapsa el generador multiplicativo")
        self.s1_inicial = s1 % M1
        self.s2_inicial = s2 % M2
        self.x1 = self.s1_inicial
        self.x2 = self.s2_inicial
        self.n_generados = 0

    def siguiente_entero(self):
        self.x1 = (A1 * self.x1) % M1
        self.x2 = (A2 * self.x2) % M2
        self.n_generados += 1
        return (self.x1 - self.x2) % M1_MENOS_1

    def u(self):
        z = self.siguiente_entero()
        return z / M1 if z > 0 else M1_MENOS_1 / M1

    def reiniciar(self):
        self.x1, self.x2 = self.s1_inicial, self.s2_inicial
        self.n_generados = 0

    def semillas_saltadas(self, k):
        """Semillas tras avanzar k pasos: x_(n+k) = a^k * x_n mod m.

        En un generador multiplicativo el salto es una potencia modular,
        calculable con pow(a, k, m) en tiempo logaritmico.
        """
        return (pow(A1, k, M1) * self.s1_inicial % M1,
                pow(A2, k, M2) * self.s2_inicial % M2)


class BancoDeStreams:
    """Un stream independiente por cada fuente de aleatoriedad del modelo.

    Problema que resuelve (simulaciones de secuencia multiple, Unidad III):
    usar un unico generador global para combate, IA y tiempos de viaje
    introduce correlacion entre subsistemas que el modelo declara
    independientes.

    Construccion: se parte de una semilla maestra y se avanza SALTO posiciones
    por stream, de modo que los bloques del periodo sean disjuntos. Con el
    generador combinado, ademas, los streams no quedan ligados por un mapa
    afin (a diferencia del GCL puro; ver nota de cabecera del modulo).
    """

    SALTO = 2 ** 40  # bloque por stream; el periodo total es ~2^61

    NOMBRES = [
        "combate_atacante",   # B^D ~ Binomial(S_j, pA)   bajas del defensor
        "combate_defensor",   # B^A ~ Binomial(A_k, pD)   bajas del atacante
        "decision_ia",        # evaluarOpcionesEstocasticas
        "tiempo_viaje",       # tau_k ~ Triangular(a, c, b)
        "desercion",          # Ev_CrisisFinanciera
    ]

    def __init__(self, semilla_maestra=7):
        if semilla_maestra % 2 == 0:
            raise ValueError(
                "semilla maestra par: recomendacion de la Unidad III es no "
                "usar valores pares ni cero"
            )
        self.semilla_maestra = semilla_maestra
        base = GeneradorCombinado(semilla_maestra, semilla_maestra + 1)
        self.streams = {}
        for idx, nombre in enumerate(self.NOMBRES):
            s1, s2 = base.semillas_saltadas(idx * self.SALTO)
            self.streams[nombre] = GeneradorCombinado(s1, s2)

    def __getitem__(self, nombre):
        return self.streams[nombre]

    def reporte_uso(self):
        return {n: g.n_generados for n, g in self.streams.items()}

    def verificar_no_solape(self):
        return all(g.n_generados < self.SALTO for g in self.streams.values())

    def reiniciar_todos(self):
        """Reproducibilidad: reinicia la corrida completa desde la semilla."""
        for g in self.streams.values():
            g.reiniciar()
