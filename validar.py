"""Validacion del motor de aleatoriedad de Age of Conquest (Parcial III)."""

from rng import (GCL, GeneradorCombinado, BancoDeStreams,
                 verificar_periodo_completo, M, A, B, K_BITS, M1, M2)
from pruebas import bateria_completa, prueba_corridas
from variables import binomial, triangular_entero

SEP = "=" * 74
def sec(t): print(f"\n{SEP}\n{t}\n{SEP}")

def pearson(a, b):
    """Correlacion de Pearson entre dos muestras alineadas, sin numpy."""
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    den = (sum((v - ma) ** 2 for v in a) * sum((v - mb) ** 2 for v in b)) ** 0.5
    return cov / den

# --- 1 ---------------------------------------------------------------------
sec("1. GCL: VERIFICACION DE PERIODO COMPLETO (Hull-Dobell)")
print(f"x_n = ({A} * x_(n-1) + {B}) mod 2^{K_BITS}\n")
for k, v in verificar_periodo_completo().items():
    print(f"   {k}: {v}")
g = GCL(1, a=5, b=1, m=16); g.x = 1
vistos = []
for _ in range(40):
    x = g.siguiente_entero()
    if x in vistos: break
    vistos.append(x)
print(f"\n   Comprobacion empirica (m=16, a=5, b=1): periodo = {len(vistos)}/16"
      f" -> {'COMPLETO' if len(vistos)==16 else 'INCOMPLETO'}")

# --- 2 ---------------------------------------------------------------------
sec("2. HALLAZGO: POR QUE EL GCL NO SIRVE PARA STREAMS MULTIPLES")
gb = GCL(7); SALTO = 2**20
Ak, Bk = gb._componer_salto(SALTO)
g1, g2 = GCL(7), GCL(gb.semilla_saltada(SALTO))
ok = sum(1 for _ in range(500)
         if (Ak * g1.siguiente_entero() + Bk) % M == g2.siguiente_entero())
print(f"   Relacion afin x2_i = A_k*x1_i + B_k (mod m): {ok}/500 pares la cumplen")
g1.reiniciar(); g2.reiniciar()
s1 = [g1.u() for _ in range(5000)]
s2 = [g2.u() for _ in range(5000)]
inter = [v for p in zip(s1, s2) for v in p]
r = prueba_corridas(inter)
print(f"   Prueba de corridas sobre streams intercalados: Z = {r['Z']}"
      f" -> rechaza H0 = {r['rechaza_H0']}")
print(f"   Correlacion de Pearson entre pares alineados: {pearson(s1, s2):.5f}")
print("   CONCLUSION: streams de GCL por salto NO son independientes en lockstep.")

# --- 3 ---------------------------------------------------------------------
sec("3. GENERADOR COMBINADO: CONTRASTES EMPIRICOS")
print(f"   x1_n = 40014*x1 mod {M1}   |   x2_n = 40692*x2 mod {M2}")
print(f"   Periodo aproximado: {(M1-1)*(M2-1)//2:,.0f}\n")
gc = GeneradorCombinado(7, 8)
muestra = [gc.u() for _ in range(10000)]
bat = bateria_completa(muestra, k=10)
for res in bat["resultados"]:
    print(f"   {res['prueba']}")
    for k, v in res.items():
        if k != "prueba": print(f"      {k}: {v}")
    print(f"      --> {'RECHAZA H0' if res['rechaza_H0'] else 'NO rechaza H0 (bien)'}\n")
print(f"   GENERADOR ACEPTADO: {bat['generador_aceptado']}")

# --- 4 ---------------------------------------------------------------------
sec("4. STREAMS POR SUBSISTEMA (correlacion cruzada corregida)")
banco = BancoDeStreams(semilla_maestra=7)
print(f"   Bloque por stream: {banco.SALTO:,} valores\n")
for n in banco.NOMBRES:
    gg = banco[n]
    print(f"      {n:<20} semillas = ({gg.s1_inicial}, {gg.s2_inicial})")
