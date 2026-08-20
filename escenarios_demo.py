"""
escenarios_demo.py -- Escenarios de validacion puntual para la defensa oral.

Corre escenarios AISLADOS (una sola provincia o una sola batalla, no una
partida completa) y compara dos columnas:

  - "teorico"    : el valor que predicen las ECUACIONES del modelo formal
                   (docs/parcial2_anexo/age_of_conquest_v4.md), calculado en
                   este script de forma independiente al motor.
  - "simulador"  : el valor que produce el motor real (entidades/eventos/
                   simulacion), corriendo el mismo escenario a traves de
                   procesar_siguiente_evento().

IMPORTANTE -- que es y que NO es esta comparacion:
No existen datos instrumentados del juego comercial Age of Conquest a los
que el equipo tenga acceso (Seccion 3.1 del informe). La columna "teorico"
NO es un dato del juego real: es la misma ecuacion evaluada por fuera del
motor, para verificar que el codigo la implementa correctamente. Es el
mismo tipo de validacion de consistencia interna de la Seccion 3.2 del
informe, aplicada escenario por escenario en vez de sobre toda la partida.

Nota sobre las filas de combate: con fuerzas simetricas (A0=S0, misma
fortificacion) el modelo de combate (ecuaciones 7-9, aplicacion cruzada de
p_A/p_D) predice bajas esperadas SIMETRICAS entre atacante y defensor. Este
script lo confirma empiricamente (ver escenario_combate). Si se necesita una
asimetria especifica hay que partir de fuerzas o fortificacion distintas y
declararlo como tal.
"""

import math
import statistics

from entidades import Mapa, Provincia, Imperio, Partida, Parametros, Politica
from lef import LEF, TipoEvento
from rng import BancoDeStreams
from simulacion import procesar_siguiente_evento
from eventos import ev_resolucion_combate
from entidades import OrdenMilitar
from variables import triangular_entero

P = Parametros

ANCHO = 88
SEP = "=" * ANCHO


def _fila(metrica, escenario, teorico, simulador, error, estado):
    print(f"{metrica:<22}{escenario:<28}{teorico!s:<14}{simulador!s:<14}"
          f"{error:<10}{estado}")


def _encabezado(titulo):
    print(f"\n{SEP}\n{titulo}\n{SEP}")
    print(f"{'Metrica':<22}{'Escenario':<28}{'Teorico':<14}{'Simulador':<14}"
          f"{'Error':<10}Estado")
    print("-" * ANCHO)


def _partida_una_provincia(poblacion, capacidad_soporte, tropas=0,
                           politica=Politica.ECONOMICO, oro_inicial=100000):
    """Partida minima: la provincia bajo prueba (imperio 0) + un segundo
    imperio inerte y sin vecinos (imperio 1), solo para que
    evaluar_condicion_victoria() no declare "dominacion territorial" de
    inmediato -- esa condicion dispara con un unico imperio activo, lo que
    terminaria la partida en el turno 0 si solo hubiera un imperio. Sin
    adyacencia entre ambos y con politica ECONOMICO (P_AGRESION=0) no hay
    combate ni interaccion posible entre ellos."""
    mapa = Mapa()
    mapa.agregar(Provincia(id_provincia=0, poblacion=poblacion,
                           capacidad_soporte=capacidad_soporte,
                           tropas=tropas, fortificacion=0, propietario=0))
    mapa.agregar(Provincia(id_provincia=1, poblacion=1, capacidad_soporte=1,
                           tropas=0, fortificacion=0, propietario=1))
    imperio = Imperio(id_imperio=0, oro_inicial=oro_inicial, politica=politica)
    relleno = Imperio(id_imperio=1, oro_inicial=oro_inicial,
                      politica=Politica.ECONOMICO)
    OrdenMilitar._contador = 0
    partida = Partida(mapa, [imperio, relleno], LEF())
    partida.lef.encolar(TipoEvento.INICIO_TURNO, 0)
    return partida


def _correr_n_turnos(partida, streams, n):
    """Procesa exactamente n eventos Ev_InicioTurno (n 'turnos' logicos)."""
    procesados = 0
    while procesados < n:
        evento, fallas = procesar_siguiente_evento(partida, streams,
                                                    chequear_invariantes=True)
        if evento is None:
            break
        assert not fallas, f"invariante violado: {fallas}"
        if evento.tipo == TipoEvento.INICIO_TURNO:
            procesados += 1
    return procesados


# ===========================================================================
# 1. Poblacion (ecuacion 1: crecimiento logistico)
# ===========================================================================

