"""Acoplamentos entre a coleta e o Windkessel (secao 5 do documento).

O Windkessel puro nao tem volume sanguineo. A coleta entra por tres caminhos,
todos alimentando os mesmos SV, R e HR do arquivo 01:

  5.1  volume   -> SV   (pre-carga, Frank-Starling linearizado)
  5.2  Hct      -> mu   -> R   (Poiseuille, em forma relativa)
  5.3  PAM      -> r, HR       (barorreflexo; ponto fixo, pois R depende de PAM
                                e PAM depende de R)
  5.4  Hct e DC -> DO2         (oferta de oxigenio)
"""

import numpy as np

import parametros as P
import comum

wk = comum.importar("01_windkessel_base")
regime_estavel = wk.regime_estavel


# ------------------------------------------------- tamanho do bebe

def volume_referencia(peso):
    """V_ref [mL] esperado para o peso do dia."""
    return P.VOL_POR_KG * peso


def peso_no_dia(dia, peso0=P.PESO0):
    """Ganho de GANHO_PESO g/kg/dia -> crescimento exponencial."""
    return peso0 * np.exp(P.GANHO_PESO / 1000.0 * dia)


def windkessel_do_bebe(peso):
    """Parametros RC do prematuro, por escala alometrica simples.

    Os valores NEONATO do arquivo 01 sao de um neonato a termo
    (~PESO_NEONATO_REF kg). Reescalamos pelo volume sanguineo: SV e C crescem
    com o volume, R cai na mesma proporcao. Assim tau = R.C e a PAM basal nao
    mudam com o crescimento -- so a escala do DC muda, como se espera.
    """
    escala = volume_referencia(peso) / volume_referencia(P.PESO_NEONATO_REF)
    return dict(HR0=P.NEONATO["HR"], SV0=P.NEONATO["SV"] * escala,
                C=P.NEONATO["C"] * escala, R0=P.NEONATO["R"] / escala,
                Pv=P.NEONATO["Pv"], escala=escala)


# ------------------------------------------------- 5.1 volume -> SV

def sv_de_volume(V, V_ref, SV0):
    """So o volume acima do nao estressado Vu = FU.V_ref gera pre-carga."""
    Vu = P.FU * V_ref
    return SV0 * float(np.clip((V - Vu) / (V_ref - Vu), 0.0, P.SV_REL_MAX))


# ------------------------------------------------- 5.2 Hct -> viscosidade

def viscosidade_relativa(Hct, Hct0=P.HCT0):
    """mu(Hct)/mu(Hct0) com mu = mu_plasma.exp(K_MU.Hct).

    R e' linear em mu, mas NAO em Hct: a relacao viscosidade x hematocrito e'
    exponencial no modelo e nao linear na realidade.
    """
    return float(np.exp(P.K_MU * (Hct - Hct0)))


# ------------------------------------------------- 5.3 barorreflexo

def _resposta(erro, reserva):
    """Raio e frequencia relativos para um dado erro de PAM, com limites."""
    r_rel = max(P.R_REL_MIN, 1.0 - reserva["g_r"] * erro)
    hr_rel = min(P.HR_REL_MAX, 1.0 + reserva["g_hr"] * erro)
    return r_rel, hr_rel


def hemodinamica(V, V_ref, Hct, peso, reserva, pam_ref=None):
    """Estado hemodinamico quase estatico (ponto fixo do barorreflexo).

    R depende da PAM (via barorreflexo) e a PAM depende de R, entao o estado
    sai da equacao de ponto fixo

        erro = max(0, (PAM_ref - PAM(erro)) / PAM_ref).

    PAM cresce quando o erro cresce (mais vasoconstricao e mais taquicardia),
    logo o lado direito e' monotonicamente decrescente em `erro` e a raiz e'
    unica: resolvemos por bisseccao em [0, 1]. Iteracao amortecida tambem
    funcionaria, mas fica instavel no "joelho" onde o reflexo satura.

    Devolve o dict de `regime_estavel` acrescido de r_rel, hr_rel, mu_rel,
    erro residual, iteracoes e a oferta de oxigenio.
    """
    if pam_ref is None:
        pam_ref = PAM_REF
    b = windkessel_do_bebe(peso)
    SV = sv_de_volume(V, V_ref, b["SV0"])            # 5.1
    mu_rel = viscosidade_relativa(Hct)               # 5.2

    def estado(erro):
        r_rel, hr_rel = _resposta(erro, reserva)
        R = b["R0"] * mu_rel / r_rel ** 4            # Poiseuille: R ~ 1/r^4
        e = regime_estavel(b["HR0"] * hr_rel, SV, R, b["C"], b["Pv"])
        e.update(r_rel=r_rel, hr_rel=hr_rel, mu_rel=mu_rel)
        return e

    def residuo(erro):                               # > 0 -> falta compensar
        return max(0.0, (pam_ref - estado(erro)["PAM"]) / pam_ref) - erro

    n = 0
    if residuo(0.0) <= 0.0:                          # PAM ja esta no alvo
        erro = 0.0
    else:
        baixo, alto = 0.0, 1.0
        for n in range(1, P.ITER_MAX + 1):
            meio = 0.5 * (baixo + alto)
            if residuo(meio) > 0.0:
                baixo = meio
            else:
                alto = meio
            if alto - baixo < P.TOL:
                break
        erro = 0.5 * (baixo + alto)

    e = estado(erro)
    e.update(erro=erro, iteracoes=n,
             **oferta_oxigenio(Hct, e["DC"], peso))
    return e


