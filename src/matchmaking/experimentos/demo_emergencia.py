"""
Demo en vivo de emergencia (R4), solo para la presentación.

`ejecutar.py --rapido` ya corre en vivo y rápido, pero solo el escenario `base`. Este script es
el respaldo si en la demo preguntan por los otros escenarios (demanda baja/alta, revisión 5 s):
corre el simulador de verdad, con pocas semillas, en los 4 escenarios, y solo imprime en
consola. No escribe en `results/`, para no arriesgar los CSV del experimento final (1,080
corridas, 30 semillas) que usa el informe.

    python -m src.matchmaking.experimentos.demo_emergencia
"""

from .ejecutar import ejecutar

SEMILLAS_DEMO = range(9000, 9003)  # inventadas para la demo; no se usan en ningún otro lado
ESCENARIOS_DEMO = ("base", "baja_demanda", "alta_demanda", "revision_5s")


def main():
    print(f"Corriendo en vivo: {len(ESCENARIOS_DEMO)} escenarios x 9 políticas x "
          f"{len(list(SEMILLAS_DEMO))} semillas nuevas...\n")
    _, _, comparacion = ejecutar(semillas=SEMILLAS_DEMO, escenarios_a_correr=ESCENARIOS_DEMO)

    print(f"{'escenario':<15} {'reducción vs fija_20':>22} {'dif. media':>12} {'mejora':>8}")
    for fila in comparacion:
        if fila["politica"] == "nsga_codo" and fila["referencia"] == "fija_20":
            print(f"{fila['escenario']:<15} {fila['reduccion_%']:>21.1f}% "
                  f"{fila['dif_media_candidata']:>12.2f} {str(fila['mejora_declarada']):>8}")


if __name__ == "__main__":
    main()
