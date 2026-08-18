"""
Interfaz de consola de Age of Conquest -- requisito del Parcial III.

El enunciado pide "un programa funcional que permita la interaccion basica
por consola para ejecutar al menos cinco fases consecutivas del juego",
"donde se puedan ingresar variables de entrada (ej. numero de tropas, nivel
de impuestos) y el sistema calcule correctamente el estado del siguiente
turno". Este modulo es esa capa de interaccion, y NADA MAS: no reimplementa
nada del modelo.

Todo el calculo lo hacen los modulos ya validados:
  - `simulacion.procesar_siguiente_evento` avanza la simulacion evento a
    evento (Seccion 3.3). Es la MISMA funcion que usa el bucle automatico,
    de modo que una demo interactiva y una corrida de test_modelo.py son la
    misma simulacion, no dos caminos que pueden divergir.
  - `simulacion.construir_escenario` arma el mapa en anillo.
  - `entidades.Parametros` guarda los parametros del modelo (Seccion 1.4);
    la tasa impositiva I se ajusta ahi.
  - `rng.BancoDeStreams` valida la semilla maestra (Seccion 6.2.4).

Sin dependencias externas: solo biblioteca estandar, igual que el motor.

Referencia de secciones: docs/parcial2_anexo/age_of_conquest_v4.md
"""

from entidades import (Parametros, EstadoPartida, EstadoOrden,
                       EstadoProvincia, Politica)
from lef import TipoEvento
from rng import BancoDeStreams
from simulacion import (construir_escenario, procesar_siguiente_evento,
                        verificar_invariantes)

ANCHO = 78
SEP = "=" * ANCHO
SEP_FINO = "-" * ANCHO


# ===========================================================================
# Lectura de entrada con validacion
#
# En la defensa se comparte pantalla y alguien va a teclear mal. Ninguna
# entrada invalida debe abortar el programa con un traceback: se avisa y se
# vuelve a preguntar. EOFError/KeyboardInterrupt se tratan como "salir"
# limpio (p.ej. si la entrada viene redirigida y se agota).
# ===========================================================================

class SalidaSolicitada(Exception):
    """El usuario pidio salir (opcion de menu, Ctrl-C o fin de entrada)."""


def _leer_crudo(mensaje):
    try:
        return input(mensaje)
    except (EOFError, KeyboardInterrupt):
        print()
        raise SalidaSolicitada()


def leer_entero(mensaje, defecto, minimo=None, maximo=None):
    """Entero con valor por defecto (Enter lo acepta) y rango validado."""
    while True:
        crudo = _leer_crudo(f"{mensaje} [{defecto}]: ").strip()
        if crudo == "":
            return defecto
        try:
            valor = int(crudo)
        except ValueError:
            print(f"  -> '{crudo}' no es un numero entero. Intenta de nuevo.")
            continue
        if minimo is not None and valor < minimo:
            print(f"  -> debe ser >= {minimo}.")
            continue
        if maximo is not None and valor > maximo:
            print(f"  -> debe ser <= {maximo}.")
            continue
        return valor


def leer_flotante(mensaje, defecto, minimo=None, maximo=None):
    """Real con valor por defecto y rango validado. Acepta coma decimal."""
    while True:
        crudo = _leer_crudo(f"{mensaje} [{defecto}]: ").strip().replace(",", ".")
        if crudo == "":
            return defecto
        try:
            valor = float(crudo)
        except ValueError:
            print(f"  -> '{crudo}' no es un numero. Intenta de nuevo.")
            continue
        if minimo is not None and valor < minimo:
            print(f"  -> debe ser >= {minimo}.")
            continue
        if maximo is not None and valor > maximo:
            print(f"  -> debe ser <= {maximo}.")
            continue
        return valor


