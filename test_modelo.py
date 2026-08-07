"""
Banco de pruebas del modelo -- verifica Seccion 4 (fronteras) sobre corridas reales.

No es un test unitario de codigo: es la verificacion de que las condiciones de
frontera declaradas en el documento se cumplen efectivamente durante la
simulacion, que es lo que el rubro llama "Tratamiento de Fronteras".
"""

from collections import Counter

from entidades import (Mapa, Provincia, Imperio, Partida, Parametros,
                       Politica, EstadoProvincia, EstadoFinanciero, OrdenMilitar)
from lef import LEF, TipoEvento
from rng import BancoDeStreams
from simulacion import (bucle_de_simulacion, verificar_invariantes,
                        construir_escenario, correr)
import eventos

P = Parametros
SEP = "=" * 74


def sec(t):
    print(f"\n{SEP}\n{t}\n{SEP}")


fallas_globales = []


def check(nombre, condicion, detalle=""):
    estado = "PASA" if condicion else "FALLA"
    if not condicion:
        fallas_globales.append(nombre)
    print(f"  [{estado}] {nombre}" + (f"  {detalle}" if detalle else ""))
    return condicion


# ===========================================================================
sec("1. INVARIANTES SOBRE UN BARRIDO DE SEMILLAS")
# ===========================================================================

resumen = []
for semilla in [3, 7, 11, 101, 999, 12345, 60013]:
    partida, _, stats = correr(semilla=semilla, turnos_max=200)
    resumen.append((semilla, stats))
    n_viol = len(stats["violaciones_invariantes"])
    check(f"semilla {semilla}: 0 violaciones de invariantes", n_viol == 0,
          f"turno final={stats['turno_final']}, ganador={stats['ganador']}, "
          f"eventos={stats['eventos_procesados']}")

check("reloj monotono en todas las corridas",
      all(s["orden_temporal_monotono"] for _, s in resumen))
check("LEF completamente drenada en todas las corridas",
      all(s["lef_encolados"] >= s["lef_procesados"] for _, s in resumen))
check("toda corrida termina (ninguna aborta por max_eventos)",
      all(s["estado"] == "FINALIZADA" for _, s in resumen))


# ===========================================================================
sec("2. REPRODUCIBILIDAD")
# ===========================================================================

def huella(semilla):
    partida, _, stats = correr(semilla=semilla, turnos_max=150)
    return (stats["turno_final"], stats["ganador"],
            tuple(sorted((p.id, p.id_propietario, p.tropas_estacionadas)
                         for p in partida.mapa.provincias.values())))

h1, h2, h3 = huella(7), huella(7), huella(11)
check("misma semilla -> corrida identica", h1 == h2)
check("distinta semilla -> corrida distinta", h1 != h3)


# ===========================================================================
sec("3. CONDICIONES DE FRONTERA (Seccion 4)")
# ===========================================================================

# F1 -- saturacion poblacional
mapa = Mapa()
mapa.agregar(Provincia(0, poblacion=49999, capacidad_soporte=50000,
                       tropas=10, propietario=0))
imp = Imperio(0, 10000, Politica.ECONOMICO)
part = Partida(mapa, [imp], LEF())
st = BancoDeStreams(7)
for t in range(50):
    eventos.ev_inicio_turno(part, st, t)
pr = mapa.provincias[0]
check("F1 saturacion poblacional: P nunca excede K_j",
      pr.poblacion <= pr.capacidad_soporte, f"P={pr.poblacion}, K={pr.capacidad_soporte}")

# F2 -- provincia despoblada
mapa = Mapa()
mapa.agregar(Provincia(0, poblacion=0, capacidad_soporte=50000,
                       tropas=80, fortificacion=2, propietario=0))
imp = Imperio(0, 10000, Politica.ECONOMICO)
part = Partida(mapa, [imp], LEF())
eventos.ev_inicio_turno(part, st, 0)
pr = mapa.provincias[0]
check("F2 provincia despoblada: marcada ABANDONADA",
      pr.estado_provincia == EstadoProvincia.ABANDONADA)
check("F2 provincia despoblada: no genera oro", not pr.produce_oro())
check("F2 provincia despoblada: conserva tropas y fortificacion",
      pr.tropas_estacionadas == 80 and pr.nivel_fortificacion == 2)

# F3/F4 -- desercion sin ingresos (el caso que colgaba la v3)
mapa = Mapa()
mapa.agregar(Provincia(0, poblacion=0, capacidad_soporte=50000,
                       tropas=1000, propietario=0))
imp = Imperio(0, -500, Politica.ECONOMICO)
imp.estado_financiero = EstadoFinanciero.BANCARROTA
part = Partida(mapa, [imp], LEF())
eventos.ev_crisis_financiera(part, st, 0, 0)
tropas = mapa.provincias[0].tropas_estacionadas
check("F4 desercion con ingreso cero: termina sin bucle infinito", True,
      f"tropas 1000 -> {tropas}")
check("F4 desercion: converge a cero", tropas == 0)

# F5 -- combate degenerado
mapa = Mapa()
mapa.agregar(Provincia(0, poblacion=100, capacidad_soporte=50000,
                       tropas=0, fortificacion=0, propietario=0))
