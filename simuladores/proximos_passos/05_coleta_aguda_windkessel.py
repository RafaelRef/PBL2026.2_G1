"""05 -- Efeito agudo de uma coleta, na escala de segundos.

Curva de pressao do prematuro em tres momentos -- antes, logo apos a coleta e
algumas horas depois -- para uma coleta de 1 mL e de 3 mL.

Mensagem: no curto prazo a coleta e' um problema de VOLUME (cai a pre-carga,
cai o SV) e o barorreflexo segura a PAM. Note que o Hct NAO muda na hora (sai
sangue inteiro); ele so cai algumas horas depois, quando o volume volta como
plasma e dilui as hemacias que foram embora.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # simuladores/

import numpy as np
import matplotlib.pyplot as plt

import parametros as P
import comum
import fisiologia as fis

wk = comum.importar("01_windkessel_base")


# ---------------------------------------------------------------- momentos

def momentos(v_coleta, peso=P.PESO0, horas=P.HORAS_DEPOIS):
    """(rotulo, V, M) antes, logo apos e `horas` depois de uma coleta."""
    V_ref = fis.volume_referencia(peso)
    M0 = P.HCT0 * V_ref
    M = M0 - v_coleta * P.HCT0                 # sangue inteiro: perde hemacias
    # reposicao exponencial do volume (so plasma) com constante TAU_V
    V_depois = V_ref - v_coleta * np.exp(-horas / P.TAU_V)
    return V_ref, [("antes", V_ref, M0, "0.35"),
                   ("logo apos", V_ref - v_coleta, M, "#c0392b"),
                   (f"{horas:.0f} h depois", V_depois, M, "#2a78d6")]


def avaliar(v_coleta, reserva, peso=P.PESO0):
    V_ref, mom = momentos(v_coleta, peso)
    saida = []
    for rotulo, V, M, cor in mom:
        e = fis.hemodinamica(V, V_ref, M / V, peso, reserva)
        e.update(rotulo=rotulo, cor=cor, Hct=M / V, V=V, V_ref=V_ref)
        saida.append(e)
    return saida


# ---------------------------------------------------------------- saida

def tabela(volumes=P.VOL_COLETA_AGUDA):
    print(f"PAM de referencia (basal) = {fis.PAM_REF:.1f} mmHg\n")
    print(f"{'coleta':>7s} {'momento':>12s} {'V':>7s} {'Hct':>6s} {'SV':>6s} "
          f"{'HR':>6s} {'R':>7s} {'PAS/PAD':>10s} {'PAM':>6s} {'dPAM':>7s} "
          f"{'DO2/kg':>7s}")
    for v in volumes:
        for reserva in (P.RESERVA_ALTA, P.SEM_COMPENSACAO):
            print(f"  -- {reserva['nome']}")
            for e in avaliar(v, reserva):
                d = 100.0 * (e["PAM"] - fis.PAM_REF) / fis.PAM_REF
                print(f"{v:6.1f}mL {e['rotulo']:>12s} {e['V']:7.2f} "
                      f"{e['Hct']:6.3f} {e['SV']:6.2f} {e['HR']:6.1f} "
                      f"{e['R']:7.2f} "
                      f"{e['PAS']:5.1f}/{e['PAD']:4.1f} {e['PAM']:6.1f} "
                      f"{d:+6.1f}% {e['DO2_kg']:7.1f}")
        print()


def figura(volumes=P.VOL_COLETA_AGUDA):
    fig = plt.figure(figsize=(11, 7))
    gs = fig.add_gridspec(2, len(volumes), height_ratios=[1.3, 1])
    eixos = [fig.add_subplot(gs[0, i]) for i in range(len(volumes))]
    ax_pam = fig.add_subplot(gs[1, :])

    for ax, v in zip(eixos, volumes):
        for e in avaliar(v, P.RESERVA_ALTA):
            t, Pr = wk.curva_batimentos(e["HR"], e["SV"], e["R"], e["C"],
                                        e["Pv"])
            ax.plot(t, Pr, lw=1.8, color=e["cor"],
                    label=f"{e['rotulo']}: {e['PAS']:.0f}/{e['PAD']:.0f} "
                          f"(PAM {e['PAM']:.1f})")
        ax.axhline(fis.PAM_REF, ls=":", lw=1, color="#16a085")
        ax.set_title(f"Coleta de {v:.0f} mL "
                     f"({100 * v / fis.volume_referencia(P.PESO0):.1f}% do "
                     f"volume sanguineo)")
        ax.set_xlabel("Tempo (s)")
        ax.set_ylabel("Pressao (mmHg)")
        ax.legend(fontsize=8, title="PAS/PAD em mmHg", title_fontsize=8)

    # painel de baixo: PAM com e sem barorreflexo
    rotulos = [e["rotulo"] for e in avaliar(volumes[0], P.RESERVA_ALTA)]
    x = np.arange(len(volumes) * len(rotulos))
    largura = 0.38
    for k, reserva in enumerate((P.RESERVA_ALTA, P.SEM_COMPENSACAO)):
        pam = [e["PAM"] for v in volumes for e in avaliar(v, reserva)]
        ax_pam.bar(x + (k - 0.5) * largura, pam, largura,
                   color=reserva["cor"], label=reserva["nome"])
    ax_pam.axhline(fis.PAM_REF, ls=":", color="#16a085",
                   label=f"PAM de referencia ({fis.PAM_REF:.0f} mmHg)")
    ax_pam.set_xticks(x)
    ax_pam.set_xticklabels([f"{v:.0f} mL\n{r}" for v in volumes
                            for r in rotulos], fontsize=8)
    ax_pam.set_ylabel("PAM (mmHg)")
    ax_pam.set_ylim(0, fis.PAM_REF * 1.3)
    ax_pam.set_title("A compensacao segura a PAM: o mesmo estado de volume "
                     "com e sem barorreflexo")
    ax_pam.legend(fontsize=8, ncol=3)

    fig.suptitle("Efeito agudo da coleta no prematuro "
                 f"({P.PESO0:.1f} kg) -- escala de segundos")
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    tabela()
    comum.salvar(figura(), "05_coleta_aguda_windkessel.png")
    plt.show()