def escenario_poblacion(pob0=10000, capacidad=50000, r=0.05, turnos=5):
    P.r = r
    partida = _partida_una_provincia(poblacion=pob0, capacidad_soporte=capacidad)
    streams = BancoDeStreams(semilla_maestra=7)
    _correr_n_turnos(partida, streams, turnos)
    simulado = partida.mapa.provincias[0].poblacion

    # Teorico: la misma ecuacion 1, en punto flotante (sin el floor() que
    # aplica el motor turno a turno) -- por eso el pequenio error esperado.
    pob = float(pob0)
    for _ in range(turnos):
        pob = min(capacidad, pob + r * pob * (1 - pob / capacidad))
    teorico = round(pob, 1)

    error = abs(simulado - teorico) / teorico
    _fila("Poblacion", f"t={turnos}, Pob0={pob0}, r={r}",
          teorico, simulado, f"{error*100:.2f}%", "Exacta")
    return teorico, simulado


# ===========================================================================
# 2. Recaudacion (ecuacion 2, sobre el snapshot pre-crecimiento del turno)
# ===========================================================================

def escenario_recaudacion(tasa=0.10, n_provincias=3, pob0=8000,
                          capacidad=50000, r=0.05, turnos=5):
    P.I = tasa
    P.r = r
    mapa = Mapa()
    for j in range(n_provincias):
        mapa.agregar(Provincia(id_provincia=j, poblacion=pob0,
                               capacidad_soporte=capacidad,
                               tropas=0, fortificacion=0, propietario=0))
    mapa.agregar(Provincia(id_provincia=n_provincias, poblacion=1,
                           capacidad_soporte=1, tropas=0, fortificacion=0,
                           propietario=1))
    imperio = Imperio(id_imperio=0, oro_inicial=0, politica=Politica.ECONOMICO)
    relleno = Imperio(id_imperio=1, oro_inicial=0, politica=Politica.ECONOMICO)
    OrdenMilitar._contador = 0
    partida = Partida(mapa, [imperio, relleno], LEF())
    partida.lef.encolar(TipoEvento.INICIO_TURNO, 0)
    streams = BancoDeStreams(semilla_maestra=7)

    _correr_n_turnos(partida, streams, turnos - 1)
    oro_antes = imperio.oro_disponible
    _correr_n_turnos(partida, streams, 1)
    oro_despues = imperio.oro_disponible
    # tropas=0 -> gasto de mantenimiento (ecuacion 3) es 0: el delta de oro
    # es exactamente la recaudacion del turno (ecuacion 4), sin mezclarse.
    simulado = round(oro_despues - oro_antes, 1)

    # Teorico: poblacion tras (turnos-1) crecimientos (snapshot con el que
    # se tributa el turno "turnos"), por la ecuacion 1, x n_provincias x I.
    pob = float(pob0)
    for _ in range(turnos - 1):
        pob = min(capacidad, pob + r * pob * (1 - pob / capacidad))
    teorico = round(tasa * pob * n_provincias, 1)

    error = abs(simulado - teorico) / teorico
    _fila("Recaudacion", f"t={turnos}, I={tasa:.0%}, {n_provincias} prov",
          teorico, simulado, f"{error*100:.2f}%", "Exacta")
    return teorico, simulado


# ===========================================================================
# 3-4. Combate (ecuaciones 7-9): bajas de atacante y defensor
# ===========================================================================

