"""
Manejadores de eventos y logica de decision -- Secciones 3.1, 3.2, 3.4.

Cada procedimiento implementa literalmente el pseudocodigo del documento v4.
Los comentarios marcan la ecuacion o el paso que corresponde a cada bloque.
"""

import math

from entidades import (Parametros, EstadoFinanciero, EstadoProvincia,
                       EstadoOrden, Politica, EstadoPartida, OrdenMilitar)
from lef import TipoEvento
from variables import binomial, triangular_entero

P = Parametros


# ===========================================================================
# Ev_InicioTurno -- Seccion 3.1
# ===========================================================================

def ev_inicio_turno(partida, streams, turno):
    mapa = partida.mapa

    # PASO 1 -- Snapshot fiscal, ANTES de cualquier mutacion.
    # Las ecuaciones 2 y 4 definen la recaudacion sobre P_{j,t}, no P_{j,t+1}.
    pob_fiscal = {j: p.poblacion for j, p in mapa.provincias.items()}

    # PASO 2 -- Fase demografica (ecuaciones 1 y 1b)
    for prov in mapa.provincias.values():
        if prov.estado_provincia == EstadoProvincia.ABANDONADA:
            prov.poblacion = 0
        else:
            crec = P.r * prov.poblacion * (1 - prov.poblacion / prov.capacidad_soporte)
            prov.poblacion = min(prov.capacidad_soporte,
                                 math.floor(prov.poblacion + crec))
            prov.poblacion = max(0, prov.poblacion)
        if prov.poblacion == 0:
            prov.estado_provincia = EstadoProvincia.ABANDONADA

    # PASO 3 -- Recaudacion sobre el snapshot (ecuacion 2)
    ingreso, gasto = {}, {}
    for imp in partida.imperios_activos():
        ingreso[imp.id] = sum(
            P.I * pob_fiscal[prov.id]
            for prov in imp.provincias(mapa)
            if prov.produce_oro()
        )

    # PASO 4 -- Mantenimiento militar (ecuacion 3)
    for imp in partida.imperios_activos():
        gasto[imp.id] = P.c_m * sum(pr.tropas_estacionadas
                                    for pr in imp.provincias(mapa))

    # PASO 5 -- Actualizacion del tesoro (ecuacion 4)
    for imp in partida.imperios_activos():
        imp.oro_disponible += ingreso[imp.id] - gasto[imp.id]

    # PASO 6 -- Estado financiero (ecuacion 5)
    for imp in partida.imperios_activos():
        if imp.oro_disponible < 0:
            imp.estado_financiero = EstadoFinanciero.BANCARROTA
            partida.lef.encolar(TipoEvento.CRISIS_FINANCIERA,
                                turno, imperio=imp.id)
        else:
            imp.estado_financiero = EstadoFinanciero.SOLVENTE

    # PASO 7 -- Decisiones de la IA
    for imp in partida.imperios_activos():
        evaluar_opciones_estocasticas(partida, streams, imp, turno)

    # PASO 8 -- Verificacion de actividad (ecuacion 5b)
    for imp in partida.imperios.values():
        imp.estado_activo = len(imp.provincias(mapa)) > 0

    # PASO 9 -- Auto-reprogramacion ciclica
    if turno + 1 <= P.T_max:
        partida.lef.encolar(TipoEvento.INICIO_TURNO, turno + 1)
    else:
        partida.lef.encolar(TipoEvento.FIN_SIMULACION, turno + 1,
                            causa="T_max alcanzado")


# ===========================================================================
# evaluarOpcionesEstocasticas -- Seccion 3.2
# ===========================================================================