# ------------------------------------------------- 5.4 oferta de oxigenio

def oferta_oxigenio(Hct, DC, peso):
    """Hb [g/dL], CaO2 [mL O2/dL], DO2 [mL O2/min] e DO2 por kg."""
    Hb = Hct * 100.0 * P.HB_POR_HCT
    CaO2 = P.K_HB * Hb * P.SAO2 + P.K_O2_DISS * P.PAO2
    DO2 = DC * CaO2 / 100.0
    return dict(Hb=Hb, CaO2=CaO2, DO2=DO2, DO2_kg=DO2 / peso)


# ------------------------------------------------- escala de dias

CHAVES_SERIE = ("PAS", "PAD", "PAM", "PP", "R", "HR", "SV", "DC",
                "DO2", "DO2_kg", "Hb", "r_rel", "hr_rel", "erro", "iteracoes")


def serie_hemodinamica(r, reserva):
    """Abordagem quase estatica: para cada passo do balanco (arquivo 02),
    calcula o regime estavel do Windkessel com o SV, R e HR daquele instante.

    Nao integramos segundos ao longo de semanas -- a cada hora resolvemos a
    forma fechada do arquivo 01.
    """
    out = {k: [] for k in CHAVES_SERIE}
    for V, V_ref, Hct, peso in zip(r["V"], r["V_ref"], r["Hct"], r["peso"]):
        e = hemodinamica(V, V_ref, Hct, peso, reserva)
        for k in CHAVES_SERIE:
            out[k].append(e[k])
    s = {k: np.array(v) for k, v in out.items()}
    baixa = s["PAM"] < (1.0 - P.QUEDA_PAM_REL) * PAM_REF
    s["dias_pam_baixa"] = baixa.sum() * P.DT_H / 24.0
    return s


# ------------------------------------------------- referencia basal

def estado_basal(peso=P.PESO0, Hct=P.HCT0):
    """Bebe no peso inicial, volume cheio e Hct inicial, sem compensacao."""
    V_ref = volume_referencia(peso)
    b = windkessel_do_bebe(peso)
    e = regime_estavel(b["HR0"], sv_de_volume(V_ref, V_ref, b["SV0"]),
                       b["R0"] * viscosidade_relativa(Hct), b["C"], b["Pv"])
    e.update(**oferta_oxigenio(Hct, e["DC"], peso))
    return e


PAM_REF = estado_basal()["PAM"]       # mmHg -- alvo do barorreflexo


if __name__ == "__main__":
    e0 = estado_basal()
    print(f"basal: PAS/PAD {e0['PAS']:.0f}/{e0['PAD']:.0f}  "
          f"PAM {e0['PAM']:.1f} mmHg  DC {e0['DC']:.0f} mL/min  "
          f"DO2 {e0['DO2']:.1f} mL/min ({e0['DO2_kg']:.1f} /kg)")
    print(f"PAM_REF = {PAM_REF:.2f} mmHg\n")

    V_ref = volume_referencia(P.PESO0)
    print(f"{'perda':>6s} {'reserva':>14s} {'SV':>6s} {'HR':>6s} {'R':>7s} "
          f"{'PAM':>6s} {'DO2/kg':>7s}")
    for perda in (0.0, 1.0, 3.0, 6.0):
        for res in (P.RESERVA_ALTA, P.RESERVA_BAIXA):
            e = hemodinamica(V_ref - perda, V_ref, P.HCT0, P.PESO0, res)
            print(f"{perda:5.1f}mL {res['nome']:>14s} {e['SV']:6.2f} "
                  f"{e['HR']:6.1f} {e['R']:7.2f} {e['PAM']:6.1f} "
                  f"{e['DO2_kg']:7.1f}")
