"""
Visualizacion de una corrida (semilla 7, reproducible) para la presentacion.

Exporta la bitacora completa a CSV y grafica tres series de tiempo que la
bitacora no da directamente (es un log de eventos, no una serie de estado):
oro por imperio, numero de provincias por imperio y poblacion total del mapa.

Para obtener esas series se re-corre la partida con un bucle identico al de
simulacion.bucle_de_simulacion (mismos MANEJADORES, mismo orden), agregando
solo un observador que toma una foto del estado al inicio de cada turno --
justo cuando se procesa Ev_InicioTurno, antes de que ese turno lo mute. Esto
corresponde a la notacion E_{i,t}, P_{j,t} del documento: el estado "en el
turno t", no a mitad de mutacion. No se modifica simulacion.py: este es un
observador externo de solo lectura sobre las mismas entidades.

Script de analisis -- puede depender de matplotlib (el motor en si,
entidades.py/eventos.py/simulacion.py/rng.py, sigue siendo stdlib-only).
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from entidades import EstadoPartida, Parametros
from lef import TipoEvento
from rng import BancoDeStreams
from simulacion import construir_escenario, MANEJADORES
import eventos

SEMILLA = 7
TURNOS_MAX = 200
MAX_EVENTOS = 200_000   # misma cota de seguridad que bucle_de_simulacion

DIR_RESULTADOS = "resultados"
DIR_FIGURAS = os.path.join(DIR_RESULTADOS, "figuras")
CSV_BITACORA = os.path.join(DIR_RESULTADOS, "bitacora_semilla7.csv")
CSV_HISTORIAL = os.path.join(DIR_RESULTADOS, "historial_semilla7.csv")


def correr_instrumentado(semilla=SEMILLA, turnos_max=TURNOS_MAX):
    """Corre una partida y devuelve (partida, historial) donde historial es
    una lista de snapshots {turno, poblacion_total, oro_impX, provincias_impX}
    tomados al inicio de cada Ev_InicioTurno.
    """
    Parametros.T_max = turnos_max
    partida = construir_escenario()
    streams = BancoDeStreams(semilla_maestra=semilla)
    historial = []

    def snapshot(turno):
        mapa = partida.mapa
        fila = {"turno": turno,
                "poblacion_total": sum(p.poblacion for p in mapa.provincias.values())}
        for imp in partida.imperios.values():
            fila[f"oro_imp{imp.id}"] = imp.oro_disponible
            fila[f"provincias_imp{imp.id}"] = len(imp.provincias(mapa))
        historial.append(fila)

    partida.lef.encolar(TipoEvento.INICIO_TURNO, 0)
    n_eventos = 0
    while partida.estado_partida == EstadoPartida.EN_CURSO and not partida.lef.vacia():
        evento = partida.lef.extraer_minimo()
        if evento is None:
            break
        partida.reloj_simulacion = evento.turno
        if evento.tipo == TipoEvento.INICIO_TURNO:
            snapshot(evento.turno)
        MANEJADORES[evento.tipo](partida, streams, evento)
        n_eventos += 1
        eventos.evaluar_condicion_victoria(partida, evento.turno)
        if n_eventos >= MAX_EVENTOS:
            break

    return partida, historial


# ---------------------------------------------------------------------------
# Exportacion a CSV
# ---------------------------------------------------------------------------

def exportar_bitacora(partida, ruta):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=["turno", "evento", "detalle"])
        escritor.writeheader()
        escritor.writerows(partida.bitacora)


def exportar_historial(historial, ruta):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    campos = sorted({campo for fila in historial for campo in fila})
    campos.remove("turno")
    campos = ["turno"] + campos
    with open(ruta, "w", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(historial)


# ---------------------------------------------------------------------------
# Graficas
# ---------------------------------------------------------------------------

def graficar(historial, partida, dir_figuras):
    os.makedirs(dir_figuras, exist_ok=True)
    turnos = [fila["turno"] for fila in historial]
    ids_imperios = sorted(partida.imperios)

    # 1. Oro por imperio
    fig, ax = plt.subplots(figsize=(9, 5))
    for i in ids_imperios:
        politica = partida.imperios[i].politica_estrategica.value
        ax.plot(turnos, [fila[f"oro_imp{i}"] for fila in historial],
                label=f"imperio {i} ({politica})")
    ax.set_xlabel("turno")
    ax.set_ylabel("oro disponible")
    ax.set_title(f"Oro por imperio -- semilla {SEMILLA}")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(dir_figuras, "oro_por_imperio.png"), dpi=120)
    plt.close(fig)

    # 2. Provincias por imperio
    fig, ax = plt.subplots(figsize=(9, 5))
    for i in ids_imperios:
        politica = partida.imperios[i].politica_estrategica.value
        ax.step(turnos, [fila[f"provincias_imp{i}"] for fila in historial],
                where="post", label=f"imperio {i} ({politica})")
    ax.set_xlabel("turno")
    ax.set_ylabel("numero de provincias")
    ax.set_title(f"Provincias por imperio -- semilla {SEMILLA}")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(dir_figuras, "provincias_por_imperio.png"), dpi=120)
    plt.close(fig)

    # 3. Poblacion total del mapa
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(turnos, [fila["poblacion_total"] for fila in historial], color="darkgreen")
    ax.set_xlabel("turno")
    ax.set_ylabel("poblacion total (habitantes)")
    ax.set_title(f"Poblacion total del mapa -- semilla {SEMILLA}")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(dir_figuras, "poblacion_total.png"), dpi=120)
    plt.close(fig)


def main():
    partida, historial = correr_instrumentado()

    exportar_bitacora(partida, CSV_BITACORA)
    exportar_historial(historial, CSV_HISTORIAL)
    graficar(historial, partida, DIR_FIGURAS)

    print(f"Partida semilla {SEMILLA}: turno final "
          f"{partida.reloj_simulacion}, ganador={partida.ganador}")
    print(f"Bitacora ({len(partida.bitacora)} eventos) -> {CSV_BITACORA}")
    print(f"Historial ({len(historial)} turnos) -> {CSV_HISTORIAL}")
    print(f"Figuras -> {DIR_FIGURAS}/"
          f"{{oro_por_imperio,provincias_por_imperio,poblacion_total}}.png")


if __name__ == "__main__":
    main()
