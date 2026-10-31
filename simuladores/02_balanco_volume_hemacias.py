"""02 -- Balanco de volume e de massa de hemacias ao longo da internacao.

Escala de dias (passo de 1 h). Duas variaveis de estado:

    V [mL]  volume sanguineo
    M [mL]  volume de hemacias ("massa"), logo Hct = M / V

Ponto fisiologico central: depois de uma coleta o VOLUME volta para V_ref em
horas (desvio de liquido do interstico + hidratacao venosa, constante TAU_V),
mas a MASSA DE HEMACIAS perdida so volta por eritropoiese (lenta) ou
transfusao. Curto prazo = problema de volume; longo prazo = problema de Hct.
"""

import numpy as np
import matplotlib.pyplot as plt

import parametros as P
import comum
import fisiologia as fis


# ---------------------------------------------------------------- agendas

def agenda_por_hora(agenda):
    """Lista [(hora, volume)] -> dict {hora inteira: volume somado}."""
    por_hora = {}
    for hora, vol in agenda:
        h = int(round(hora))
        por_hora[h] = por_hora.get(h, 0.0) + vol
    return por_hora


def agenda_rotina(vol=P.VOL_COLETA):
    """Estrategia A: 2 coletas/dia na 1a semana, 1/dia na 2a, 1 a cada 2 dias
    depois. Com vol = 0.8 mL da ~22 mL em 28 dias (~33% do volume inicial),
    da ordem dos 28.5% de Counsilman 2019."""
    agenda = []
    for dia in range(P.DIAS):
        if dia < 7:
            horas = (6, 18)
        elif dia < 14:
            horas = (6,)
        else:
            horas = (6,) if dia % 2 == 0 else ()
        agenda += [(dia * 24 + h, vol) for h in horas]
    return agenda


# ---------------------------------------------------------------- hemacias

def destruicao_basal():
    """M0 / vida media [mL/dia] -- referencia para calibrar a producao."""
    return P.HCT0 * fis.volume_referencia(P.PESO0) / P.VIDA_HEMACIA


def producao_hemacias(Hct):
    """Eritropoiese: basal insuficiente + resposta lenta e limitada a Hct baixo."""
    frac = P.FRAC_PROD_BASAL + P.GANHO_PROD * max(0.0, P.HCT0 - Hct)
    return destruicao_basal() * min(frac, P.PROD_MAX)


# ---------------------------------------------------------------- simulacao

def simular(agenda, dias=P.DIAS, dt=P.DT_H, transfundir=True):
    """Integra V e M por `dias`. `agenda` e' uma lista [(hora, volume)] ou uma
    politica callable(estado) -> volume a coletar agora (estrategia D)."""
    politica = agenda if callable(agenda) else None
    pedidos = {} if politica else agenda_por_hora(agenda)

    peso = P.PESO0
    V_ref = fis.volume_referencia(peso)
    V, M = V_ref, P.HCT0 * V_ref
    V0, M0 = V, M

    n = int(round(dias * 24.0 / dt))
    hist = {k: [] for k in ("t_h", "peso", "V", "V_ref", "M", "Hct")}
    coletas, transfusoes = [], []
    acc = dict(reposto=0.0, coletado=0.0, coletado_M=0.0, transf_V=0.0,
               transf_M=0.0, produzido=0.0, destruido=0.0)

    for i in range(n + 1):
        t = i * dt
        Hct = M / V
        estado = dict(t_h=t, dia=t / 24.0, peso=peso, V=V, V_ref=V_ref, M=M,
                      Hct=Hct, historico=coletas)

        # --- coleta: sai sangue inteiro, ou seja, plasma + hemacias
        vol = politica(estado) if politica else pedidos.get(int(round(t)), 0.0)
        if vol > 0.0:
            V -= vol
            M -= vol * Hct
            acc["coletado"] += vol
            acc["coletado_M"] += vol * Hct
            coletas.append((t, vol))
            Hct = M / V

        # --- transfusao: concentrado de hemacias, auto-limitada (sobe o Hct)
        if transfundir and Hct < P.HCT_LIMIAR:
            vt = P.TRANSF_ML_KG * peso
            V += vt
            M += vt * P.HCT_CONCENTRADO
            acc["transf_V"] += vt
            acc["transf_M"] += vt * P.HCT_CONCENTRADO
            transfusoes.append((t, vt))
            Hct = M / V

        for k, v in (("t_h", t), ("peso", peso), ("V", V), ("V_ref", V_ref),
                     ("M", M), ("Hct", M / V)):
            hist[k].append(v)
        if i == n:
            break

        # --- avanco de dt horas
        rep = dt * (V_ref - V) / P.TAU_V          # reposicao: so plasma, dilui
        V += rep
        acc["reposto"] += rep
        prod = producao_hemacias(M / V) * dt / 24.0
        destr = (M / P.VIDA_HEMACIA) * dt / 24.0
        M += prod - destr
        acc["produzido"] += prod
        acc["destruido"] += destr
        peso = fis.peso_no_dia((t + dt) / 24.0)   # crescimento
        V_ref = fis.volume_referencia(peso)

    r = {k: np.array(v) for k, v in hist.items()}
    r.update(dia=r["t_h"] / 24.0, coletas=coletas, transfusoes=transfusoes,
             V0=V0, M0=M0, **acc)
    r["res_V"] = (V0 + acc["reposto"] + acc["transf_V"] - acc["coletado"]
                  - r["V"][-1])
    r["res_M"] = (M0 + acc["produzido"] - acc["destruido"] - acc["coletado_M"]
                  + acc["transf_M"] - r["M"][-1])
    return r