def leer_semilla(mensaje, defecto):
    """Semilla maestra: entera, positiva e IMPAR (Seccion 6.2.4).

    rng.BancoDeStreams rechaza las pares con excepcion, y el cero es punto
    fijo absorbente del generador multiplicativo. Se valida aqui para poder
    explicar el motivo en vez de mostrar un traceback en plena defensa.
    """
    while True:
        crudo = _leer_crudo(f"{mensaje} [{defecto}]: ").strip()
        if crudo == "":
            return defecto
        try:
            valor = int(crudo)
        except ValueError:
            print(f"  -> '{crudo}' no es un numero entero. Intenta de nuevo.")
            continue
        if valor <= 0:
            print("  -> la semilla debe ser positiva y no nula: el cero es un "
                  "punto fijo absorbente del generador (Seccion 6.2.4).")
            continue
        if valor % 2 == 0:
            print(f"  -> {valor} es par. La Unidad III recomienda semillas "
                  f"impares; prueba con {valor + 1} (Seccion 6.2.4).")
            continue
        return valor


def leer_opcion(mensaje, validas):
    """Opcion de menu restringida al conjunto `validas`."""
    while True:
        crudo = _leer_crudo(mensaje).strip().lower()
        if crudo in validas:
            return crudo
        print(f"  -> opcion no valida. Elige una de: {', '.join(sorted(validas))}")


# ===========================================================================
# Formato de salida
#
# Tablas alineadas con f-strings de ancho fijo: sin dependencias externas,
# legible al compartir pantalla.
# ===========================================================================

def titulo(texto):
    print(f"\n{SEP}\n{texto}\n{SEP}")


def mostrar_estado(partida):
    """Resumen por imperio: oro, provincias, tropas, politica y solvencia."""
    mapa = partida.mapa
    print(f"\n  TURNO {partida.reloj_simulacion}"
          f"   |   estado de la partida: {partida.estado_partida.value}")
    print(f"  {'Imp':<4} {'Politica':<11} {'Oro':>10} {'Provs':>6} "
          f"{'Tropas':>7} {'Poblacion':>10}  {'Financiero':<11} Activo")
    print(f"  {SEP_FINO[:74]}")

    for imp in partida.imperios.values():
        propias = imp.provincias(mapa)
        tropas = sum(p.tropas_estacionadas for p in propias)
        poblacion = sum(p.poblacion for p in propias)
        print(f"  {imp.id:<4} {imp.politica_estrategica.value:<11} "
              f"{imp.oro_disponible:>10.1f} {len(propias):>6} "
              f"{tropas:>7} {poblacion:>10}  "
              f"{imp.estado_financiero.value:<11} "
              f"{'si' if imp.estado_activo else 'NO'}")

    en_transito = sum(1 for o in partida.ordenes.values()
                      if o.estado_orden == EstadoOrden.EN_TRANSITO)
    print(f"\n  Ordenes en transito: {en_transito}    "
          f"Eventos en la LEF: {len(partida.lef)}")


def mostrar_eventos(partida, desde_indice):
    """Eventos registrados en la bitacora a partir de un indice dado."""
    nuevos = partida.bitacora[desde_indice:]
    if not nuevos:
        print("\n  (sin eventos registrados en este avance)")
        return
    print(f"\n  Eventos ocurridos ({len(nuevos)}):")
    for registro in nuevos:
        print(f"    t={registro['turno']:<4} [{registro['evento']:<16}] "
              f"{registro['detalle']}")


# ===========================================================================
# Sesion interactiva
# ===========================================================================

