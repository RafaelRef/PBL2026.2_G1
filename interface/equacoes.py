# -*- coding: utf-8 -*-
"""equacoes.py -- cada valor da tela com a formula que o produziu.

A interface mostra, ao clicar num numero, a equacao em simbolos e a mesma
equacao com os valores substituidos. As duas sao montadas AQUI, ao lado do
calculo, e nao no HTML: assim nao existe a chance de a tela exibir uma
formula e o modelo rodar outra.

Cada entrada e' um dict:
    simbolo      nome curto da grandeza        "V_ref"
    formula      em simbolos                   "V_ref = vol_kg . peso"
    substituida  com os numeros no lugar       "V_ref = 85 . 0.95"
    resultado    o valor, formatado            "80.75"
    unidade      "mL"
    onde         arquivo e funcao de origem    "fisiologia.volume_referencia"
"""

import sys
from pathlib import Path

_SIM = Path(__file__).resolve().parent.parent / "simuladores"
if str(_SIM) not in sys.path:
    sys.path.insert(0, str(_SIM))

import parametros as P


def n(x, casas=2):
    """Numero curto, sem zeros a toa."""
    t = f"{x:.{casas}f}"
    return t.rstrip("0").rstrip(".") if "." in t else t


def eq(simbolo, formula, substituida, resultado, unidade="", onde=""):
    return dict(simbolo=simbolo, formula=formula, substituida=substituida,
                resultado=resultado, unidade=unidade, onde=onde)