def escenario_combate(fuerza_a=10, fuerza_s=10, k_c=0.3, replicas=3000):
    P.k_c = k_c
    bajas_atacante, bajas_defensor = [], []

    for i in range(replicas):
        mapa = Mapa()
        mapa.agregar(Provincia(id_provincia=0, poblacion=1000,
                               capacidad_soporte=50000, tropas=fuerza_s,
                               fortificacion=0, propietario=1))
        imperio_atk = Imperio(id_imperio=0, oro_inicial=0, politica=Politica.EXPANSIVO)
        imperio_def = Imperio(id_imperio=1, oro_inicial=0, politica=Politica.DEFENSIVO)
        OrdenMilitar._contador = 0
        partida = Partida(mapa, [imperio_atk, imperio_def], LEF())
        orden = OrdenMilitar(emisor=0, origen=0, destino=0,
                            fuerza=fuerza_a, tiempo_viaje=0, turno_emision=0)
        partida.ordenes[orden.id] = orden

        streams = BancoDeStreams(semilla_maestra=1 + 2 * i)  # impar, distinta por replica
        ev_resolucion_combate(partida, streams, turno=0,
                              id_orden=orden.id, id_provincia=0)

        prov = mapa.provincias[0]
        bajas_defensor.append(fuerza_s - prov.tropas_estacionadas
                              if prov.id_propietario == 1
                              else fuerza_s)
        # tropas_estacionadas al final == supervivientes (atacante si conquisto,
        # defensor si repelio); las bajas del atacante se leen de la bitacora.
        detalle = partida.bitacora[-1]["detalle"]
        superv_atk = int(detalle.split("superv atk=")[1].split(" ")[0])
        bajas_atacante.append(fuerza_a - superv_atk)

    media_atk = statistics.mean(bajas_atacante)
    std_atk = statistics.pstdev(bajas_atacante)
    media_def = statistics.mean(bajas_defensor)
    std_def = statistics.pstdev(bajas_defensor)

    # Teorico: NO hay forma cerrada simple para el proceso multi-ronda hasta
    # agotamiento (ecuaciones 7-9 iteradas); se usa una corrida Monte Carlo
    # de referencia con mas replicas como aproximacion al valor esperado.
    ref_atk, ref_def = [], []
    for i in range(replicas * 5):
        mapa = Mapa()
        mapa.agregar(Provincia(id_provincia=0, poblacion=1000,
                               capacidad_soporte=50000, tropas=fuerza_s,
                               fortificacion=0, propietario=1))
        imperio_atk = Imperio(id_imperio=0, oro_inicial=0, politica=Politica.EXPANSIVO)
        imperio_def = Imperio(id_imperio=1, oro_inicial=0, politica=Politica.DEFENSIVO)
        OrdenMilitar._contador = 0
        partida = Partida(mapa, [imperio_atk, imperio_def], LEF())
        orden = OrdenMilitar(emisor=0, origen=0, destino=0,
                            fuerza=fuerza_a, tiempo_viaje=0, turno_emision=0)
        partida.ordenes[orden.id] = orden
        streams = BancoDeStreams(semilla_maestra=1 + 2 * (i + replicas))
        ev_resolucion_combate(partida, streams, turno=0,
                              id_orden=orden.id, id_provincia=0)
        prov = mapa.provincias[0]
        ref_def.append(fuerza_s - prov.tropas_estacionadas
                       if prov.id_propietario == 1 else fuerza_s)
        detalle = partida.bitacora[-1]["detalle"]
        superv_atk = int(detalle.split("superv atk=")[1].split(" ")[0])
        ref_atk.append(fuerza_a - superv_atk)

    teorico_atk = round(statistics.mean(ref_atk), 2)
    teorico_def = round(statistics.mean(ref_def), 2)

    error_atk = abs(media_atk - teorico_atk) / teorico_atk if teorico_atk else 0
    error_def = abs(media_def - teorico_def) / teorico_def if teorico_def else 0

    escenario_txt = f"{fuerza_a}v{fuerza_s}, k_c={k_c}"
    _fila("Bajas Atacante", escenario_txt,
          f"{teorico_atk:.2f}", f"{media_atk:.2f} (+/-{std_atk:.1f})",
          f"{error_atk*100:.1f}%", "Estocastica")
    _fila("Bajas Defensor", escenario_txt,
          f"{teorico_def:.2f}", f"{media_def:.2f} (+/-{std_def:.1f})",
          f"{error_def*100:.1f}%", "Estocastica")

    if abs(media_atk - media_def) < max(std_atk, std_def):
        print(f"  Nota: con fuerzas simetricas ({fuerza_a}v{fuerza_s}, misma "
              f"fortificacion) el modelo predice bajas esperadas SIMETRICAS "
              f"entre bandos -- confirmado (diferencia dentro de 1 desv. "
              f"estandar). Si se buscaba una asimetria especifica, hace "
              f"falta partir de fuerzas o fortificacion distintas.")

    return (teorico_atk, media_atk), (teorico_def, media_def)


# ===========================================================================
# 5. Retardo de ordenes (Triangular(a, c, b), ecuacion del tiempo de viaje)
# ===========================================================================

def escenario_retardo(a=1, c=2, b=3, replicas=5000):
    streams = BancoDeStreams(semilla_maestra=9)
    muestras = [triangular_entero(streams["tiempo_viaje"], a, c, b)
               for _ in range(replicas)]
    simulado = round(statistics.mean(muestras), 2)
    teorico = round((a + c + b) / 3, 2)  # media de la Triangular
    error = abs(simulado - teorico) / teorico
    _fila("Retardo Ordenes", f"Triangular(a={a}, c={c}, b={b})",
          teorico, simulado, f"{error*100:.2f}%", "Funcional")
    return teorico, simulado


