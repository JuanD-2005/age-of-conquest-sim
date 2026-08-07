"""
Motor de simulacion -- Seccion 3.3 (bucleDeSimulacion).

Une la LEF, las entidades, los eventos y el banco de streams.
Verifica los invariantes de la Seccion 4 en cada iteracion si se solicita.
"""

from entidades import (Mapa, Provincia, Imperio, Partida, Parametros,
                       Politica, EstadoPartida, EstadoProvincia, OrdenMilitar)
from lef import LEF, TipoEvento
from rng import BancoDeStreams
import eventos

P = Parametros


# ---------------------------------------------------------------------------
# Invariantes de la Seccion 4
# ---------------------------------------------------------------------------

def verificar_invariantes(partida):
    """Devuelve la lista de invariantes violados. Vacia = estado consistente."""
    fallas = []
    mapa = partida.mapa

    for pr in mapa.provincias.values():
        if not (0 <= pr.poblacion <= pr.capacidad_soporte):
            fallas.append(f"I1 prov{pr.id}: P={pr.poblacion} fuera de [0,{pr.capacidad_soporte}]")
        if not (0 <= pr.nivel_fortificacion <= P.F_max):
            fallas.append(f"I2 prov{pr.id}: F={pr.nivel_fortificacion} fuera de [0,{P.F_max}]")
        if pr.tropas_estacionadas < 0 or not isinstance(pr.tropas_estacionadas, int):
            fallas.append(f"I3 prov{pr.id}: S={pr.tropas_estacionadas} negativo o no entero")
        if pr.poblacion == 0 and pr.estado_provincia != EstadoProvincia.ABANDONADA:
            fallas.append(f"I4 prov{pr.id}: P=0 pero estado={pr.estado_provincia.value}")

    # I5: la particion territorial debe cubrir el mapa exactamente
    suma = sum(len(imp.provincias(mapa)) for imp in partida.imperios.values())
    sin_dueno = sum(1 for pr in mapa.provincias.values() if pr.id_propietario is None)
    if suma + sin_dueno != len(mapa):
        fallas.append(f"I5: suma provs={suma} + sin dueno={sin_dueno} != |mapa|={len(mapa)}")

    # I6: coherencia de estadoActivo
    for imp in partida.imperios.values():
        tiene = len(imp.provincias(mapa)) > 0
        if imp.estado_activo != tiene:
            fallas.append(f"I6 imp{imp.id}: activo={imp.estado_activo} pero provs={tiene}")

    return fallas


# ---------------------------------------------------------------------------
# Bucle principal
# ---------------------------------------------------------------------------

MANEJADORES = {
    TipoEvento.INICIO_TURNO:      lambda p, s, ev: eventos.ev_inicio_turno(p, s, ev.turno),
    TipoEvento.LLEGADA_ORDEN:     lambda p, s, ev: eventos.ev_llegada_orden(p, s, ev.turno, ev.datos["orden"]),
    TipoEvento.RESOLUCION_COMBATE: lambda p, s, ev: eventos.ev_resolucion_combate(p, s, ev.turno, ev.datos["orden"], ev.datos["provincia"]),
    TipoEvento.CRISIS_FINANCIERA: lambda p, s, ev: eventos.ev_crisis_financiera(p, s, ev.turno, ev.datos["imperio"]),
    TipoEvento.FIN_SIMULACION:    lambda p, s, ev: eventos.ev_fin_simulacion(p, s, ev.turno, ev.datos.get("causa", "")),
}


def bucle_de_simulacion(partida, streams, chequear_invariantes=True,
                        max_eventos=200000):
    """Motor de eventos discretos. Devuelve estadisticas de la corrida."""
    violaciones = []
    n_eventos = 0
    orden_temporal_ok = True
    ultimo_turno = -1

    partida.lef.encolar(TipoEvento.INICIO_TURNO, 0)

    while partida.estado_partida == EstadoPartida.EN_CURSO and not partida.lef.vacia():
        evento = partida.lef.extraer_minimo()
        if evento is None:
            break

        # El reloj nunca debe retroceder
        if evento.turno < ultimo_turno:
            orden_temporal_ok = False
        ultimo_turno = evento.turno

        partida.reloj_simulacion = evento.turno
        MANEJADORES[evento.tipo](partida, streams, evento)
        n_eventos += 1

        if chequear_invariantes:
            fallas = verificar_invariantes(partida)
            if fallas:
                violaciones.append((evento.turno, evento.tipo.name, fallas))

        eventos.evaluar_condicion_victoria(partida, evento.turno)

        if n_eventos >= max_eventos:
            partida.registrar(evento.turno, "ABORTO", "max_eventos alcanzado")
            break

    return {
        "eventos_procesados": n_eventos,
        "turno_final": partida.reloj_simulacion,
        "estado": partida.estado_partida.value,
        "ganador": partida.ganador,
        "violaciones_invariantes": violaciones,
        "orden_temporal_monotono": orden_temporal_ok,
        "lef_encolados": partida.lef.n_encolados,
        "lef_procesados": partida.lef.n_procesados,
    }


# ---------------------------------------------------------------------------
# Escenario de prueba
# ---------------------------------------------------------------------------

def construir_escenario(n_imperios=3, provs_por_imperio=3):
    """Mapa en anillo: cada imperio controla un bloque contiguo de provincias.

    La topologia en anillo garantiza que todo imperio tenga exactamente dos
    frentes, lo que ejercita el codigo de conquista sin escenarios triviales.
    """
    mapa = Mapa()
    total = n_imperios * provs_por_imperio
    politicas = [Politica.EXPANSIVO, Politica.DEFENSIVO, Politica.ECONOMICO]
    imperios = []

    for idx in range(n_imperios):
        imperios.append(Imperio(
            id_imperio=idx,
            oro_inicial=2000,
            politica=politicas[idx % len(politicas)],
        ))

    for j in range(total):
        dueno = j // provs_por_imperio
        mapa.agregar(Provincia(
            id_provincia=j,
            poblacion=8000 + 500 * (j % 5),
            capacidad_soporte=50000,
            tropas=100 + 20 * (j % 4),
            fortificacion=j % 3,
            propietario=dueno,
        ))

    for j in range(total):
        mapa.conectar(j, (j + 1) % total)

    OrdenMilitar._contador = 0
    return Partida(mapa, imperios, LEF())


def correr(semilla=7, turnos_max=None, chequear=True, silencioso=False):
    if turnos_max is not None:
        P.T_max = turnos_max
    partida = construir_escenario()
    streams = BancoDeStreams(semilla_maestra=semilla)
    stats = bucle_de_simulacion(partida, streams, chequear_invariantes=chequear)
    if not silencioso:
        return partida, streams, stats
    return partida, streams, stats
