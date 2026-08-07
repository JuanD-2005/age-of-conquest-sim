"""
Entidades del Modelo Conceptual (Parcial I), formalizadas segun v4.

Cada atributo corresponde a un simbolo declarado en la Seccion 1 del
documento. Los nombres de atributo son los del Parcial I; los simbolos
matematicos aparecen en los comentarios para mantener la trazabilidad.
"""

from enum import Enum


# ---------------------------------------------------------------------------
# Enumeraciones de estado
# ---------------------------------------------------------------------------

class EstadoFinanciero(Enum):     # Phi_{i,t}
    SOLVENTE = "SOLVENTE"
    BANCARROTA = "BANCARROTA"


class EstadoProvincia(Enum):      # Omega_{j,t}
    POBLADA = "POBLADA"
    ABANDONADA = "ABANDONADA"


class EstadoOrden(Enum):          # sigma_{k,t}
    EMITIDA = "EMITIDA"
    EN_TRANSITO = "EN_TRANSITO"
    RESUELTA = "RESUELTA"
    CANCELADA = "CANCELADA"


class Politica(Enum):             # pi_i
    EXPANSIVO = "EXPANSIVO"
    DEFENSIVO = "DEFENSIVO"
    ECONOMICO = "ECONOMICO"


class EstadoPartida(Enum):
    EN_CURSO = "EN_CURSO"
    FINALIZADA = "FINALIZADA"


# ---------------------------------------------------------------------------
# Parametros fijos (Seccion 1.4)
# ---------------------------------------------------------------------------

class Parametros:
    I = 0.02          # tasa impositiva          oro/(hab*turno)
    r = 0.05          # tasa de crecimiento      1/turno
    c_m = 0.5         # costo mantenimiento      oro/(sold*turno)
    c_mov = 2.0       # costo movilizacion       oro/soldado
    c_fort = 500.0    # costo fortificacion      oro/nivel
    k_c = 0.3         # letalidad de combate     adimensional
    beta = 0.25       # bono defensivo           adimensional/nivel
    delta = 0.10      # fraccion de desercion    adimensional
    rho_atk = 1.5     # ratio minimo para atacar adimensional
    S_min = 50        # guarnicion minima        soldados
    n_max_des = 200   # cota de iteraciones      iteraciones
    n_rondas_max = 20  # rondas maximas por asalto  rondas
    F_max = 4         # fortificacion maxima     nivel
    T_max = 500       # tiempo maximo            turnos

    # parametros estructurales del tiempo de viaje: (min, moda, max) en turnos
    tau_a, tau_c, tau_b = 1, 2, 5

    # probabilidad de actuar militarmente segun politica
    P_AGRESION = {
        Politica.EXPANSIVO: 0.70,
        Politica.DEFENSIVO: 0.30,
        Politica.ECONOMICO: 0.00,
    }


# ---------------------------------------------------------------------------
# Entidades
# ---------------------------------------------------------------------------

class Provincia:
    """Provincia j. Simbolos: P_{j,t}, S_{j,t}, F_{j,t}, O_{j,t}, Omega_{j,t}."""

    def __init__(self, id_provincia, poblacion, capacidad_soporte,
                 tropas=0, fortificacion=0, propietario=None):
        self.id = id_provincia
        self.poblacion = int(poblacion)              # P_{j,t}
        self.capacidad_soporte = int(capacidad_soporte)  # K_j (estructural)
        self.tropas_estacionadas = int(tropas)       # S_{j,t}
        self.nivel_fortificacion = int(fortificacion)  # F_{j,t}
        self.id_propietario = propietario            # O_{j,t}
        self.estado_provincia = (                    # Omega_{j,t}
            EstadoProvincia.ABANDONADA if poblacion == 0
            else EstadoProvincia.POBLADA
        )
        self.vecinos = set()

    def fuerza_defensiva_efectiva(self):
        """D_eff_{j,t} = S_{j,t} * (1 + beta * F_{j,t})   -- ecuacion 6."""
        return self.tropas_estacionadas * (1 + Parametros.beta * self.nivel_fortificacion)

    def produce_oro(self):
        return self.estado_provincia != EstadoProvincia.ABANDONADA

    def __repr__(self):
        return (f"Prov({self.id}, dueno={self.id_propietario}, "
                f"P={self.poblacion}, S={self.tropas_estacionadas}, "
                f"F={self.nivel_fortificacion})")