class Sesion:
    """Envuelve una partida y expone avance paso a paso.

    No contiene reglas del modelo: delega en procesar_siguiente_evento().
    """

    def __init__(self, config):
        self.config = config
        Parametros.I = config["tasa_impositiva"]
        Parametros.T_max = config["turnos_max"]

        self.partida = construir_escenario(
            n_imperios=config["n_imperios"],
            provs_por_imperio=config["provs_por_imperio"],
            oro_inicial=config["oro_inicial"],
            tropas_base=config["tropas_base"],
        )
        self.streams = BancoDeStreams(semilla_maestra=config["semilla"])
        self.violaciones = []

        # El bucle automatico arranca encolando el turno 0 (Seccion 3.3);
        # en modo interactivo hay que hacerlo una sola vez al iniciar.
        self.partida.lef.encolar(TipoEvento.INICIO_TURNO, 0)

    def terminada(self):
        return (self.partida.estado_partida != EstadoPartida.EN_CURSO
                or self.partida.lef.vacia())

    def avanzar_un_turno(self):
        """Procesa todos los eventos que pertenecen al turno en curso.

        Un "turno" del juego no es un evento sino el conjunto de eventos que
        comparten la marca temporal t: crisis financieras, combates, llegadas
        de ordenes y el propio Ev_InicioTurno (Seccion 3.3). Se procesan
        mientras el proximo evento siga siendo de ese turno; el
        Ev_InicioTurno(t+1) que se encola al final marca la frontera.
        """
        if self.terminada():
            return 0
        turno = self.partida.lef.proximo_turno()
        procesados = 0
        while (not self.terminada()
               and self.partida.lef.proximo_turno() == turno):
            evento, fallas = procesar_siguiente_evento(self.partida, self.streams)
            if evento is None:
                break
            procesados += 1
            if fallas:
                self.violaciones.append((evento.turno, evento.tipo.name, fallas))
        return procesados

    def avanzar_n_turnos(self, n):
        total = 0
        for _ in range(n):
            if self.terminada():
                break
            total += self.avanzar_un_turno()
        return total

    def correr_hasta_fin(self, tope_turnos=10000):
        total = 0
        for _ in range(tope_turnos):
            if self.terminada():
                break
            total += self.avanzar_un_turno()
        return total


# ===========================================================================
# Configuracion del escenario
# ===========================================================================

DEFECTOS = {
    "n_imperios": 3,
    "provs_por_imperio": 3,
    "tropas_base": 100,
    "oro_inicial": 2000,
    "tasa_impositiva": Parametros.I,   # 0.02, Seccion 1.4
    "semilla": 7,
    "turnos_max": 200,
}


def configurar_escenario():
    """Pide los parametros de entrada. Enter en todo = escenario por defecto.

    Los valores por defecto reproducen el escenario con el que se validaron
    las fronteras F1-F10 (test_modelo.py), asi que dar Enter a todo arranca
    una partida ya conocida y verificada.
    """
    titulo("CONFIGURACION DEL ESCENARIO  (Enter = valor por defecto)")

    cfg = dict(DEFECTOS)
    cfg["n_imperios"] = leer_entero(
        "  Numero de imperios", DEFECTOS["n_imperios"], minimo=1, maximo=12)
    cfg["provs_por_imperio"] = leer_entero(
        "  Provincias por imperio", DEFECTOS["provs_por_imperio"],
        minimo=1, maximo=20)
    cfg["tropas_base"] = leer_entero(
        "  Tropas iniciales por provincia", DEFECTOS["tropas_base"],
        minimo=0, maximo=100000)
    cfg["oro_inicial"] = leer_entero(
        "  Oro inicial por imperio", DEFECTOS["oro_inicial"],
        minimo=0, maximo=10000000)
    cfg["tasa_impositiva"] = leer_flotante(
        "  Tasa impositiva I (oro por habitante y turno)",
        DEFECTOS["tasa_impositiva"], minimo=0.0, maximo=10.0)
    cfg["semilla"] = leer_semilla(
        "  Semilla maestra (impar, no nula)", DEFECTOS["semilla"])
    cfg["turnos_max"] = leer_entero(
        "  Turno maximo T_max", DEFECTOS["turnos_max"], minimo=1, maximo=100000)

    print(f"\n  Escenario: {cfg['n_imperios']} imperios x "
          f"{cfg['provs_por_imperio']} provincias "
          f"({cfg['n_imperios'] * cfg['provs_por_imperio']} en total), "
          f"I={cfg['tasa_impositiva']}, semilla={cfg['semilla']}")
    return cfg


