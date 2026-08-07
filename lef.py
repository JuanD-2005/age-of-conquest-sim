"""
Lista de Eventos Futuros (LEF) y reloj de simulacion -- Seccion 3.3.

Cola de prioridad sobre la clave compuesta (turno, prioridad, secuencia).

El tercer campo NO es decorativo: sin un contador monotono, dos eventos con
el mismo turno y la misma prioridad quedarian ordenados por detalles internos
de la estructura de datos, y la simulacion dejaria de ser reproducible aun
con la misma semilla. Con 'secuencia' el desempate final es FIFO determinista.
"""

import heapq
from enum import IntEnum


class TipoEvento(IntEnum):
    """El valor entero ES la prioridad de desempate (menor = primero).

    Justificacion del orden (Seccion 3.3):
      - CrisisFinanciera primero: la desercion altera S_{j,t}, entrada del combate.
      - Combate antes que LlegadaOrden: refuerzos que llegan el mismo turno no
        participan en una batalla ya iniciada.
      - InicioTurno despues: cierra el turno y reprograma el siguiente.
    """
    CRISIS_FINANCIERA = 0
    RESOLUCION_COMBATE = 1
    LLEGADA_ORDEN = 2
    INICIO_TURNO = 3
    FIN_SIMULACION = 4


class Evento:
    def __init__(self, tipo, turno, **datos):
        self.tipo = tipo
        self.turno = turno
        self.datos = datos

    def __repr__(self):
        return f"Ev({self.tipo.name}, t={self.turno}, {self.datos})"


class LEF:
    """Lista de Eventos Futuros."""

    def __init__(self):
        self._heap = []
        self._secuencia = 0
        self.n_encolados = 0
        self.n_procesados = 0

    def encolar(self, tipo, turno, **datos):
        if turno < 0:
            raise ValueError(f"turno negativo: {turno}")
        self._secuencia += 1
        self.n_encolados += 1
        evento = Evento(tipo, turno, **datos)
        heapq.heappush(self._heap, (turno, int(tipo), self._secuencia, evento))
        return evento

    def extraer_minimo(self):
        if not self._heap:
            return None
        self.n_procesados += 1
        return heapq.heappop(self._heap)[3]

    def vacia(self):
        return len(self._heap) == 0

    def purgar(self):
        """Vacia la LEF. Se usa al disparar Ev_FinSimulacion."""
        self._heap.clear()

    def __len__(self):
        return len(self._heap)
