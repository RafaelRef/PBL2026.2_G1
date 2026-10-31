"""Utilidades compartilhadas pelos arquivos numerados.

Duas coisas so:
  importar(nome)  -> carrega um arquivo "0X_...py" como modulo
  salvar(fig, n)  -> grava a figura em figuras/simuladores/ e avisa no terminal
"""

import importlib.util
import sys
from pathlib import Path

import parametros as P

PASTA = Path(__file__).resolve().parent              # simuladores/
RAIZ = PASTA.parent                                  # raiz do repositorio
FIGURAS = RAIZ / "figuras" / "simuladores"
FIGURAS_RELATORIO = RAIZ / "figuras" / "relatorio_parcial"
PROXIMOS_PASSOS = PASTA / "proximos_passos"            # analises para o relatorio final


def importar(nome):
    """Importa um arquivo numerado, ex.: importar("01_windkessel_base").

    `import 01_windkessel_base` e' sintaxe invalida em Python -- nome de
    modulo nao pode comecar com digito -- entao carregamos pelo caminho do
    arquivo, procurando em simuladores/ e em simuladores/proximos_passos/.
    O codigo de cada arquivo fica atras de `if __name__ ==
    "__main__"`, logo importar nao dispara figura nenhuma.
    """
    if nome in sys.modules:
        return sys.modules[nome]
    caminho = PASTA / f"{nome}.py"
    if not caminho.exists():                      # ex.: 06_recomendacao
        caminho = PROXIMOS_PASSOS / f"{nome}.py"
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def salvar(fig, nome):
    """Grava a figura em figuras/simuladores/<nome> e devolve o caminho."""
    FIGURAS.mkdir(parents=True, exist_ok=True)
    caminho = FIGURAS / nome
    fig.savefig(caminho, dpi=P.DPI, bbox_inches="tight")
    print(f"\nfigura salva em figuras/simuladores/{nome}")
    return caminho