# ===========================================================================
# 6. Turno de colapso (ecuaciones 3-5: gasto > ingreso -> bancarrota)
# ===========================================================================

def escenario_colapso(oro_inicial=0, tropas=200, pob0=1000, capacidad=50000,
                      tasa=0.02, r=0.05, max_turnos=20):
    P.I = tasa
    P.r = r
    partida = _partida_una_provincia(poblacion=pob0, capacidad_soporte=capacidad,
                                     tropas=tropas, oro_inicial=oro_inicial)
    streams = BancoDeStreams(semilla_maestra=11)
    imperio = partida.imperios[0]

    # Teorico: turno en el que ingreso(t) = I*P_fiscal(t) < gasto = c_m*tropas
    # (tropas constantes, no hay combate en este escenario aislado).
    pob = float(pob0)
    turno_teorico = None
    for t in range(max_turnos):
        ingreso = tasa * pob
        gasto = P.c_m * tropas
        if ingreso < gasto:
            turno_teorico = t
            break
        pob = min(capacidad, pob + r * pob * (1 - pob / capacidad))
    turno_simulado = None
    for t in range(max_turnos):
        _correr_n_turnos(partida, streams, 1)
        if imperio.estado_financiero.name == "BANCARROTA":
            turno_simulado = partida.reloj_simulacion
            break

    error = ("N/A" if turno_teorico is None or turno_simulado is None
             else f"{abs(turno_simulado - turno_teorico)} turno(s)")
    _fila("Turno Colapso", f"Oro0={oro_inicial}, S={tropas}, I={tasa:.0%}",
          turno_teorico, turno_simulado, error, "Rigurosa")
    return turno_teorico, turno_simulado


# ===========================================================================
# Runner
# ===========================================================================

def correr_todos_los_escenarios():
    _encabezado("ESCENARIOS DE VALIDACION PUNTUAL -- Age of Conquest (Parcial III)")
    escenario_poblacion()
    escenario_recaudacion()
    escenario_combate()
    escenario_retardo()
    escenario_colapso()
    print(SEP)
    print("Nota: 'Teorico' = ecuaciones del modelo formal evaluadas por fuera")
    print("del motor (o, en combate, una corrida Monte Carlo de referencia con")
    print("5x mas replicas). NO son datos del juego comercial: el equipo no")
    print("tiene acceso a ese dato (ver Seccion 3.1 del informe).")


# ===========================================================================
# Demo de 5+ fases consecutivas (respaldo no interactivo para la defensa)
#
# Complementa a main.py: si en la defensa conviene no depender de tipear en
# vivo, esta funcion corre una partida real turno a turno y narra cada fase,
# usando exactamente el mismo motor (construir_escenario +
# procesar_siguiente_evento) que main.py y test_modelo.py.
# ===========================================================================

def demo_cinco_fases(semilla=7, n_fases=5):
    from simulacion import construir_escenario

    print(f"\n{SEP}\nDEMO NO INTERACTIVA -- {n_fases} fases consecutivas "
          f"(semilla={semilla})\n{SEP}")
    partida = construir_escenario()
    streams = BancoDeStreams(semilla_maestra=semilla)
    partida.lef.encolar(TipoEvento.INICIO_TURNO, 0)

    fases_completadas = 0
    while fases_completadas < n_fases:
        marca = len(partida.bitacora)
        evento, fallas = procesar_siguiente_evento(partida, streams)
        if evento is None:
            print("  (la partida termino antes de completar las fases pedidas)")
            break
        assert not fallas, f"invariante violado: {fallas}"

        if evento.tipo == TipoEvento.INICIO_TURNO:
            fases_completadas += 1
            print(f"\n--- FASE {fases_completadas} (turno {evento.turno}) ---")
            for imp in partida.imperios.values():
                propias = imp.provincias(partida.mapa)
                oro = imp.oro_disponible
                tropas = sum(p.tropas_estacionadas for p in propias)
                print(f"  imperio {imp.id} ({imp.politica_estrategica.value}): "
                      f"oro={oro:.1f}  provincias={len(propias)}  tropas={tropas}")
            nuevos = partida.bitacora[marca:]
            if nuevos:
                print(f"  eventos de la fase: {len(nuevos)}")

    print(f"\n{n_fases} fases completadas correctamente. "
          f"Turno final del reloj: {partida.reloj_simulacion}.")


if __name__ == "__main__":
    correr_todos_los_escenarios()
    demo_cinco_fases()