# ===========================================================================
# Menu de inspeccion (Seccion 1: variables de estado)
# ===========================================================================

def inspeccionar_provincia(partida):
    ids = sorted(partida.mapa.provincias)
    print(f"\n  Provincias disponibles: {ids[0]}..{ids[-1]}")
    id_prov = leer_entero("  Id de provincia", ids[0],
                          minimo=ids[0], maximo=ids[-1])
    prov = partida.mapa.provincias.get(id_prov)
    if prov is None:
        print("  -> esa provincia no existe.")
        return

    print(f"\n  PROVINCIA {prov.id}")
    print(f"    Propietario (O_j)          : imperio {prov.id_propietario}")
    print(f"    Poblacion  (P_j)           : {prov.poblacion} hab "
          f"(capacidad K_j = {prov.capacidad_soporte})")
    print(f"    Tropas     (S_j)           : {prov.tropas_estacionadas} soldados")
    print(f"    Fortificacion (F_j)        : {prov.nivel_fortificacion} "
          f"/ {Parametros.F_max}")
    print(f"    Estado     (Omega_j)       : {prov.estado_provincia.value}")
    print(f"    Fuerza defensiva efectiva  : {prov.fuerza_defensiva_efectiva():.1f}"
          f"   (D_eff = S*(1+beta*F), ec. 6)")
    print(f"    Produce oro                : "
          f"{'si' if prov.produce_oro() else 'no (abandonada)'}")
    print(f"    Vecinas                    : {sorted(prov.vecinos)}")


def inspeccionar_ordenes(partida):
    en_transito = [o for o in partida.ordenes.values()
                   if o.estado_orden == EstadoOrden.EN_TRANSITO]
    print(f"\n  ORDENES MILITARES EN TRANSITO: {len(en_transito)}")
    if not en_transito:
        print("    (ninguna en vuelo en este momento)")
    else:
        print(f"    {'Id':>4} {'Emisor':>7} {'Origen':>7} {'Destino':>8} "
              f"{'Fuerza':>7} {'Llega en t':>11}")
        for orden in sorted(en_transito, key=lambda o: o.turno_llegada):
            print(f"    {orden.id:>4} {orden.emisor:>7} {orden.origen:>7} "
                  f"{orden.destino:>8} {orden.fuerza_militar:>7} "
                  f"{orden.turno_llegada:>11}")

    # El ciclo de vida completo (Seccion 1.1 / Correccion 16)
    totales = {}
    for orden in partida.ordenes.values():
        clave = orden.estado_orden.value
        totales[clave] = totales.get(clave, 0) + 1
    if totales:
        print(f"\n    Ciclo de vida de las {len(partida.ordenes)} ordenes emitidas: "
              f"{totales}")


def inspeccionar_lef(partida):
    conteo = partida.lef.conteo_por_tipo()
    print(f"\n  LISTA DE EVENTOS FUTUROS: {len(partida.lef)} eventos encolados")
    if not conteo:
        print("    (vacia: la partida termino o no hay nada programado)")
        return
    print(f"    Proximo turno a procesar: {partida.lef.proximo_turno()}")
    print(f"    {'Tipo de evento':<22} {'Prioridad':>10} {'Encolados':>10}")
    for tipo in sorted(conteo, key=lambda t: int(t)):
        print(f"    {tipo.name:<22} {int(tipo):>10} {conteo[tipo]:>10}")
    print(f"\n    Acumulado: {partida.lef.n_encolados} encolados / "
          f"{partida.lef.n_procesados} procesados")


def menu_inspeccion(partida):
    while True:
        print("\n  --- INSPECCIONAR ESTADO ---")
        print("    1) Detalle de una provincia")
        print("    2) Ordenes militares en transito")
        print("    3) Estado de la LEF")
        print("    4) Volver")
        opcion = leer_opcion("  Opcion: ", {"1", "2", "3", "4"})
        if opcion == "1":
            inspeccionar_provincia(partida)
        elif opcion == "2":
            inspeccionar_ordenes(partida)
        elif opcion == "3":
            inspeccionar_lef(partida)
        else:
            return