def evaluar_opciones_estocasticas(partida, streams, imperio, turno):
    mapa = partida.mapa

    # Override: la bancarrota anula la agresividad
    if imperio.estado_financiero == EstadoFinanciero.BANCARROTA:
        imperio.politica_estrategica = Politica.ECONOMICO
        return

    # Tirada de agresividad (stream 'decision_ia')
    p_agr = P.P_AGRESION[imperio.politica_estrategica]
    if streams["decision_ia"].u() >= p_agr:
        return

    # Reserva minima: nunca gastar por debajo de un turno de mantenimiento
    propias = imperio.provincias(mapa)
    reserva = P.c_m * sum(pr.tropas_estacionadas for pr in propias)
    presupuesto = imperio.oro_disponible - reserva
    if presupuesto <= 0:
        return

    # --- EXPANSIVO ---------------------------------------------------------
    if imperio.politica_estrategica == Politica.EXPANSIVO:
        objetivos = sorted(mapa.objetivos_de(imperio.id),
                           key=lambda p: p.fuerza_defensiva_efectiva())

        # Fase 1: intentar atacar con lo que ya tiene movilizado
        for destino in objetivos:
            candidatos = [mapa.provincias[v] for v in destino.vecinos
                          if mapa.provincias[v].id_propietario == imperio.id]
            if not candidatos:
                continue
            origen = max(candidatos, key=lambda p: p.tropas_estacionadas)
            disponibles = origen.tropas_estacionadas - P.S_min
            requerido = math.ceil(P.rho_atk * destino.fuerza_defensiva_efectiva())
            requerido = max(1, requerido)
            if disponibles >= requerido and presupuesto >= P.c_mov * requerido:
                emitir_orden(partida, streams, imperio, origen, destino,
                             requerido, turno)
                return

        # Fase 2: acumulacion. Sin esta rama la politica EXPANSIVO queda en
        # deadlock estructural: solo puede atacar con la guarnicion inicial,
        # que nunca crece, y el oro se acumula sin uso indefinidamente.
        # Se recluta en la frontera mas fuerte para converger al umbral rho_atk.
        fronterizas = mapa.fronterizas_de(imperio.id)
        if fronterizas:
            objetivo = max(fronterizas, key=lambda p: p.tropas_estacionadas)
            lote = reclutar(imperio, objetivo, presupuesto)
            if lote > 0:
                partida.registrar(turno, "RECLUTA",
                                  f"imp{imperio.id} +{lote} en prov{objetivo.id} "
                                  f"(acumulacion ofensiva)")

    # --- DEFENSIVO ---------------------------------------------------------
    elif imperio.politica_estrategica == Politica.DEFENSIVO:
        debiles = [pr for pr in propias if pr.tropas_estacionadas < P.S_min]
        if debiles:
            objetivo = min(debiles, key=lambda p: p.tropas_estacionadas)
            faltante = P.S_min - objetivo.tropas_estacionadas
            if presupuesto >= P.c_mov * faltante:
                objetivo.tropas_estacionadas += faltante
                imperio.oro_disponible -= P.c_mov * faltante
                partida.registrar(turno, "RECLUTA",
                                  f"imp{imperio.id} +{faltante} en prov{objetivo.id}")
            return

        fronterizas = [pr for pr in mapa.fronterizas_de(imperio.id)
                       if pr.nivel_fortificacion < P.F_max]
        if fronterizas and presupuesto >= P.c_fort:
            objetivo = min(fronterizas, key=lambda p: p.nivel_fortificacion)
            objetivo.nivel_fortificacion += 1
            imperio.oro_disponible -= P.c_fort
            partida.registrar(turno, "FORTIFICA",
                              f"imp{imperio.id} prov{objetivo.id} "
                              f"-> F={objetivo.nivel_fortificacion}")
            return

        # Excedente con fortificaciones al maximo: engrosar guarniciones.
        # Sin esta rama el imperio DEFENSIVO tambien acumula oro sin uso.
        todas_frontera = mapa.fronterizas_de(imperio.id)
        if todas_frontera:
            objetivo = min(todas_frontera, key=lambda p: p.tropas_estacionadas)
            lote = reclutar(imperio, objetivo, presupuesto)
            if lote > 0:
                partida.registrar(turno, "RECLUTA",
                                  f"imp{imperio.id} +{lote} en prov{objetivo.id} "
                                  f"(refuerzo de frontera)")

    # --- ECONOMICO ---------------------------------------------------------
    # No emite ordenes militares. Acumula reservas.
    return


def reclutar(imperio, provincia, presupuesto, fraccion=0.5):
    """Recluta soldados en una provincia con cargo al presupuesto disponible.

    Se gasta a lo sumo 'fraccion' del presupuesto por turno para que el
    imperio conserve capacidad de reaccion en turnos posteriores en lugar
    de vaciar el tesoro en una sola leva.
    """
    lote = int(presupuesto * fraccion / Parametros.c_mov)
    if lote <= 0:
        return 0
    provincia.tropas_estacionadas += lote
    imperio.oro_disponible -= Parametros.c_mov * lote
    return lote


