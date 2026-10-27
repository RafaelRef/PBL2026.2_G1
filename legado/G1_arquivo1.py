import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------------- parametros

ADULTO = dict(nome="Adulto", HR=70.0, SV=70.0, C=1.20, R=1.0, Pv=5.0,
              cor="#2a78d6")
NEONATO = dict(nome="Neonato", HR=140.0, SV=5.0, C=0.13, R=3.6, Pv=3.0,
               cor="#eb6834")

"""
  P  [mmHg]       pressao arterial
  SV [mL]         volume sistolico
  C  [mL/mmHg]    complacencia arterial total
  R  [mmHg.s/mL]  resistencia periferica total
  Pv [mmHg]       pressao venosa de saida
  T  [s]          intervalo entre batimentos = 60/HR
"""

PACIENTES = [ADULTO, NEONATO]

N_BATIMENTOS = 4       # batimentos mostrados no grafico
PONTOS = 400           # pontos usados para desenhar cada decaimento


# ---------------------------------------------------------------- simulacao

def curva(p):
    T = 60.0 / p["HR"]
    tau = p["R"] * p["C"]
    dP = p["SV"] / p["C"]                     # degrau de cada batimento

    PAS = p["Pv"] + dP / (1 - np.exp(-T / tau))
    PAD = p["Pv"] + (PAS - p["Pv"]) * np.exp(-T / tau)

    # concatena N_BATIMENTOS decaimentos iguais, um a cada T segundos
    t, P = [], []
    for k in range(N_BATIMENTOS):
        s = np.linspace(0, T, PONTOS)
        t.append(k * T + s)
        P.append(p["Pv"] + (PAS - p["Pv"]) * np.exp(-s / tau))
    return np.concatenate(t), np.concatenate(P), PAS, PAD, tau, T


def plotar():
    fig, eixos = plt.subplots(1, len(PACIENTES), figsize=(11, 4))

    for ax, p in zip(eixos, PACIENTES):
        t, P, PAS, PAD, tau, T = curva(p)
        PAM = p["Pv"] + p["R"] * p["SV"] / T

        print(f"{p['nome']:8s}  PAS {PAS:5.1f}  PAD {PAD:5.1f}  "
              f"PAM {PAM:5.1f} mmHg   tau {tau:.2f} s   T {T:.2f} s")

        ax.plot(t, P, lw=2, color=p["cor"])

        # setas verticais: o batimento levando a pressao de PAD ate PAS
        for k in range(N_BATIMENTOS):
            ax.annotate("", xy=(k * T, PAS), xytext=(k * T, PAD),
                        arrowprops=dict(arrowstyle="-|>", lw=1.8,
                                        color=p["cor"]))

        ax.set_ylim(0, PAS * 1.15)
        ax.set_xlim(-0.1 * T, N_BATIMENTOS * T)
        ax.set_title(f"{p['nome']}   {p['HR']:.0f} bpm   "
                     f"PAS/PAD {PAS:.0f}/{PAD:.0f} mmHg")
        ax.set_xlabel("Tempo (s)")
        ax.set_ylabel("Pressao (mmHg)")

    fig.suptitle("Windkessel RC: pulso instantaneo + "
                 r"decaimento $e^{-t/\tau}$")
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    plotar()