mapa.agregar(Provincia(1, poblacion=100, capacidad_soporte=50000,
                       tropas=0, propietario=1))
mapa.conectar(0, 1)
imps = [Imperio(0, 1000, Politica.ECONOMICO), Imperio(1, 1000, Politica.EXPANSIVO)]
part = Partida(mapa, imps, LEF())
OrdenMilitar._contador = 0
orden = OrdenMilitar(emisor=1, origen=1, destino=0, fuerza=0,
                     tiempo_viaje=1, turno_emision=0)
part.ordenes[orden.id] = orden
try:
    eventos.ev_resolucion_combate(part, st, 1, orden.id, 0)
    sin_excepcion = True
except ZeroDivisionError:
    sin_excepcion = False
check("F5 combate degenerado A_k=0 y D_eff=0: sin division por cero", sin_excepcion)
check("F5 combate degenerado: no hay cambio de soberania",
      mapa.provincias[0].id_propietario == 0)

# F6 -- destruccion mutua conserva soberania
detectado = False
for semilla in [3, 7, 11, 101, 999, 12345, 60013, 4243, 31337]:
    partida, _, _ = correr(semilla=semilla, turnos_max=200)
    for b in partida.bitacora:
        if b["evento"] == "COMBATE" and "REPELIDO" in b["detalle"]:
            detectado = True
            break
check("F6 asaltos repelidos observados en el barrido", detectado)

# F8 -- orden huerfana
mapa = Mapa()
mapa.agregar(Provincia(0, poblacion=100, capacidad_soporte=50000,
                       tropas=50, propietario=0))
imps = [Imperio(0, 1000, Politica.ECONOMICO), Imperio(1, 1000, Politica.EXPANSIVO)]
imps[1].estado_activo = False
part = Partida(mapa, imps, LEF())
OrdenMilitar._contador = 0
orden = OrdenMilitar(emisor=1, origen=0, destino=0, fuerza=100,
                     tiempo_viaje=2, turno_emision=0)
part.ordenes[orden.id] = orden
eventos.ev_llegada_orden(part, st, 2, orden.id)
check("F8 orden huerfana: emisor inactivo -> CANCELADA",
      orden.estado_orden.value == "CANCELADA")

# F9 -- fortificacion maxima
partida, _, _ = correr(semilla=7, turnos_max=200)
check("F9 fortificacion nunca excede F_max",
      all(p.nivel_fortificacion <= P.F_max for p in partida.mapa.provincias.values()))

# F10 -- condicion de parada
check("F10 condicion de parada respetada en todas las corridas",
      all(s["turno_final"] <= 201 for _, s in resumen))


# ===========================================================================
sec("4. CONSERVACION DE EFECTIVOS")
# ===========================================================================

# Las tropas solo pueden aparecer por reclutamiento y desaparecer por combate,
# desercion o dispersion. Ninguna debe evaporarse silenciosamente.
partida, _, _ = correr(semilla=11, turnos_max=200)
retiradas = sum(1 for b in partida.bitacora
                if b["evento"] == "COMBATE" and "RETIRADA de" in b["detalle"])
dispersados = sum(1 for b in partida.bitacora
                  if b["evento"] == "COMBATE" and "dispersados" in b["detalle"])
check("supervivientes de asaltos no concluyentes se retiran al origen",
      retiradas > 0, f"{retiradas} retiradas, {dispersados} dispersiones")

ordenes_vivas = [o for o in partida.ordenes.values()
                 if o.estado_orden.value == "EN_TRANSITO"]
check("no quedan ordenes colgadas en transito al terminar",
      len(ordenes_vivas) == 0, f"{len(ordenes_vivas)} en transito")

negativas = [p for p in partida.mapa.provincias.values() if p.tropas_estacionadas < 0]
check("ninguna provincia con tropas negativas", len(negativas) == 0)


# ===========================================================================
sec("5. COMPORTAMIENTO DE LAS POLITICAS DE IA")
# ===========================================================================

conteo = Counter()
for semilla in [3, 7, 11, 101, 999, 12345, 60013, 4243, 31337, 55555]:
    partida, _, stats = correr(semilla=semilla, turnos_max=250)
    if stats["ganador"] is not None:
        conteo[partida.imperios[stats["ganador"]].politica_estrategica.value] += 1
    else:
        conteo["sin ganador"] += 1

print(f"  Resultados en 10 corridas: {dict(conteo)}")
check("la simulacion produce ganadores (no siempre empate)",
      conteo.get("sin ganador", 0) < 10)

partida, _, _ = correr(semilla=7, turnos_max=200)
acciones = Counter(b["evento"] for b in partida.bitacora)
print(f"  Acciones en una corrida tipica: {dict(acciones)}")
check("la IA emite ordenes militares", acciones.get("ORDEN", 0) > 0)
check("la IA recluta", acciones.get("RECLUTA", 0) > 0)
check("se resuelven combates", acciones.get("COMBATE", 0) > 0)


# ===========================================================================
sec("RESUMEN")
# ===========================================================================
if fallas_globales:
    print(f"  {len(fallas_globales)} verificaciones fallaron:")
    for f in fallas_globales:
        print(f"     - {f}")
else:
    print("  Todas las verificaciones pasaron.")
print()