def montar(e, h, pac, peso0, b, hct_crit, L, disponivel, coletado_24h,
           transfusao, ig):
    """Todas as equacoes da tela do paciente.

    e    estado do balanco (06_recomendacao.estado_de)
    h    estado hemodinamico (fisiologia.hemodinamica)
    b    parametros RC do bebe (fisiologia.windkessel_do_bebe)
    L    as tres regras (06_recomendacao.limites)
    """
    peso, V, M, V_ref, Hct = e["peso"], e["V"], e["M"], e["V_ref"], e["Hct"]
    dia = e["dia"]
    T = 60.0 / h["HR"]
    Vu = P.FU * V_ref

    return {
    # ---------------------------------------------------------- crescimento
    "peso": eq("peso", "peso(t) = peso₀ · e^(ganho/1000 · t)",
        f"peso = {n(peso0)} · e^({n(P.GANHO_PESO,0)}/1000 · {n(dia,1)})",
        n(peso), "kg", "fisiologia.peso_no_dia"),

    "V_ref": eq("V_ref", "V_ref = vol_kg · peso",
        f"V_ref = {n(P.VOL_POR_KG,0)} · {n(peso)}",
        n(V_ref, 1), "mL", "fisiologia.volume_referencia"),

    "V": eq("V", "dV/dt = (V_ref − V)/τ   − coletas  + transfusões",
        f"τ = {n(P.TAU_V,0)} h se V < V_ref, {n(P.TAU_EXCRECAO,0)} h se V > V_ref"
        f"   ·   integrado de hora em hora desde o nascimento",
        n(V, 1), "mL", "02_balanco_volume_hemacias.simular"),

    "M": eq("M", "dM/dt = produção − destruição   − coleta · Hct  + transf · Hct_bolsa",
        f"destruição = M/{n(P.VIDA_HEMACIA,0)} por dia"
        f"   ·   produção = destruição basal · ({n(P.FRAC_PROD_BASAL)} + "
        f"{n(P.GANHO_PROD)} · déficit de Hct), teto {n(P.PROD_MAX)}",
        n(M, 2), "mL", "02_balanco_volume_hemacias"),

    # ---------------------------------------------------------- hematocrito
    "Hct": eq("Hct", "Hct = M / V",
        f"Hct = {n(M,2)} / {n(V,2)}", n(Hct, 3), "", "02_balanco"),

    "hct_limiar": eq("Hct_crit",
        "Hct_crit = interpolação linear por semana de vida",
        _interp_texto(dia / 7.0, P.HCT_CRIT_SEMANAS, P.HCT_CRIT_VALORES),
        n(hct_crit, 3), "", "fisiologia.hct_critico"),

    # ---------------------------------------------------------- as tres regras
    "disponivel": eq("disp", "disp = min(R₁, R₂, R₃)",
        f"disp = min({n(L['janela_24h'])}; {n(L['hct'])}; {n(L['volume'])})",
        n(max(0.0, disponivel)), "mL", "06_recomendacao.volume_disponivel"),

    "regra_24h": eq("R₁", "R₁ = frac_24h · V_ref − coletado nas 24 h",
        f"R₁ = {n(P.FRAC_MAX_24H)} · {n(V_ref,1)} − {n(coletado_24h)}",
        n(L["janela_24h"]), "mL", "06_recomendacao.limites"),

    "regra_hct": eq("R₂", "R₂ = (M − Hct_crit · V_ref) / Hct",
        f"R₂ = ({n(M,2)} − {n(hct_crit,3)} · {n(V_ref,1)}) / {n(Hct,3)}",
        n(L["hct"]), "mL", "06_recomendacao.limites"),

    "regra_volume": eq("R₃", "R₃ = V − (1 − margem) · V_ref",
        f"R₃ = {n(V,2)} − (1 − {n(P.MARGEM_VOLUME)}) · {n(V_ref,1)}",
        n(L["volume"]), "mL", "06_recomendacao.limites"),

    # ---------------------------------------------------------- hemodinamica
    "SV": eq("SV", "SV = SV₀ · (V − Vu)/(V_ref − Vu),  Vu = fu · V_ref",
        f"SV = {n(b['SV0'],3)} · ({n(V,2)} − {n(Vu,2)})/({n(V_ref,2)} − {n(Vu,2)})",
        n(h["SV"], 3), "mL", "fisiologia.sv_de_volume"),

    "R": eq("R", "R = R₀ · μ_rel / r_rel⁴",
        f"R = {n(b['R0'],2)} · {n(h['mu_rel'],3)} / {n(h['r_rel'],3)}⁴",
        n(h["R"], 2), "mmHg·s/mL", "fisiologia.hemodinamica"),

    "mu_rel": eq("μ_rel", "μ_rel = f + (1 − f) · Hct/Hct₀",
        f"μ_rel = {n(P.MU_PLASMA_REL)} + (1 − {n(P.MU_PLASMA_REL)}) · "
        f"{n(Hct,3)}/{n(P.HCT0)}",
        n(h["mu_rel"], 3), "", "fisiologia.viscosidade_relativa"),

    "PAM": eq("PAM", "PAM = Pv + R · SV · HR/60",
        f"PAM = {n(h['Pv'],0)} + {n(h['R'],2)} · {n(h['SV'],3)} · "
        f"{n(h['HR'],1)}/60",
        n(h["PAM"], 1), "mmHg", "01_windkessel_base.regime_estavel"),

    "PAS": eq("PAS", "PAS = Pv + (SV/C) / (1 − e^(−T/τ)),  τ = R·C",
        f"PAS = {n(h['Pv'],0)} + ({n(h['SV'],3)}/{n(h['C'],3)}) / "
        f"(1 − e^(−{n(T,3)}/{n(h['tau'],3)}))",
        n(h["PAS"], 0), "mmHg", "01_windkessel_base.regime_estavel"),

    "PAD": eq("PAD", "PAD = Pv + (PAS − Pv) · e^(−T/τ)",
        f"PAD = {n(h['Pv'],0)} + ({n(h['PAS'],1)} − {n(h['Pv'],0)}) · "
        f"e^(−{n(T,3)}/{n(h['tau'],3)})",
        n(h["PAD"], 0), "mmHg", "01_windkessel_base.regime_estavel"),

    "DC": eq("DC", "DC = SV · HR",
        f"DC = {n(h['SV'],3)} · {n(h['HR'],1)}",
        n(h["DC"], 0), "mL/min", "01_windkessel_base.regime_estavel"),

    "DC_kg": eq("DC/kg", "DC/kg = DC / peso",
        f"DC/kg = {n(h['DC'],0)} / {n(peso)}",
        n(h["DC"] / peso, 0), "mL/kg/min", "clinico"),

    "pam_minima": eq("PAM_min", "PAM_min = IG · k",
        f"PAM_min = {n(ig,1)} · {n(P.PAM_POR_SEMANA_IG,0)}",
        n(ig * P.PAM_POR_SEMANA_IG, 0), "mmHg", "parametros"),

    # ---------------------------------------------------------- oxigenio
    "Hb": eq("Hb", "Hb = Hct · 100 · k_hb",
        f"Hb = {n(Hct,3)} · 100 · 1/3",
        n(h["Hb"], 1), "g/dL", "fisiologia.oferta_oxigenio"),

    "CaO2": eq("CaO₂", "CaO₂ = k_Hb · Hb · SaO₂ + k_diss · PaO₂",
        f"CaO₂ = {n(P.K_HB)} · {n(h['Hb'],1)} · {n(P.SAO2)} + "
        f"{P.K_O2_DISS} · {n(P.PAO2,0)}",
        n(h["CaO2"], 1), "mL O₂/dL", "fisiologia.oferta_oxigenio"),

    "DO2_kg": eq("DO₂/kg", "DO₂/kg = DC · CaO₂ / 100 / peso",
        f"DO₂/kg = {n(h['DC'],0)} · {n(h['CaO2'],1)} / 100 / {n(peso)}",
        n(h["DO2_kg"], 1), "mL O₂/min/kg", "fisiologia.oferta_oxigenio"),

    # ---------------------------------------------------------- transfusao
    "transf_volume": eq("v_transf", "v_transf = transf_kg · peso",
        f"v_transf = {n(P.TRANSF_ML_KG,0)} · {n(peso)}",
        n(transfusao["volume"], 1), "mL", "clinico.registrar_transfusao"),

    "transf_hct": eq("Hct_após",
        "Hct_após = (M + v · Hct_bolsa) / V_ref",
        f"Hct_após = ({n(M,2)} + {n(transfusao['volume'],1)} · "
        f"{n(P.HCT_CONCENTRADO)}) / {n(V_ref,1)}",
        n(transfusao["hct_depois"], 3), "", "clinico.avaliar"),
    }


