"""05 -- Comparacao de estrategias de coleta (pergunta de pesquisa 1).

Mesma crianca, mesmos 28 dias, mesma reserva cardiovascular; muda so a
estrategia de coleta:

  A. Rotina      varias coletas/dia na 1a semana, VOL_COLETA por puncao
  B. Agrupada    os mesmos exames, agrupados em menos puncoes -- cada exame
                 extra na mesma puncao custa so FATOR_AGRUPAMENTO do volume
                 (menos desperdicio por puncao)
  C. Micrometodo mesma frequencia que A, VOL_COLETA_MICRO por puncao
  D. Guiada      so coleta se o volume disponivel (arquivo 06) permitir;
                 senao adia o pedido

A estrategia D usa um limiar de Hct com folga (HCT_LIMIAR + MARGEM_HCT): a
ideia e' nao coletar o paciente ate a transfusao, e sim parar antes. E tem uma
valvula de escape: um pedido que espera mais de ESPERA_MAX horas e' feito de
qualquer forma, mas no volume de micrometodo -- exame essencial nao pode
esperar para sempre. Sem essa valvula a regra simplesmente trava as coletas
depois que o Hct cai, o que nao e' um protocolo utilizavel.
"""

import numpy as np
import matplotlib.pyplot as plt

import parametros as P
import comum
import fisiologia as fis

bal = comum.importar("02_balanco_volume_hemacias")
rec = comum.importar("06_recomendacao")

RESERVA = P.RESERVA_BAIXA     # pior caso: evidencia as diferencas na PAM


# ---------------------------------------------------------------- estrategias

