"""Parametros do simulador -- PBL 2026.2, Grupo 1 (UTI neonatal).

Todos os numeros do projeto moram aqui: nenhum arquivo 0X_*.py deve ter
constante numerica solta no meio do codigo.

Os valores sao ILUSTRATIVOS, escolhidos para dar a ordem de grandeza certa
numa prova de conceito didatica. Os marcados com TODO precisam de conferencia
na literatura antes de qualquer uso que nao seja de sala de aula.

Unidades:
  hemodinamica -> mL, mmHg, s
  internacao   -> mL, dias (o passo de integracao e' em horas)
"""

# ------------------------------------------------ Windkessel RC (secao 4)
# SV [mL], C [mL/mmHg], R [mmHg.s/mL], Pv [mmHg], HR [bpm]
ADULTO = dict(nome="Adulto", HR=70.0, SV=70.0, C=1.20, R=1.0, Pv=5.0,
              cor="#2a78d6")
# R calibrado para PAM basal de ~33 mmHg, o valor normativo ao nascer em
# prematuros <28 semanas (Vesoulis et al., 2016: 25.7 +- 1.5 sem, 865 +- 201 g,
# 11.9 milhoes de pontos por cateter umbilical). R e' o unico dos tres que se
# pode mexer sem estragar o resto: mexer em SV derrubaria o debito cardiaco
# para 143 mL/kg/min, fora da faixa neonatal de 200-230, e com ele a DO2.
NEONATO = dict(nome="Neonato", HR=140.0, SV=5.0, C=0.13, R=2.57, Pv=3.0,
               cor="#eb6834")
PACIENTES = [ADULTO, NEONATO]

# Peso implicito nos parametros NEONATO (neonato a termo). O prematuro do
# estudo pesa ~0.8 kg, entao SV/C/R sao reescalados pelo volume sanguineo
# (ver fisiologia.windkessel_do_bebe).
PESO_NEONATO_REF = 3.5        # kg                                     TODO

# ------------------------------------------------ paciente (escala de dias)
PESO0        = 0.80           # kg      prematuro de ~27 semanas
VOL_POR_KG   = 85.0           # mL/kg   volume sanguineo total          TODO
GANHO_PESO   = 15.0           # g/kg/dia  ganho de peso alvo            TODO
HCT0         = 0.45           # -       hematocrito inicial

# ------------------------------------------------ hemacias (eritropoiese)
# VIDA MEDIA, nao meia-vida: a destruicao e' M/VIDA_HEMACIA, sem o ln2. A
# meia-vida equivalente e' VIDA_HEMACIA * ln2 = 31 dias. Literatura para
# prematuro: 30-50 dias de sobrevida (termo 60-70, adulto 110-130); medidas
# diretas em ~26 semanas dao 56 +- 7 dias.
VIDA_HEMACIA   = 45.0         # dias    vida media (adulto ~120)
# Producao em fracao da destruicao basal (M0/VIDA_HEMACIA). E' insuficiente:
# manter o Hct durante o crescimento exigiria ~2.1x a destruicao basal, e o
# teto PROD_MAX apenas empata com a destruicao -- nunca faz M crescer.
FRAC_PROD_BASAL = 0.60        # -       producao basal / destruicao basal  TODO
# Referencia medida para conferir a calibracao acima: Kuruvilla et al. (2016)
# acharam producao de Hb de 0.23 +- 0.12 g/kg/dia no 1o mes, em 79 prematuros
# de peso medio 0.768 kg -- praticamente o paciente de referencia daqui.
PROD_HB_MEDIDA = 0.23         # g/kg/dia  Kuruvilla et al. (2016)
PROD_HB_DESVIO = 0.12         # g/kg/dia
GANHO_PROD      = 2.00        # -       resposta lenta a (HCT0 - Hct)      TODO
PROD_MAX        = 1.20        # -       teto da producao