# ===========================================================================
# Bucle principal de la interfaz
# ===========================================================================

def avanzar_y_reportar(sesion, n_turnos=1, hasta_fin=False):
    """Avanza la simulacion y muestra estado + eventos de lo ocurrido."""
    if sesion.terminada():
        print("\n  La partida ya termino. Usa 'reiniciar' para otra corrida.")
        return

    marca = len(sesion.partida.bitacora)
    if hasta_fin:
        sesion.correr_hasta_fin()
    else:
        sesion.avanzar_n_turnos(n_turnos)

    mostrar_estado(sesion.partida)
    mostrar_eventos(sesion.partida, marca)

    if sesion.violaciones:
        print(f"\n  !! {len(sesion.violaciones)} violaciones de invariantes "
              f"detectadas (Seccion 4)")

    if sesion.terminada():
        ganador = sesion.partida.ganador
        print(f"\n  {SEP_FINO[:74]}")
        if ganador is not None:
            imp = sesion.partida.imperios[ganador]
            print(f"  PARTIDA FINALIZADA en el turno "
                  f"{sesion.partida.reloj_simulacion}: gana el imperio "
                  f"{ganador} ({imp.politica_estrategica.value}) "
                  f"por dominacion territorial.")
        else:
            print(f"  PARTIDA FINALIZADA en el turno "
                  f"{sesion.partida.reloj_simulacion} sin ganador "
                  f"(T_max alcanzado, mas de un imperio activo).")


def menu_principal(sesion):
    while True:
        print(f"\n{SEP_FINO}")
        print(f"  MENU PRINCIPAL   |   turno actual: "
              f"{sesion.partida.reloj_simulacion}   |   "
              f"{'EN CURSO' if not sesion.terminada() else 'FINALIZADA'}")
        print(f"{SEP_FINO}")
        print("    1) Avanzar 1 turno")
        print("    2) Avanzar N turnos")
        print("    3) Correr hasta el final")
        print("    4) Ver estado actual")
        print("    5) Inspeccionar estado (provincia / ordenes / LEF)")
        print("    6) Reiniciar con otra configuracion")
        print("    7) Salir")

        opcion = leer_opcion("  Opcion: ", {"1", "2", "3", "4", "5", "6", "7"})

        if opcion == "1":
            avanzar_y_reportar(sesion, n_turnos=1)
        elif opcion == "2":
            n = leer_entero("  Cuantos turnos avanzar", 5, minimo=1, maximo=10000)
            avanzar_y_reportar(sesion, n_turnos=n)
        elif opcion == "3":
            avanzar_y_reportar(sesion, hasta_fin=True)
        elif opcion == "4":
            mostrar_estado(sesion.partida)
        elif opcion == "5":
            menu_inspeccion(sesion.partida)
        elif opcion == "6":
            return "reiniciar"
        else:
            return "salir"


def main():
    titulo("AGE OF CONQUEST -- SIMULACION DE EVENTOS DISCRETOS")
    print("  Grupo 3 - Ballesteros Maria, Morillo Gustavo, Juan Paredes")
    print("  Modelo formal: docs/parcial2_anexo/age_of_conquest_v4.md")
    print("\n  Toda corrida queda determinada por la semilla maestra:")
    print("  la misma semilla reproduce exactamente la misma partida.")

    try:
        while True:
            config = configurar_escenario()
            sesion = Sesion(config)

            titulo("ESTADO INICIAL (turno 0, antes de procesar eventos)")
            mostrar_estado(sesion.partida)

            if menu_principal(sesion) == "salir":
                break
    except SalidaSolicitada:
        pass

    print("\n  Fin de la sesion. Hasta luego.\n")


if __name__ == "__main__":
    main()