def agenda_agrupada(vol=P.VOL_COLETA, fator=P.FATOR_AGRUPAMENTO):
    """Junta as coletas do mesmo dia numa puncao so. n exames na mesma puncao
    custam vol * (1 + fator*(n-1)) em vez de n * vol."""
    por_dia = {}
    for hora, _ in bal.agenda_rotina(vol):
        por_dia.setdefault(int(hora // 24), []).append(hora)
    return [(min(horas), vol * (1.0 + fator * (len(horas) - 1)))
            for _, horas in sorted(por_dia.items())]


def politica_guiada(agenda=None, limite_Hct=P.HCT_LIMIAR + P.MARGEM_HCT,
                    espera_max=P.ESPERA_MAX, vol_minimo=P.VOL_COLETA_MICRO):
    """Fila de pedidos: cada um so sai quando couber no volume disponivel.

    Depois de `espera_max` horas na fila, o pedido sai no volume minimo
    (micrometodo), mesmo que estoure o disponivel.
    """
    pedidos = bal.agenda_por_hora(agenda if agenda is not None
                                  else bal.agenda_rotina())
    pendentes, atrasos, reduzidos = [], [], []

    def politica(estado):
        t = estado["t_h"]
        if int(round(t)) in pedidos:
            pendentes.append([t, pedidos[int(round(t))]])
        if not pendentes:
            return 0.0
        disponivel = rec.volume_disponivel(estado, limite_Hct=limite_Hct)
        total = 0.0
        while pendentes and pendentes[0][1] <= disponivel - total:
            t0, vol = pendentes.pop(0)
            total += vol
            atrasos.append(t - t0)
        # valvula de escape: exame essencial sai no volume minimo
        while pendentes and t - pendentes[0][0] >= espera_max:
            t0, vol = pendentes.pop(0)
            total += vol_minimo
            atrasos.append(t - t0)
            reduzidos.append(vol - vol_minimo)
        return total

    politica.pendentes = pendentes
    politica.atrasos = atrasos
    politica.reduzidos = reduzidos
    return politica


def estrategias():
    guiada = politica_guiada()
    return [
        dict(id="A", nome="Rotina", cor="#c0392b",
             agenda=bal.agenda_rotina()),
        dict(id="B", nome="Agrupada", cor="#e67e22",
             agenda=agenda_agrupada()),
        dict(id="C", nome="Micrometodo", cor="#2a78d6",
             agenda=bal.agenda_rotina(P.VOL_COLETA_MICRO)),
        dict(id="D", nome="Guiada", cor="#16a085",
             agenda=guiada, politica=guiada),
    ]


def rodar(reserva=RESERVA):
    saida = []
    for e in estrategias():
        r = bal.simular(e["agenda"])
        s = fis.serie_hemodinamica(r, reserva)
        saida.append({**e, "r": r, "s": s})
    return saida


# ---------------------------------------------------------------- saida

def tabela(res):
    print(f"reserva cardiovascular: {RESERVA['nome']}   "
          f"PAM de referencia {fis.PAM_REF:.1f} mmHg\n")
    print(f"{'':2s} {'estrategia':<12s} {'puncoes':>8s} {'coletado':>9s} "
          f"{'% V0':>6s} {'transf':>7s} {'1a transf':>10s} {'Hct min':>8s} "
          f"{'Hct dia 28':>11s} {'DO2/kg min':>11s} {'dias PAM baixa':>15s}")
    for e in res:
        r, s = e["r"], e["s"]
        d1 = (f"dia {r['transfusoes'][0][0] / 24:.1f}" if r["transfusoes"]
              else "-")
        print(f"{e['id']:2s} {e['nome']:<12s} {len(r['coletas']):8d} "
              f"{r['coletado']:8.2f}mL {100 * r['coletado'] / r['V0']:5.1f}% "
              f"{len(r['transfusoes']):7d} {d1:>10s} {r['Hct'].min():8.3f} "
              f"{r['Hct'][-1]:11.3f} {s['DO2_kg'].min():11.1f} "
              f"{s['dias_pam_baixa']:15.1f}")

    g = next(e for e in res if "politica" in e)["politica"]
    print(f"\nD (guiada, Hct protegido em "
          f"{P.HCT_LIMIAR + P.MARGEM_HCT:.2f}): {len(g.atrasos)} pedidos "
          f"atendidos, atraso medio {np.mean(g.atrasos) if g.atrasos else 0:.1f} h "
          f"(maximo {max(g.atrasos) if g.atrasos else 0:.0f} h); "
          f"{len(g.reduzidos)} reduzidos ao volume minimo "
          f"(economia de {sum(g.reduzidos):.1f} mL); "
          f"{len(g.pendentes)} ainda na fila no dia {P.DIAS}")
    print("\nnota: Hct min fica colado no limiar sempre que ha transfusao -- "
          "o que discrimina as estrategias e' o dia da 1a transfusao, "
          "quantas foram\n      necessarias e o Hct no fim.")


def figura(res):
    fig, (a_hct, a_do2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    for e in res:
        rot = f"{e['id']}. {e['nome']} ({e['r']['coletado']:.1f} mL)"
        a_hct.plot(e["r"]["dia"], e["r"]["Hct"], lw=1.6, color=e["cor"],
                   label=rot)
        a_do2.plot(e["r"]["dia"], e["s"]["DO2_kg"], lw=1.6, color=e["cor"],
                   label=rot)
        for t, _ in e["r"]["transfusoes"]:
            a_hct.plot(t / 24.0, P.HCT_LIMIAR, marker="v", ms=7,
                       color=e["cor"])

    a_hct.axhline(P.HCT_LIMIAR, ls=":", color="0.3",
                  label=f"limiar de transfusao ({P.HCT_LIMIAR:.2f})")
    a_hct.set_ylabel("Hematocrito")
    a_hct.set_title("Hematocrito (marcadores = transfusoes)")
    a_do2.set_ylabel(r"DO$_2$ (mL O$_2$/min/kg)")
    a_do2.set_xlabel("Dia de internacao")
    a_do2.set_title(f"Oferta de oxigenio por kg ({RESERVA['nome']})")
    for ax in (a_hct, a_do2):
        ax.legend(fontsize=8, ncol=2)
    a_do2.set_xlim(0, res[0]["r"]["dia"][-1])
    fig.suptitle("Estrategias de coleta no mesmo prematuro -- "
                 f"{P.DIAS} dias")
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    res = rodar()
    tabela(res)
    comum.salvar(figura(res), "05_estrategias_coleta.png")
    plt.show()