# ===========================================================================
# Emision y llegada de ordenes -- Seccion 3.4
# ===========================================================================

def emitir_orden(partida, streams, imperio, origen, destino, fuerza, turno):
    tau = triangular_entero(streams["tiempo_viaje"], P.tau_a, P.tau_c, P.tau_b)

    orden = OrdenMilitar(emisor=imperio.id, origen=origen.id,
                         destino=destino.id, fuerza=fuerza,
                         tiempo_viaje=tau, turno_emision=turno)

    origen.tropas_estacionadas -= fuerza
    imperio.oro_disponible -= P.c_mov * fuerza

    partida.ordenes[orden.id] = orden
    partida.lef.encolar(TipoEvento.LLEGADA_ORDEN, orden.turno_llegada,
                        orden=orden.id)
    partida.registrar(turno, "ORDEN",
                      f"imp{imperio.id} prov{origen.id}->prov{destino.id} "
                      f"A={fuerza} tau={tau}")
    return orden


def ev_llegada_orden(partida, streams, turno, id_orden):
    orden = partida.ordenes[id_orden]

    if orden.estado_orden != EstadoOrden.EN_TRANSITO:
        return

    emisor = partida.imperios[orden.emisor]
    if not emisor.estado_activo:
        orden.estado_orden = EstadoOrden.CANCELADA
        partida.registrar(turno, "ORDEN_CANCELADA",
                          f"orden{orden.id}: emisor imp{emisor.id} inactivo")
        return

    destino = partida.mapa.provincias[orden.destino]

    if destino.id_propietario == orden.emisor:
        # Refuerzo: el destino ya es propio
        destino.tropas_estacionadas += orden.fuerza_militar
        orden.estado_orden = EstadoOrden.RESUELTA
        partida.registrar(turno, "REFUERZO",
                          f"prov{destino.id} +{orden.fuerza_militar}")
    else:
        # Invasion: se agenda el combate en este mismo turno
        orden.estado_orden = EstadoOrden.RESUELTA
        partida.lef.encolar(TipoEvento.RESOLUCION_COMBATE, turno,
                            orden=orden.id, provincia=destino.id)


# ===========================================================================
# Ev_ResolucionCombate -- Seccion 2.5
# ===========================================================================

def ev_resolucion_combate(partida, streams, turno, id_orden, id_provincia):
    orden = partida.ordenes[id_orden]
    prov = partida.mapa.provincias[id_provincia]
    emisor = partida.imperios[orden.emisor]

    A_k = orden.fuerza_militar
    S_inicial = prov.tropas_estacionadas
    A_actual, S_actual = A_k, S_inicial
    propietario_previo = prov.id_propietario
    rondas = 0

    # El asalto se resuelve por RONDAS dentro del mismo evento.
    #
    # Con un unico intercambio, la ecuacion 8 elimina en promedio una
    # fraccion k_c*D/(A+D) del defensor (~15% con k_c=0.3), de modo que la
    # condicion de conquista S_{j,t+1}=0 de la ecuacion 10 es practicamente
    # inalcanzable: se verifico empiricamente que 16 combates producian 0
    # conquistas. El asalto se itera hasta que un bando se agota o hasta
    # n_rondas_max, que acota el costo computacional del evento.
    while rondas < P.n_rondas_max and A_actual > 0 and S_actual > 0:
        D_eff = S_actual * (1 + P.beta * prov.nivel_fortificacion)

        # Ecuacion 7: caso degenerado resuelto explicitamente
        if A_actual + D_eff == 0:
            break
        p_A = P.k_c * A_actual / (A_actual + D_eff)
        p_D = P.k_c * D_eff / (A_actual + D_eff)

        assert 0.0 <= p_A <= P.k_c + 1e-12, f"p_A fuera de rango: {p_A}"
        assert 0.0 <= p_D <= P.k_c + 1e-12, f"p_D fuera de rango: {p_D}"

        # Ecuacion 8: bajas simultaneas sobre los efectivos PREVIOS
        bajas_defensor = binomial(streams["combate_atacante"], S_actual, p_A)
        bajas_atacante = binomial(streams["combate_defensor"], A_actual, p_D)

        # Ecuacion 9
        S_actual = max(0, S_actual - bajas_defensor)
        A_actual = max(0, A_actual - bajas_atacante)
        rondas += 1

    prov.tropas_estacionadas = S_actual

    # Ecuacion 10: regla de conquista
    if S_actual == 0 and A_actual > 0:
        prov.id_propietario = orden.emisor
        prov.tropas_estacionadas = A_actual
        prov.nivel_fortificacion = 0   # las fortificaciones caen en el asalto
        resultado = f"CONQUISTA por imp{orden.emisor}"
    elif A_actual == 0:
        resultado = "ASALTO REPELIDO"
    else:
        # Asalto no concluyente: los supervivientes se retiran al origen.
        #
        # La ecuacion 10 de la v3 solo definia el caso de conquista y dejaba
        # A'_k indefinido en el resto. En la implementacion inicial esos
        # soldados desaparecian del sistema: fuga silenciosa que rompe la
        # conservacion de efectivos. La retirada cierra el balance.
        origen = partida.mapa.provincias[orden.origen]
        if origen.id_propietario == orden.emisor:
            origen.tropas_estacionadas += A_actual
            resultado = f"RETIRADA de {A_actual} a prov{origen.id}"
        else:
            resultado = f"RETIRADA IMPOSIBLE, {A_actual} dispersados"

    partida.registrar(
        turno, "COMBATE",
        f"prov{prov.id} (imp{propietario_previo}) A={A_k} vs S={S_inicial} "
        f"| {rondas} rondas | superv atk={A_actual} def={S_actual} | {resultado}"
    )

    for imp in partida.imperios.values():
        imp.estado_activo = len(imp.provincias(partida.mapa)) > 0


