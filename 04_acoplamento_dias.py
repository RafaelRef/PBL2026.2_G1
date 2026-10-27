"""04 -- Acoplamento das duas escalas de tempo, ao longo de 28 dias.

Roda o balanco do arquivo 02 e, a cada passo de 1 h, calcula o estado
hemodinamico quase estatico: SV pela pre-carga (5.1), R pela viscosidade e
pelo raio (5.2 + 5.3), HR pelo barorreflexo (5.3), o regime estavel do
Windkessel (arquivo 01) e a oferta de oxigenio (5.4).

Roda duas vezes -- reserva cardiovascular alta e baixa -- e sobrepoe, que e' a
pergunta de pesquisa 2: como a reserva e os parametros vasculares modificam a
resposta hemodinamica a perda sanguinea causada pelas coletas.
"""

import matplotlib.pyplot as plt

import parametros as P
import comum
import fisiologia as fis

bal = comum.importar("02_balanco_volume_hemacias")

RESERVAS = (P.RESERVA_ALTA, P.RESERVA_BAIXA)


def rodar(agenda=None, reservas=RESERVAS):
    r = bal.simular(agenda if agenda is not None else bal.agenda_rotina())
    return r, {res["nome"]: fis.serie_hemodinamica(r, res) for res in reservas}


# ---------------------------------------------------------------- saida

def resumo(r, series):
    bal.resumo(r, f"coleta de rotina, {P.DIAS} dias")
    print(f"\nPAM de referencia {fis.PAM_REF:.1f} mmHg   "
          f"('PAM baixa' = abaixo de "
          f"{(1 - P.QUEDA_PAM_REL) * fis.PAM_REF:.1f} mmHg)")
    print(f"\n{'reserva':>14s} {'PAM min':>8s} {'PAM media':>10s} "
          f"{'R/R0':>12s} {'HR max':>7s} {'DO2/kg min':>11s} "
          f"{'dias PAM baixa':>15s}")
    for nome, s in series.items():
        print(f"{nome:>14s} {s['PAM'].min():8.1f} {s['PAM'].mean():10.1f} "
              f"{s['R'].min() / s['R'][0]:5.2f}-{s['R'].max() / s['R'][0]:<6.2f} "
              f"{s['HR'].max():7.1f} "
              f"{s['DO2_kg'].min():11.1f} {s['dias_pam_baixa']:15.1f}")
    print("\nsanidade: PAM == Pv + R.DC em todos os passos -> "
          f"erro max {max(abs(s['PAM'] - (P.NEONATO['Pv'] + s['R'] * s['DC'] / 60.0)).max() for s in series.values()):.2e} mmHg")


def figura(r, series):
    fig, eixos = plt.subplots(4, 1, figsize=(10, 10), sharex=True)
    a_pam, a_r, a_hct, a_do2 = eixos

    for res in RESERVAS:
        s = series[res["nome"]]
        a_pam.plot(r["dia"], s["PAM"], lw=1.6, color=res["cor"],
                   label=res["nome"])
        a_r.plot(r["dia"], s["R"], lw=1.6, color=res["cor"],
                 label=res["nome"])
        a_do2.plot(r["dia"], s["DO2_kg"], lw=1.6, color=res["cor"],
                   label=res["nome"])

    a_pam.axhline(fis.PAM_REF, ls=":", color="#16a085",
                  label=f"referencia ({fis.PAM_REF:.0f} mmHg)")
    a_pam.set_ylabel("PAM (mmHg)")
    a_pam.set_title("Pressao arterial media")

    a_r.set_ylabel("R (mmHg.s/mL)")
    a_r.set_title("Resistencia periferica: viscosidade (Hct) x raio "
                  "(barorreflexo)")

    a_hct.plot(r["dia"], r["Hct"], lw=1.6, color="#8e44ad")
    a_hct.axhline(P.HCT_LIMIAR, ls=":", color="0.3",
                  label=f"limiar de transfusao ({P.HCT_LIMIAR:.2f})")
    a_hct.set_ylabel("Hematocrito")
    a_hct.set_title("Hematocrito (igual nas duas reservas: o balanco de "
                    "hemacias nao depende da hemodinamica)")

    a_do2.set_ylabel(r"DO$_2$ (mL O$_2$/min/kg)")
    a_do2.set_xlabel("Dia de internacao")
    a_do2.set_title("Oferta de oxigenio por kg")

    for t, _ in r["transfusoes"]:
        for ax in eixos:
            ax.axvline(t / 24.0, color="#16a085", lw=1.0, alpha=0.5)
    a_do2.plot([], [], color="#16a085", lw=1.0, alpha=0.5, label="transfusao")

    for ax in eixos:
        ax.legend(fontsize=8, loc="best", ncol=2)
    eixos[-1].set_xlim(0, r["dia"][-1])
    fig.suptitle("Coletas de rotina x reserva cardiovascular -- "
                 f"{P.DIAS} dias de internacao")
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    r, series = rodar()
    resumo(r, series)
    comum.salvar(figura(r, series), "04_acoplamento_dias.png")
    plt.show()
