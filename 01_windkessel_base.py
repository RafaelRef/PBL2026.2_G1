"""01 -- Windkessel RC de 2 elementos: adulto vs neonato.

Modelo 0D de parametros concentrados. Cada batimento e' um impulso: o volume
sistolico entra de uma vez e a pressao sobe SV/C. Entre batimentos o circuito
RC descarrega:

    P(t) = Pv + (P0 - Pv) * exp(-t/tau),      tau = R * C

Em regime periodico (T = 60/HR) a solucao fecha em forma analitica -- e' o que
`regime_estavel` devolve. Os arquivos 03, 04 e 05 reaproveitam essa funcao em
vez de reescrever o modelo.
"""

import numpy as np
import matplotlib.pyplot as plt

import parametros as P
import comum


# ---------------------------------------------------------------- modelo

def regime_estavel(HR, SV, R, C, Pv):
    """Pressoes do regime periodico, em forma fechada.

    Devolve PAS, PAD, PAM, PP [mmHg], tau e T [s] e DC [mL/min].
    """
    T = 60.0 / HR
    tau = R * C
    dP = SV / C                                    # degrau de cada batimento
    PAS = Pv + dP / (1.0 - np.exp(-T / tau))
    PAD = Pv + (PAS - Pv) * np.exp(-T / tau)
    PAM = Pv + R * SV / T                          # = Pv + R * DC
    return dict(PAS=PAS, PAD=PAD, PAM=PAM, PP=PAS - PAD,
                tau=tau, T=T, DC=SV * HR,
                HR=HR, SV=SV, R=R, C=C, Pv=Pv)


def curva_batimentos(HR, SV, R, C, Pv, n_batimentos=P.N_BATIMENTOS):
    """Concatena n decaimentos iguais, um a cada T segundos. Devolve (t, Pr)."""
    e = regime_estavel(HR, SV, R, C, Pv)
    t, Pr = [], []
    for k in range(n_batimentos):
        s = np.linspace(0.0, e["T"], P.PONTOS)
        t.append(k * e["T"] + s)
        Pr.append(Pv + (e["PAS"] - Pv) * np.exp(-s / e["tau"]))
    return np.concatenate(t), np.concatenate(Pr)


# ---------------------------------------------------------------- figura

def figura(pacientes=P.PACIENTES):
    fig, eixos = plt.subplots(1, len(pacientes), figsize=(11, 4))

    for ax, p in zip(np.atleast_1d(eixos), pacientes):
        e = regime_estavel(p["HR"], p["SV"], p["R"], p["C"], p["Pv"])
        t, Pr = curva_batimentos(p["HR"], p["SV"], p["R"], p["C"], p["Pv"])

        ax.plot(t, Pr, lw=2, color=p["cor"])
        # setas verticais: o batimento levando a pressao de PAD ate PAS
        for k in range(P.N_BATIMENTOS):
            ax.annotate("", xy=(k * e["T"], e["PAS"]),
                        xytext=(k * e["T"], e["PAD"]),
                        arrowprops=dict(arrowstyle="-|>", lw=1.8,
                                        color=p["cor"]))

        ax.axhline(e["PAM"], ls=":", lw=1, color="0.4")
        ax.text(0.98, e["PAM"], " PAM", color="0.3", fontsize=8,
                va="bottom", ha="right", transform=ax.get_yaxis_transform())
        ax.set_ylim(0, e["PAS"] * 1.15)
        ax.set_xlim(-0.1 * e["T"], P.N_BATIMENTOS * e["T"])
        ax.set_title(f"{p['nome']}   {p['HR']:.0f} bpm   "
                     f"PAS/PAD {e['PAS']:.0f}/{e['PAD']:.0f} mmHg")
        ax.set_xlabel("Tempo (s)")
        ax.set_ylabel("Pressao (mmHg)")

    fig.suptitle("Windkessel RC: pulso instantaneo + "
                 r"decaimento $e^{-t/\tau}$")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------- saida

def tabela(pacientes=P.PACIENTES):
    print(f"{'paciente':10s} {'PAS':>6s} {'PAD':>6s} {'PAM':>6s} "
          f"{'PP':>6s} {'tau':>6s} {'T':>6s} {'DC':>8s}")
    print(f"{'':10s} {'mmHg':>6s} {'mmHg':>6s} {'mmHg':>6s} "
          f"{'mmHg':>6s} {'s':>6s} {'s':>6s} {'mL/min':>8s}")
    for p in pacientes:
        e = regime_estavel(p["HR"], p["SV"], p["R"], p["C"], p["Pv"])
        print(f"{p['nome']:10s} {e['PAS']:6.1f} {e['PAD']:6.1f} "
              f"{e['PAM']:6.1f} {e['PP']:6.1f} {e['tau']:6.2f} "
              f"{e['T']:6.2f} {e['DC']:8.0f}")


def sanidade(pacientes=P.PACIENTES):
    """PAM fechada vs media numerica da curva (devem coincidir no RC linear)."""
    print("\nsanidade -- PAM fechada (Pv + R.DC) vs media da curva:")
    for p in pacientes:
        e = regime_estavel(p["HR"], p["SV"], p["R"], p["C"], p["Pv"])
        t, Pr = curva_batimentos(p["HR"], p["SV"], p["R"], p["C"], p["Pv"], 1)
        pam_num = np.trapezoid(Pr, t) / (t[-1] - t[0])
        print(f"  {p['nome']:10s} fechada {e['PAM']:7.3f}   "
              f"numerica {pam_num:7.3f}   erro {abs(e['PAM']-pam_num):.2e} mmHg")


if __name__ == "__main__":
    tabela()
    sanidade()
    fig = figura()
    comum.salvar(fig, "01_windkessel_adulto_vs_neonato.png")
    plt.show()
