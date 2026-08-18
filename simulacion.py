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


def procesar_siguiente_evento(partida, streams, chequear_invariantes=True):
    """Extrae y procesa UN evento de la LEF -- cuerpo del bucle de la Seccion 3.3.

    Aislado en su propia funcion para que el bucle completo
    (`bucle_de_simulacion`) y el avance paso a paso de la interfaz de consola
    (`main.py`) compartan exactamente la misma logica: extraer el minimo,
    mover el reloj, despachar el manejador, verificar invariantes y evaluar
    la condicion de victoria. Duplicar este cuerpo seria arriesgar que la
    corrida interactiva y la automatica dejen de ser la misma simulacion.

    Devuelve (evento, fallas). (None, []) si no hay nada mas que procesar.
    """
    if partida.estado_partida != EstadoPartida.EN_CURSO or partida.lef.vacia():
        return None, []

    evento = partida.lef.extraer_minimo()
    if evento is None:
        return None, []

    partida.reloj_simulacion = evento.turno
    MANEJADORES[evento.tipo](partida, streams, evento)

    fallas = verificar_invariantes(partida) if chequear_invariantes else []

    eventos.evaluar_condicion_victoria(partida, evento.turno)

    return evento, fallas


def bucle_de_simulacion(partida, streams, chequear_invariantes=True,
                        max_eventos=200000):
    """Motor de eventos discretos. Devuelve estadisticas de la corrida."""
    violaciones = []
    n_eventos = 0
    orden_temporal_ok = True
    ultimo_turno = -1

    partida.lef.encolar(TipoEvento.INICIO_TURNO, 0)

    while partida.estado_partida == EstadoPartida.EN_CURSO and not partida.lef.vacia():
        evento, fallas = procesar_siguiente_evento(
            partida, streams, chequear_invariantes)
        if evento is None:
            break

        # El reloj nunca debe retroceder. Se compara contra el turno previo,
        # que sigue siendo el de la iteracion anterior en este punto.
        if evento.turno < ultimo_turno:
            orden_temporal_ok = False
        ultimo_turno = evento.turno

        n_eventos += 1

        if fallas:
            violaciones.append((evento.turno, evento.tipo.name, fallas))

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

def construir_escenario(n_imperios=3, provs_por_imperio=3,
                        oro_inicial=2000, tropas_base=100):
    """Mapa en anillo: cada imperio controla un bloque contiguo de provincias.

    La topologia en anillo garantiza que todo imperio tenga exactamente dos
    frentes, lo que ejercita el codigo de conquista sin escenarios triviales.

    `oro_inicial` y `tropas_base` son parametros del escenario, no del modelo
    (los del modelo estan en Parametros, Seccion 1.4). Los valores por defecto
    reproducen exactamente el escenario con el que se validaron las fronteras
    F1-F10, de modo que test_modelo.py no cambia de comportamiento; la
    interfaz de consola los expone para poder configurarlos en la demo.
    """
    mapa = Mapa()
    total = n_imperios * provs_por_imperio
    politicas = [Politica.EXPANSIVO, Politica.DEFENSIVO, Politica.ECONOMICO]
    imperios = []

    for idx in range(n_imperios):
        imperios.append(Imperio(
            id_imperio=idx,
            oro_inicial=oro_inicial,
            politica=politicas[idx % len(politicas)],
        ))

    for j in range(total):
        dueno = j // provs_por_imperio
        mapa.agregar(Provincia(
            id_provincia=j,
            poblacion=8000 + 500 * (j % 5),
            capacidad_soporte=50000,
            tropas=tropas_base + 20 * (j % 4),
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
