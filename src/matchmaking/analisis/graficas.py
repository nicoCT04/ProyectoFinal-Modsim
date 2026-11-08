"""
Gráficas mínimas de los experimentos finales (R4, Parte 7 del enunciado).

    python -m src.matchmaking.analisis.graficas

Guarda tres figuras en results/figuras/:

  cola_en_el_tiempo.png     tamaño de la cola durante un día, para tres políticas
  frente_pareto.png         candidatas y referencias en el espacio (espera, diferencia), evaluadas
                            las nueve en las mismas condiciones en que buscó NSGA-II (escenario
                            `optimizacion`, semillas 1000-1002), sobre el frente explorado
  sensibilidad_demanda.png  espera media (IC95 %) de tres políticas en los cuatro escenarios del
                            estudio, con results/experimentos_resumen.csv (30 semillas nuevas)

La nube de fondo de `frente_pareto.png` y el resumen de `sensibilidad_demanda.png` requieren haber
corrido antes optimizacion/nsga2.py, optimizacion/aleatoria.py y experimentos/ejecutar.py.
"""

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from ..optimizacion.problema import cargar_config, evaluar
from ..simulacion.escenarios import RAIZ, cargar
from ..simulacion.motor import simular

RESULTADOS = RAIZ / "results"
FIGURAS = RESULTADOS / "figuras"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECUNDARIA = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AZUL, NARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
NUBE_NSGA, NUBE_ALEATORIA = "#b7d3f6", "#c3c2b7"

FIJAS = ("fija_20", "fija_40", "fija_60")
CANDIDATAS = ("nsga_codo", "nsga_menor_espera", "nsga_intermedia", "nsga_menor_dif", "aleatoria_mejor")

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_SECUNDARIA,
    "text.color": INK, "xtick.color": INK_MUTED, "ytick.color": INK_MUTED,
    "grid.color": GRID, "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
})


def _leer_csv(ruta):
    with open(ruta, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _despejar(ax):
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.grid(axis="y", linewidth=0.8, alpha=0.6)
    ax.set_axisbelow(True)


def _guardar(fig, ruta_salida):
    FIGURAS.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(ruta_salida, dpi=150)
    plt.close(fig)


def grafica_cola_en_el_tiempo(ruta_salida=FIGURAS / "cola_en_el_tiempo.png", semilla=5000):
    """Tamaño de la cola durante un día (escenario base): ventana fija +-20, base calibrada y la
    candidata nsga_codo, con la misma semilla (números aleatorios comunes)."""
    estudio = cargar()
    escenario = estudio["escenarios"]["base"]
    series = [("fija_20", AZUL), ("base", NARANJA), ("nsga_codo", AQUA)]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for nombre, color in series:
        r = simular(estudio["politicas"][nombre], escenario, semilla, detalle=True)
        t_h = [t / 3600 for t in r["detalle"]["serie_cola"]["t"]]
        ax.plot(t_h, r["detalle"]["serie_cola"]["en_cola"], color=color, linewidth=2, label=nombre)
    ax.set_xlabel("Hora del día (Guatemala)")
    ax.set_ylabel("Solicitudes en cola")
    ax.set_title("Tamaño de la cola durante un día simulado (escenario base)")
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 4))
    ax.legend(frameon=False, loc="upper right")
    _despejar(ax)
    _guardar(fig, ruta_salida)