# ===========================================================================
# Ev_CrisisFinanciera -- Seccion 2.6
# ===========================================================================

def ev_crisis_financiera(partida, streams, turno, id_imperio):
    imperio = partida.imperios[id_imperio]
    if not imperio.estado_activo:
        return

    propias = imperio.provincias(partida.mapa)
    ingreso = sum(P.I * pr.poblacion for pr in propias if pr.produce_oro())
    tropas_iniciales = sum(pr.tropas_estacionadas for pr in propias)

    n = 0
    while n < P.n_max_des:
        total = sum(pr.tropas_estacionadas for pr in propias)
        if total == 0 or P.c_m * total <= ingreso:
            break
        for pr in propias:
            # Ecuacion 11: funcion piso -> decrecimiento estricto, termina
            pr.tropas_estacionadas = math.floor(pr.tropas_estacionadas * (1 - P.delta))
        n += 1

    desertores = tropas_iniciales - sum(pr.tropas_estacionadas for pr in propias)
    if desertores > 0:
        partida.registrar(turno, "DESERCION",
                          f"imp{imperio.id} -{desertores} soldados "
                          f"en {n} iteraciones")


# ===========================================================================
# Ev_FinSimulacion
# ===========================================================================

def ev_fin_simulacion(partida, streams, turno, causa=""):
    partida.estado_partida = EstadoPartida.FINALIZADA
    activos = partida.imperios_activos()
    partida.ganador = activos[0].id if len(activos) == 1 else None

    # Purgar la LEF deja sin procesar los Ev_LlegadaOrden pendientes, de modo
    # que sus ordenes quedarian con sigma = EN_TRANSITO: un estado NO TERMINAL
    # al cierre de la partida. El ciclo de vida declarado en la Seccion 1.1
    # exige que toda orden acabe en RESUELTA o CANCELADA.
    en_vuelo = 0
    for orden in partida.ordenes.values():
        if orden.estado_orden == EstadoOrden.EN_TRANSITO:
            orden.estado_orden = EstadoOrden.CANCELADA
            en_vuelo += 1

    partida.lef.purgar()
    detalle = causa or "sin causa declarada"
    if en_vuelo:
        detalle += f" | {en_vuelo} ordenes en vuelo canceladas"
    partida.registrar(turno, "FIN", detalle)


def evaluar_condicion_victoria(partida, turno):
    """Dominacion territorial total: un unico imperio activo."""
    activos = partida.imperios_activos()
    if len(activos) <= 1 and partida.estado_partida == EstadoPartida.EN_CURSO:
        partida.lef.encolar(TipoEvento.FIN_SIMULACION, turno,
                            causa="dominacion territorial")
        return True
    return False
