"""06 -- Recomendacao: quanto ainda da para coletar e quando dara para coletar.

Funcao de apoio usada pela estrategia D do arquivo 05, e executavel sozinha.
Tres regras explicitas, todas em `limites`; vale sempre a mais restritiva:

  1. janela de 24 h -- a perda acumulada nas ultimas 24 h nao passa de
     FRAC_MAX_24H de V_ref;
  2. hematocrito    -- o Hct projetado DEPOIS que o volume voltar a V_ref
                       (ou seja, ja contando a diluicao) nao cai abaixo do
                       limiar de transfusao;
  3. volume agora   -- V nao cai abaixo de (1 - margem) de V_ref.
"""

import numpy as np

import parametros as P
import comum
import fisiologia as fis

bal = comum.importar("02_balanco_volume_hemacias")


# ---------------------------------------------------------------- estado

def estado_de(r, i=-1):
    """Extrai o estado do indice i de um resultado de `bal.simular`."""
    return dict(t_h=float(r["t_h"][i]), dia=float(r["dia"][i]),
                peso=float(r["peso"][i]), V=float(r["V"][i]),
                V_ref=float(r["V_ref"][i]), M=float(r["M"][i]),
                Hct=float(r["Hct"][i]), historico=r["coletas"])


def coletado_em_24h(estado):
    """Soma das coletas na janela movel (t - 24 h, t].

    O limite superior importa: quando o estado vem de uma simulacao ja
    rodada, `historico` tem tambem as coletas futuras -- que nao contam.
    """
    t = estado["t_h"]
    return sum(v for th, v in estado["historico"] if t - 24.0 < th <= t)


def projetar(estado, horas, dt=P.DT_H):
    """Estado `horas` a frente sem novas coletas (mesmo avanco do arquivo 02)."""
    t, V, M = estado["t_h"], estado["V"], estado["M"]
    peso, V_ref = estado["peso"], estado["V_ref"]
    for _ in range(int(round(horas / dt))):
        V += dt * (V_ref - V) / P.TAU_V
        M += (bal.producao_hemacias(M / V) - M / P.VIDA_HEMACIA) * dt / 24.0
        t += dt
        peso = fis.peso_no_dia(t / 24.0)
        V_ref = fis.volume_referencia(peso)
    return dict(t_h=t, dia=t / 24.0, peso=peso, V=V, V_ref=V_ref, M=M,
                Hct=M / V, historico=estado["historico"])


# ---------------------------------------------------------------- regras

def limites(estado, limite_Hct=P.HCT_LIMIAR, margem_volume=P.MARGEM_VOLUME):
    """As tres regras, em mL. Negativo = regra ja violada."""
    V, M, V_ref = estado["V"], estado["M"], estado["V_ref"]
    Hct = M / V
    return dict(
        janela_24h=P.FRAC_MAX_24H * V_ref - coletado_em_24h(estado),
        # coletar v tira v.Hct de hemacias; depois o volume volta para V_ref
        hct=(M - limite_Hct * V_ref) / Hct,
        volume=V - (1.0 - margem_volume) * V_ref,
    )


def volume_disponivel(estado, limite_Hct=P.HCT_LIMIAR,
                      margem_volume=P.MARGEM_VOLUME):
    """Volume [mL] que pode sair agora sem furar nenhuma das tres regras."""
    return max(0.0, min(limites(estado, limite_Hct, margem_volume).values()))


def tempo_ate_proxima_coleta(estado, volume_desejado,
                             horizonte=P.HORIZONTE_ESPERA, dt=P.DT_H):
    """Horas de espera ate caber `volume_desejado`; inf se nao couber no
    horizonte. Procura hora a hora: a janela de 24 h abre sozinha quando as
    coletas antigas saem dela, e o Hct sobe devagar pela eritropoiese."""
    if volume_disponivel(estado) >= volume_desejado:
        return 0.0
    h = dt
    while h <= horizonte:
        if volume_disponivel(projetar(estado, h, dt)) >= volume_desejado:
            return float(h)
        h += dt
    return float("inf")


# ---------------------------------------------------------------- saida

def frase(estado, volume_desejado=P.VOL_EXEMPLO):
    disp = volume_disponivel(estado)
    espera = tempo_ate_proxima_coleta(estado, volume_desejado)
    quando = ("agora" if espera == 0.0 else
              f"aguardar ~{espera:.0f} h" if np.isfinite(espera) else
              f"nao cabe nas proximas {P.HORIZONTE_ESPERA} h")
    return (f"Paciente {estado['peso']:.2f} kg, dia {estado['dia']:.0f}: "
            f"pode coletar ate {disp:.2f} mL agora; "
            f"para {volume_desejado:.1f} mL, {quando}.")


if __name__ == "__main__":
    print(f"regras: perda em 24 h <= {100 * P.FRAC_MAX_24H:.0f}% de V_ref | "
          f"Hct projetado >= {P.HCT_LIMIAR:.2f} | "
          f"V >= {100 * (1 - P.MARGEM_VOLUME):.0f}% de V_ref\n")

    r = bal.simular(bal.agenda_rotina(P.VOL_COLETA_MICRO))
    print(f"paciente sob micrometodo ({P.VOL_COLETA_MICRO:.1f} mL/coleta):\n")
    print(f"{'dia':>4s} {'peso':>5s} {'Hct':>6s} {'24h':>6s} "
          f"{'lim 24h':>8s} {'lim Hct':>8s} {'lim vol':>8s} "
          f"{'disponivel':>10s} {'espera':>12s}")
    for dia in (1, 3, P.DIA_EXEMPLO, 10, 14, 21, 27):
        e = estado_de(r, int(round(dia * 24 / P.DT_H)))
        L = limites(e)
        esp = tempo_ate_proxima_coleta(e, P.VOL_EXEMPLO)
        print(f"{dia:4d} {e['peso']:5.2f} {e['Hct']:6.3f} "
              f"{coletado_em_24h(e):6.2f} {L['janela_24h']:8.2f} "
              f"{L['hct']:8.2f} {L['volume']:8.2f} "
              f"{volume_disponivel(e):10.2f} "
              f"{(f'{esp:.0f} h' if np.isfinite(esp) else '> horizonte'):>12s}")
    print(f"\n(espera = ate caber {P.VOL_EXEMPLO:.1f} mL; a regra que aperta "
          f"e' a menor das tres colunas 'lim')\n")

    e_micro = estado_de(r, int(round(P.DIA_EXEMPLO * 24 / P.DT_H)))
    print(frase(e_micro))

    # contraste: o mesmo dia, mas com a agenda de rotina
    r_rot = bal.simular(bal.agenda_rotina())
    e_rot = estado_de(r_rot, int(round(P.DIA_EXEMPLO * 24 / P.DT_H)))
    print("sob coleta de rotina, no mesmo dia: " + frase(e_rot))