class Imperio:
    """Imperio i. Simbolos: E_{i,t}, Phi_{i,t}, Psi_{i,t}, pi_i."""

    def __init__(self, id_imperio, oro_inicial, politica):
        self.id = id_imperio
        self.oro_disponible = float(oro_inicial)      # E_{i,t}
        self.estado_financiero = EstadoFinanciero.SOLVENTE  # Phi_{i,t}
        self.estado_activo = True                     # Psi_{i,t}
        self.politica_estrategica = politica          # pi_i

    def provincias(self, mapa):
        """provs(i): provincias bajo control del imperio i."""
        return [p for p in mapa.provincias.values() if p.id_propietario == self.id]

    def __repr__(self):
        return (f"Imp({self.id}, {self.politica_estrategica.value}, "
                f"oro={self.oro_disponible:.0f}, activo={self.estado_activo})")


class OrdenMilitar:
    """Orden k. Simbolos: A_k, tau_k, L_k, sigma_{k,t}."""

    _contador = 0

    def __init__(self, emisor, origen, destino, fuerza, tiempo_viaje, turno_emision):
        OrdenMilitar._contador += 1
        self.id = OrdenMilitar._contador
        self.emisor = emisor                          # imperio que la emite
        self.origen = origen
        self.destino = destino
        self.fuerza_militar = int(fuerza)             # A_k
        self.tiempo_viaje = int(tiempo_viaje)         # tau_k
        self.turno_llegada = turno_emision + self.tiempo_viaje  # L_k
        self.estado_orden = EstadoOrden.EN_TRANSITO   # sigma_{k,t}

    def __repr__(self):
        return (f"Orden({self.id}, {self.origen}->{self.destino}, "
                f"A={self.fuerza_militar}, L={self.turno_llegada}, "
                f"{self.estado_orden.value})")


class Mapa:
    """mapaGlobal: coleccion de provincias con relacion de adyacencia."""

    def __init__(self):
        self.provincias = {}

    def agregar(self, provincia):
        self.provincias[provincia.id] = provincia

    def conectar(self, id_a, id_b):
        self.provincias[id_a].vecinos.add(id_b)
        self.provincias[id_b].vecinos.add(id_a)

    def fronterizas_de(self, id_imperio):
        """Provincias propias que limitan con territorio ajeno."""
        return [p for p in self.provincias.values()
                if p.id_propietario == id_imperio
                and any(self.provincias[v].id_propietario != id_imperio
                        for v in p.vecinos)]

    def objetivos_de(self, id_imperio):
        """Provincias ajenas adyacentes a territorio propio."""
        objetivos = {}
        for p in self.provincias.values():
            if p.id_propietario != id_imperio:
                continue
        for p in self.provincias.values():
            if p.id_propietario == id_imperio:
                for v in p.vecinos:
                    vecino = self.provincias[v]
                    if vecino.id_propietario != id_imperio:
                        objetivos[v] = vecino
        return list(objetivos.values())

    def __len__(self):
        return len(self.provincias)


class Partida:
    """Estado global de la simulacion. Simbolo: t (relojSimulacion)."""

    def __init__(self, mapa, imperios, lef):
        self.mapa = mapa
        self.imperios = {i.id: i for i in imperios}
        self.lef = lef
        self.reloj_simulacion = 0                     # t
        self.estado_partida = EstadoPartida.EN_CURSO
        self.ordenes = {}
        self.ganador = None
        self.bitacora = []

    def imperios_activos(self):
        return [i for i in self.imperios.values() if i.estado_activo]

    def registrar(self, turno, tipo, detalle):
        self.bitacora.append({"turno": turno, "evento": tipo, "detalle": detalle})