s1 = [banco["combate_atacante"].u() for _ in range(3000)]
s2 = [banco["combate_defensor"].u() for _ in range(3000)]
inter = [v for p in zip(s1, s2) for v in p]
r = prueba_corridas(inter)
n = len(s1); mx = sum(s1)/n; my = sum(s2)/n
cov = sum((s1[i]-mx)*(s2[i]-my) for i in range(n))
pearson = cov / ((sum((v-mx)**2 for v in s1) * sum((v-my)**2 for v in s2))**0.5)
print(f"\n   Corridas sobre intercalado lockstep: Z = {r['Z']} "
      f"-> rechaza H0 = {r['rechaza_H0']}")
print(f"   Correlacion de Pearson entre pares alineados: {pearson:.5f}")
print(f"   Valores en comun entre los dos streams: {len(set(s1) & set(s2))}")
banco.reiniciar_todos()
for nom in banco.NOMBRES:
    gg = banco[nom]
    b = bateria_completa([gg.u() for _ in range(5000)], k=10)
    print(f"      {nom:<20} bateria completa -> aceptado = {b['generador_aceptado']}")

# --- 5 ---------------------------------------------------------------------
sec("5. SUBSISTEMAS ESTOCASTICOS DE AGE OF CONQUEST")
banco.reiniciar_todos()
k_c, beta = 0.3, 0.25
S, F, Ak_t = 500, 2, 800
D = S * (1 + beta*F); pA = k_c*Ak_t/(Ak_t+D); pD = k_c*D/(Ak_t+D)
print(f"\n   5.1 Combate: A_k={Ak_t}, S={S}, F={F}, D_eff={D}")
print(f"       pA={pA:.4f}  pD={pD:.4f}   (ambas en [0, k_c] -> validas)")
bd = [binomial(banco["combate_atacante"], S, pA) for _ in range(1000)]
ba = [binomial(banco["combate_defensor"], Ak_t, pD) for _ in range(1000)]
print(f"       Bajas defensor: media {sum(bd)/1000:.2f} vs teorica {S*pA:.2f}"
      f"  (error {abs(sum(bd)/1000-S*pA)/(S*pA)*100:.2f}%)")
print(f"       Bajas atacante: media {sum(ba)/1000:.2f} vs teorica {Ak_t*pD:.2f}"
      f"  (error {abs(sum(ba)/1000-Ak_t*pD)/(Ak_t*pD)*100:.2f}%)")

print(f"\n   5.2 Caso borde A_k=0 y D_eff=0 (division por cero, ec. 8)")
A0, S0, F0 = 0, 0, 0
D0 = S0*(1+beta*F0)
print(f"       A_k + D_eff = {A0+D0} -> combate NULO por definicion, "
      f"pA=pD=0, no se invoca Binomial")

print(f"\n   5.3 tau_k ~ Triangular(1, 2, 5) turnos")
taus = [triangular_entero(banco["tiempo_viaje"], 1, 2, 5) for _ in range(2000)]
print(f"       media simulada {sum(taus)/2000:.3f} (teorica {(1+2+5)/3:.3f})")
print(f"       reparto: { {v: taus.count(v) for v in sorted(set(taus))} }")

print(f"\n   5.4 Desercion con piso entero (garantiza terminacion)")
delta, c_m, I = 0.10, 0.5, 0.02
tropas, pob = 1000, 20000
ingreso = I*pob; it = 0
while c_m*tropas > ingreso and tropas > 0 and it < 200:
    tropas = int(tropas*(1-delta)); it += 1
print(f"       ingreso {ingreso:.1f}/turno vs gasto inicial 500.0/turno")
print(f"       converge en {it} iteraciones -> {tropas} soldados "
      f"(gasto {c_m*tropas:.1f})")

# --- 6 ---------------------------------------------------------------------
sec("6. REPRODUCIBILIDAD")
def corrida(semilla):
    b = BancoDeStreams(semilla)
    return [binomial(b["combate_atacante"], 100, 0.3) for _ in range(20)]
print(f"   semilla 7  (1a vez): {corrida(7)[:10]}")
print(f"   semilla 7  (2a vez): {corrida(7)[:10]}")
print(f"   semilla 11          : {corrida(11)[:10]}")
print(f"\n   Identicas con misma semilla: {corrida(7) == corrida(7)}")
print(f"   Distintas con otra semilla:  {corrida(7) != corrida(11)}")
print(f"\n   Uso final de streams: {banco.reporte_uso()}")
print(f"   Sin solape: {banco.verificar_no_solape()}\n")