def grafica_frente_pareto(ruta_salida=FIGURAS / "frente_pareto.png"):
    """Candidatas y referencias en el espacio (espera, diferencia), todas evaluadas en el
    escenario `optimizacion` con las semillas 1000-1002 (las mismas condiciones en que NSGA-II y
    la búsqueda aleatoria exploraron el frente), con el frente explorado como referencia de fondo.
    La validación con 30 semillas y el escenario de un día completo está en sensibilidad_demanda.png
    y en results/experimentos_comparacion.csv."""
    pareto = _leer_csv(RESULTADOS / "pareto.csv")
    aleatoria = _leer_csv(RESULTADOS / "aleatoria_frente.csv")
    estudio = cargar()
    config_opt = cargar_config()
    escenario_opt = estudio["escenarios"][config_opt["escenario"]]
    semillas_opt = config_opt["semillas_evaluacion"]
    umbrales = estudio["umbrales"]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter([float(f["espera_media"]) for f in pareto], [float(f["dif_media"]) for f in pareto],
              s=14, color=NUBE_NSGA, zorder=1)
    ax.scatter([float(f["espera_media"]) for f in aleatoria], [float(f["dif_media"]) for f in aleatoria],
              s=14, color=NUBE_ALEATORIA, marker="x", zorder=1)

    # El codo del frente agrupa varias candidatas muy cerca entre sí: se numeran en vez de
    # escribir el nombre junto al punto, y el número se explica en un recuadro aparte.
    destacadas = [(n, AZUL, "o") for n in FIJAS] + [("base", NARANJA, "D")] + \
                 [(n, AQUA, "^") for n in CANDIDATAS]
    for i, (nombre, color, marcador) in enumerate(destacadas, start=1):
        m = evaluar(estudio["politicas"][nombre], escenario_opt, semillas_opt)
        ax.scatter([m["espera_media"]], [m["dif_media"]], s=90, color=color, marker=marcador,
                  zorder=3, edgecolors=INK, linewidths=0.6)
        ax.annotate(str(i), (m["espera_media"], m["dif_media"]), ha="center", va="center",
                   fontsize=7, fontweight="bold", color="white", zorder=4)

    recuadro = "\n".join(f"{i}  {nombre}" for i, (nombre, _, _) in enumerate(destacadas, start=1))
    ax.text(0.60, 0.74, recuadro, transform=ax.transAxes, fontsize=8, color=INK_SECUNDARIA,
           va="top", linespacing=1.6,
           bbox={"facecolor": SURFACE, "edgecolor": GRID, "boxstyle": "round,pad=0.5"})

    ax.text(0.99, umbrales["d_max"], f"D_max = {umbrales['d_max']:g} trofeos",
           transform=ax.get_yaxis_transform(), ha="right", va="bottom", fontsize=8, color=INK_MUTED)
    ax.axhline(umbrales["d_max"], color=INK_MUTED, linewidth=1, linestyle="--", zorder=2)

    handles = [
        Line2D([], [], marker="o", linestyle="", color=NUBE_NSGA, label="Explorado por NSGA-II"),
        Line2D([], [], marker="x", linestyle="", color=NUBE_ALEATORIA, label="Explorado por la búsqueda aleatoria"),
        Line2D([], [], marker="o", linestyle="", color=AZUL, markeredgecolor=INK, label="Ventana fija (±20/40/60)"),
        Line2D([], [], marker="D", linestyle="", color=NARANJA, markeredgecolor=INK, label="Base calibrada"),
        Line2D([], [], marker="^", linestyle="", color=AQUA, markeredgecolor=INK, label="Candidata adaptativa"),
    ]
    ax.legend(handles=handles, frameon=False, loc="upper right", fontsize=8)
    ax.set_xlabel("Espera media (s) — escenario optimización, hora pico")
    ax.set_ylabel("Diferencia media de trofeos")
    ax.set_title("Frente de Pareto: candidatas y ventanas de referencia")
    _despejar(ax)
    _guardar(fig, ruta_salida)


def grafica_sensibilidad_demanda(ruta_salida=FIGURAS / "sensibilidad_demanda.png"):
    """Espera media (IC95 %) de fija_20, base y nsga_codo en los cuatro escenarios del estudio,
    con 30 semillas nuevas (results/experimentos_resumen.csv)."""
    resumen = _leer_csv(RESULTADOS / "experimentos_resumen.csv")
    por_clave = {(f["escenario"], f["politica"]): f for f in resumen}
    escenarios = ["baja_demanda", "base", "alta_demanda", "revision_5s"]
    etiquetas = {"baja_demanda": "Baja demanda\n(2.5/s)", "base": "Base\n(5/s)",
                "alta_demanda": "Alta demanda\n(10/s)", "revision_5s": "Revisión 5 s\n(5/s)"}
    politicas = [("fija_20", AZUL), ("base", NARANJA), ("nsga_codo", AQUA)]
    x = range(len(escenarios))
    ancho = 0.25

    fig, ax = plt.subplots(figsize=(8, 5))
    for i, (pol, color) in enumerate(politicas):
        medias, err_inf, err_sup = [], [], []
        for esc in escenarios:
            f = por_clave[(esc, pol)]
            media = float(f["espera_media_media"])
            medias.append(media)
            err_inf.append(media - float(f["espera_media_ic95_inf"]))
            err_sup.append(float(f["espera_media_ic95_sup"]) - media)
        pos = [xi + (i - 1) * ancho for xi in x]
        ax.bar(pos, medias, width=ancho, color=color, label=pol,
              yerr=[err_inf, err_sup], capsize=3, error_kw={"linewidth": 1, "ecolor": INK_SECUNDARIA})

    ax.set_xticks(list(x))
    ax.set_xticklabels([etiquetas[e] for e in escenarios])
    ax.set_ylabel("Espera media (s)")
    ax.set_title("Sensibilidad de la espera media a la demanda y a la frecuencia de revisión")
    ax.legend(frameon=False, loc="upper right")
    _despejar(ax)
    _guardar(fig, ruta_salida)


def main():
    ap = argparse.ArgumentParser(description="Genera las gráficas mínimas de los experimentos")
    ap.parse_args()
    grafica_cola_en_el_tiempo()
    print("cola_en_el_tiempo.png")
    grafica_frente_pareto()
    print("frente_pareto.png")
    grafica_sensibilidad_demanda()
    print("sensibilidad_demanda.png")
    print(f"Guardadas en {FIGURAS}")


if __name__ == "__main__":
    main()