# ------------------------------------------------ volume
# Duas constantes, nao uma. O volume volta para V_ref por caminhos diferentes
# conforme esteja abaixo ou acima dele, e nao ha razao para serem iguais:
#
#   TAU_V       V < V_ref, depois de uma coleta. Refil transcapilar, rapido.
#   TAU_EXCRECAO  V > V_ref, depois de uma transfusao. Excrecao renal, lenta,
#                 e mais lenta ainda no prematuro, de funcao renal imatura.
#                 E' por isso que sobrecarga de volume e' risco real da
#                 transfusao -- com um tau unico de 6 h, esse risco sumia em
#                 24 h no modelo.
#
# Com TAU_EXCRECAO = TAU_V o comportamento volta a ser o de antes.      TODO
TAU_V        = 6.0            # h       reposicao apos coleta
TAU_EXCRECAO = 24.0           # h       excrecao do excesso apos transfusao

# ------------------------------------------------ coletas
VOL_COLETA        = 0.80      # mL      coleta de rotina                TODO
VOL_COLETA_AGUDA  = (1.0, 3.0) # mL     volumes ilustrados no arquivo 05
HORAS_DEPOIS      = 6.0        # h      "algumas horas depois" no arquivo 05
VOL_COLETA_MICRO  = 0.50      # mL      micrometodo
FATOR_AGRUPAMENTO = 0.25      # -       custo extra por exame extra na mesma puncao

# ------------------------------------------------ exames (interface clinica)
# Volume de sangue por puncao, em mL. Sao os tres exames que a interface
# web oferece ao medico.                                          TODO
EXAMES = {
    "gasometria": dict(nome="Gasometria", volume=0.50),
    "hemograma":  dict(nome="Hemograma",  volume=1.00),
    "glicemia":   dict(nome="Glicemia",   volume=0.05),
}

# ------------------------------------------------ interface web
# Marca. O nome ainda pode mudar -- trocar aqui muda a interface inteira.
APP_NOME_1    = "BabyCare"            # parte em verde do logotipo
APP_NOME_2    = "Hemo"                # parte em vermelho
APP_SUBTITULO = "simulador de coletas de sangue em prematuros"
APP_RODAPE    = "PBL 2026.2 \u00b7 Grupo 1 \u00b7 UTI neonatal"

# Paleta (imagem de identidade visual do grupo)
COR_FUNDO_TIFFANY   = "#DDF4F1"
COR_TIFFANY_CLARO   = "#E3F6F3"
COR_VERDE_TIFFANY   = "#9EDFD7"
COR_AZUL_BEBE_CLARO = "#E6F2FC"
COR_AZUL_BEBE       = "#CFE6F8"
COR_ROSA_CLARO      = "#FDEBF0"
COR_ROSA            = "#F5B3C6"
COR_SANGUE          = "#D7263D"       # gotinha do logotipo
COR_VERDE_ESCURO    = "#123F38"       # texto do logotipo

HOST          = "127.0.0.1"   # so local: e' uma prova de conceito didatica
PORTA         = 8000
ARQUIVO_DADOS = "dados_clinicos.json"
PBKDF2_ITER   = 200_000       # iteracoes do hash de senha
SESSAO_HORAS  = 8.0           # validade do token de sessao

# ------------------------------------------------ transfusao
HCT_LIMIAR      = 0.30        # -       limiar de indicacao             TODO
                              #         valor unico, usado pelos arquivos
                              #         numerados. A interface clinica usa
                              #         fisiologia.hct_critico(peso), abaixo.

# Limiar da interface clinica: varia com a IDADE POS-NATAL e com o SUPORTE
# RESPIRATORIO, como na diretriz Deschmann et al. (2024), JAMA Netw Open,
# que o relatorio ja cita. A diretriz publica limiares de HEMOGLOBINA por
# semana; convertidos para hematocrito com HB_POR_HCT (Hb[g/dL] = Hct%/3):
#
#   semana      Hb sem suporte -> Hct      Hb com suporte -> Hct
#      1          10.0 g/dL       0.300       11.0 g/dL      0.330
#      2           8.5 g/dL       0.255       10.0 g/dL      0.300
#      3           7.0 g/dL       0.210        9.0 g/dL      0.270
#
# A diretriz e' DISCRETA por semana; aqui interpolamos linearmente para o
# limiar nao dar saltos no meio da projecao hora a hora de 06_recomendacao.
# Fora das pontas vira patamar (antes da semana 1 e depois da semana 3).
HCT_CRIT_SEMANAS      = (1.0, 2.0, 3.0)       # semana de vida
HCT_CRIT_SEM_SUPORTE  = (0.300, 0.255, 0.210) # -   ar ambiente
HCT_CRIT_COM_SUPORTE  = (0.330, 0.300, 0.270) # -   em suporte respiratorio
MARGEM_HCT      = 0.03        # -       folga que a estrategia guiada mantem
                              #         acima do limiar (nao coletar o
                              #         paciente ate a transfusao)