# ---------------------------------------------------------------- saida

def resumo(r, nome=""):
    print(f"{nome}")
    print(f"  coletas            {len(r['coletas']):4d} puncoes")
    print(f"  volume coletado    {r['coletado']:6.2f} mL "
          f"({100 * r['coletado'] / r['V0']:.1f}% do volume inicial de "
          f"{r['V0']:.0f} mL)")
    print(f"  transfusoes        {len(r['transfusoes']):4d}")
    print(f"  Hct final / minimo {r['Hct'][-1]:6.3f} / {r['Hct'].min():.3f}")
    print(f"  peso {r['peso'][0]:.2f} -> {r['peso'][-1]:.2f} kg   "
          f"V_ref {r['V_ref'][0]:.0f} -> {r['V_ref'][-1]:.0f} mL")
    print(f"  sanidade: residuo do balanco  V {r['res_V']:+.2e} mL   "
          f"M {r['res_M']:+.2e} mL")


def figura(r):
    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

    a1.plot(r["dia"], r["V_ref"], ls="--", lw=1.5, color="0.5",
            label=r"$V_{ref}$ (85 mL/kg do peso do dia)")
    a1.plot(r["dia"], r["V"], lw=1.8, color="#2a78d6", label="V simulado")
    # ticks das coletas na base do painel (y em coordenadas do eixo)
    for t, _ in r["coletas"]:
        a1.plot(t / 24.0, 0.02, marker="|", color="#c0392b", ms=8,
                transform=a1.get_xaxis_transform(), clip_on=False)
    a1.plot([], [], marker="|", ls="", color="#c0392b", label="coleta")
    a1.set_ylabel("Volume (mL)")
    a1.set_title("Volume: a coleta e' reposta em horas (tau = "
                 f"{P.TAU_V:.0f} h)")

    a2.plot(r["dia"], r["M"], lw=1.8, color="#8e44ad")
    a2.set_ylabel("Hemacias M (mL)")
    a2.set_title("Massa de hemacias: so volta por eritropoiese ou transfusao")

    a3.plot(r["dia"], r["Hct"], lw=1.8, color="#eb6834")
    a3.axhline(P.HCT_LIMIAR, ls=":", color="0.3",
               label=f"limiar de transfusao ({P.HCT_LIMIAR:.2f})")
    a3.set_ylabel("Hematocrito")
    a3.set_xlabel("Dia de internacao")
    a3.set_title("Hematocrito = M / V")

    for t, _ in r["transfusoes"]:
        for ax in (a1, a2, a3):
            ax.axvline(t / 24.0, color="#16a085", lw=1.2, alpha=0.7)
    a3.plot([], [], color="#16a085", lw=1.2, label="transfusao")

    for ax in (a1, a3):
        ax.legend(fontsize=8, loc="best")
    a3.set_xlim(0, r["dia"][-1])
    fig.suptitle("Balanco de volume e de hemacias -- coleta de rotina, "
                 f"{P.DIAS} dias")
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    r = simular(agenda_rotina())
    resumo(r, f"coleta de rotina ({P.VOL_COLETA:.1f} mL/puncao)")
    print()
    resumo(simular([]), "sem coleta nenhuma (referencia)")
    comum.salvar(figura(r), "02_balanco_volume_hemacias.png")
    plt.show()
