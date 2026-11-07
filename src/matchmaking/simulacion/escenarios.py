"""
Escenarios y políticas de referencia del estudio, definidos en configs/escenarios.yaml.

Uso desde optimización o experimentos:

    from src.matchmaking.simulacion.escenarios import cargar
    from src.matchmaking.simulacion.motor import simular

    cfg = cargar()
    r = simular(cfg["politicas"]["base"], cfg["escenarios"]["base"], semilla=1)
"""

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[3]
CONFIG = RAIZ / "configs" / "escenarios.yaml"


def cargar(ruta=CONFIG):
    cfg = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))
    comun = cfg.get("comun", {})
    escenarios = {k: {**comun, **v} for k, v in cfg["escenarios"].items()}
    politicas = {k: {kk: float(vv) for kk, vv in v.items()} for k, v in cfg["politicas"].items()}
    return {"escenarios": escenarios, "politicas": politicas, "umbrales": cfg.get("umbrales", {})}