def por_exame(chave, nome, volume, disponivel, L, hct_crit):
    """Equacoes dos tres numeros de cada cartao de exame."""
    import math
    return {
    "cabe_agora": eq("n_agora", "n = ⌊disp / v_exame⌋",
        f"n = ⌊{n(max(0.0, disponivel))} / {n(volume)}⌋",
        str(int(max(0.0, disponivel) // volume)), "", "clinico.avaliar"),
    "restante_24h": eq("n_24h", "n = ⌊R₁ / v_exame⌋",
        f"n = ⌊{n(max(0.0, L['janela_24h']))} / {n(volume)}⌋",
        str(int(max(0.0, L["janela_24h"]) // volume)), "", "clinico.avaliar"),
    "ate_hct_critico": eq("n_crit", "n = ⌊R₂ / v_exame⌋",
        f"n = ⌊{n(max(0.0, L['hct']))} / {n(volume)}⌋",
        str(int(max(0.0, L["hct"]) // volume)), "", "clinico.avaliar"),
    }


def _interp_texto(x, xs, ys):
    """Mostra entre quais ancoras a interpolacao caiu."""
    if x <= xs[0]:
        return f"{n(x,2)} sem ≤ {n(xs[0],0)} sem  →  patamar de {n(ys[0],3)}"
    if x >= xs[-1]:
        return f"{n(x,2)} sem ≥ {n(xs[-1],0)} sem  →  patamar de {n(ys[-1],3)}"
    for i in range(1, len(xs)):
        if x <= xs[i]:
            return (f"entre ({n(xs[i-1],0)} sem; {n(ys[i-1],3)}) e "
                    f"({n(xs[i],0)} sem; {n(ys[i],3)}), em {n(x,2)} sem")
    return ""