TRANSF_ML_KG    = 15.0        # mL/kg   volume do concentrado
HCT_CONCENTRADO = 0.60        # -       hematocrito do concentrado

# ------------------------------------------------ simulacao
DIAS  = 28                    # dias
DT_H  = 1.0                   # h       passo do balanco

# ------------------------------------------------ 5.1 Frank-Starling
FU         = 0.70             # -       Vu = FU * V_ref (volume nao estressado)
SV_REL_MAX = 1.20             # -       teto de SV/SV0

# ------------------------------------------------ 5.2 viscosidade (Poiseuille)
# A forma exponencial mu = mu_plasma.exp(K_MU.Hct) so foi confirmada em
# recem-nascidos ACIMA de Hct 42% (Pediatrics, 1984, 93 amostras). O modelo
# percorre 45% -> 30%, ou seja, quase toda a simulacao acontece abaixo dessa
# fronteira. Na faixa de interesse a relacao e' praticamente linear: num
# estudo em prematuros a viscosidade acompanhou o Hct com r = 0.877 entre
# 29% e 63%.
#
# Usamos entao a forma linear  mu(Hct) = mu_plasma + (mu_ref - mu_plasma).Hct/HCT0,
# parametrizada pela fracao do plasma na viscosidade do sangue de referencia:
#   MU_PLASMA_REL = mu_plasma / mu_sangue(HCT0)
# com plasma neonatal ~1.18 cP (adulto 1.36) e sangue a Hct 45% ~4.2 cP. TODO
MODELO_VISCOSIDADE = "linear"  # "linear" (padrao) ou "exponencial"
MU_PLASMA_REL = 0.28          # -       mu_plasma / mu_sangue(HCT0)      TODO
K_MU = 2.5                    # -       so usado se MODELO_VISCOSIDADE = exponencial

# ------------------------------------------------ 5.3 barorreflexo
# g_r  -> vasoconstricao (reduz o raio)
# g_hr -> taquicardia
SEM_COMPENSACAO = dict(nome="sem compensacao", g_r=0.0, g_hr=0.0, cor="0.55")
RESERVA_ALTA  = dict(nome="reserva alta",  g_r=0.80, g_hr=0.50, cor="#2a78d6")
RESERVA_BAIXA = dict(nome="reserva baixa", g_r=0.20, g_hr=0.10, cor="#eb6834")
QUEDA_PAM_REL = 0.05          # -       "PAM baixa" = 5% abaixo da referencia
R_REL_MIN  = 0.80             # -       r >= 0.80 * r0
HR_REL_MAX = 1.30             # -       HR <= 1.30 * HR0
ITER_MAX   = 60               # -       iteracoes do ponto fixo (bisseccao)
TOL        = 1e-10            # -       tolerancia no erro de PAM

# ------------------------------------------------ 5.4 oferta de oxigenio
SAO2       = 0.92             # -                                       TODO
PAO2       = 60.0             # mmHg                                    TODO
HB_POR_HCT = 1.0 / 3.0        # Hb [g/dL] ~ Hct(%) / 3
K_HB       = 1.34             # mL O2 / g Hb
K_O2_DISS  = 0.003            # mL O2 / dL / mmHg

# ------------------------------------------------ 06 recomendacao
FRAC_MAX_24H     = 0.03       # -   perda em 24 h <= 3% de V_ref        TODO
MARGEM_VOLUME    = 0.05       # -   V nao cair abaixo de (1-margem)*V_ref
HORIZONTE_ESPERA = 72         # h   ate onde procurar a proxima janela
DIA_EXEMPLO      = 6          # dia usado no exemplo impresso pelo arquivo 06
VOL_EXEMPLO      = 1.5        # mL  volume "grande" pedido no mesmo exemplo
ESPERA_MAX       = 24.0       # h   depois disso o exame sai no volume minimo

# ------------------------------------------------ figuras
N_BATIMENTOS = 4              # batimentos desenhados nas curvas de pressao
PONTOS       = 400            # pontos por decaimento
DPI          = 150
