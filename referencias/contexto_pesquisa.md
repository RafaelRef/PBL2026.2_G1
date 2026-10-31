# Contexto do projeto — PBL 2026.2, Grupo 1 (UTI Neonatal)

> Documento de passagem de contexto. Reúne o estado do projeto, o modelo
> matemático, os parâmetros em aberto e o que já foi verificado na literatura,
> para continuar a pesquisa em outra sessão.
> Última atualização: 27/10/2026.

---

## 1. O que é o projeto

Disciplina de **Simulação de Sistemas Biomédicos**. O grupo construiu uma prova
de conceito didática (não é ferramenta clínica) que simula o **impacto
hemodinâmico das coletas de sangue repetidas em um prematuro de UTI neonatal**,
percorrendo a cadeia:

```
coleta de sangue → volume e massa de hemácias → hemodinâmica → oferta de O₂
```

A espinha dorsal é o **Windkessel RC de 2 elementos** visto na disciplina. Todo
o resto são acoplamentos pendurados nele.

**Perguntas de pesquisa:**

1. Qual estratégia de coleta minimiza o impacto acumulado?
2. Como a reserva cardiovascular modifica a resposta à perda sanguínea?

**Paciente de referência:** prematuro de ~27 semanas, 0,80 kg, Hct inicial 0,45,
seguido por 28 dias.

---

## 2. O modelo

### 2.1 Windkessel RC de 2 elementos (modelo 0D de parâmetros concentrados)

A árvore arterial é um circuito RC: a complacência **C** é o capacitor que
armazena o volume ejetado; a resistência periférica total **R** é o resistor por
onde o sangue escoa para a microcirculação.

A implementação adotada é a de **trem de impulsos**, sem integrador numérico:

1. **Batimento** — a cada `T = 60/HR` segundos o volume sistólico entra de uma
   vez e a pressão sobe em degrau:  `ΔP = SV / C`
2. **Entre batimentos** — o capacitor descarrega pela resistência, exato:
   `P(t) = Pv + (P₀ − Pv)·e^(−t/τ)`, com **τ = R·C**

Em regime periódico isso fecha em forma analítica, sem simular ciclos até
estabilizar. Igualando o que sobe num batimento ao que desce até o próximo
(`A = PAS − Pv`, `B = PAD − Pv`; `A = B + ΔP` e `B = A·e^(−T/τ)`):

```
PAS = Pv + (SV/C) / (1 − e^(−T/τ))
PAD = Pv + (PAS − Pv)·e^(−T/τ)
PAM = Pv + R·SV/T          (exata no modelo linear; independe da forma do pulso)
```

**Consequência conhecida e assumida:** como a ejeção é instantânea, a PAS e a
pressão de pulso saem **superestimadas** (PP = SV/C = 58 mmHg no adulto, contra
~40 reais). Na fisiologia a ejeção dura ~1/3 do ciclo e o sangue já começa a
escoar enquanto entra. A **PAM não sofre** desse erro.

### 2.2 Poiseuille — como a resistência muda

```
R = 8·μ·L / (π·r⁴)
```

Dois mecanismos independentes entram no modelo por essa equação:

- **raio r** (quarta potência, denominador) → drogas vasoativas e barorreflexo.
  Alavancagem enorme: raio pela metade = resistência 16×.
- **viscosidade μ** (numerador, linear) → hematócrito. No código,
  `μ = μ_plasma · exp(K_MU · Hct)` com `K_MU = 2.5`.

### 2.3 Acoplamentos (arquivo `fisiologia.py`)

| § | Caminho | Forma |
|---|---|---|
| 5.1 | volume → SV | Frank-Starling linearizado, volume não estressado `Vu = 0,70·V_ref`, teto `SV/SV₀ ≤ 1,20` |
| 5.2 | Hct → μ → R | Poiseuille em forma relativa |
| 5.3 | PAM → r, HR | barorreflexo proporcional estático; ponto fixo por **bissecção** (R depende de PAM e PAM depende de R) |
| 5.4 | Hct e DC → DO₂ | `DO₂ = DC · (1,34·Hb·SaO₂ + 0,003·PaO₂)` |

### 2.4 Balanço de volume e hemácias (escala de dias, passo 1 h)

Duas variáveis de estado: `V` (volume sanguíneo) e `M` (volume de hemácias),
com `Hct = M/V`.

**Ponto fisiológico central do projeto:** depois de uma coleta o **volume** volta
a `V_ref` em horas (`TAU_V = 6 h`), mas a **massa de hemácias** só volta por
eritropoiese (lenta) ou transfusão. Curto prazo = problema de volume; longo
prazo = problema de hematócrito. O Hct **não cai na hora da coleta** (sai sangue
inteiro) — cai horas depois, quando o volume retorna como plasma e dilui as
hemácias que foram embora.

---

## 3. Parâmetros atuais

### Windkessel (`parametros.py`)

| | HR [bpm] | SV [mL] | C [mL/mmHg] | R [mmHg·s/mL] | Pv [mmHg] | τ = RC |
|---|---|---|---|---|---|---|
| Adulto | 70 | 70 | 1,20 | 1,0 | 5,0 | 1,20 s |
| Neonato (a termo, ~3,5 kg) | 140 | 5 | 0,13 | 3,6 | 3,0 | 0,47 s |

O prematuro de 0,8 kg **não** usa esses valores crus: `fisiologia.windkessel_do_bebe()`
reescala pelo volume sanguíneo (SV e C crescem com o volume, R cai na mesma
proporção), preservando τ e a PAM basal e dando DC ≈ 200 mL/kg/min. Aplicar os
valores do neonato a termo a 0,8 kg daria DC de 875 mL/kg/min, ~4× o fisiológico.

### Demais (todos marcados `TODO` no código = precisam de conferência)

```
PESO0 = 0,80 kg          VOL_POR_KG = 85 mL/kg      HCT0 = 0,45
VIDA_HEMACIA = 45 dias   FRAC_PROD_BASAL = 0,60     PROD_MAX = 1,20
TAU_V = 6 h              VOL_COLETA = 0,80 mL       VOL_COLETA_MICRO = 0,30 mL
HCT_LIMIAR = 0,30        TRANSF_ML_KG = 15 mL/kg    HCT_CONCENTRADO = 0,60
K_MU = 2,5               FRAC_MAX_24H = 0,03        SaO₂ = 0,92   PaO₂ = 60 mmHg
```

---

## 4. Arquivos e resultados obtidos

> Os arquivos `.py` citados abaixo ficam em `simuladores/` desde a reorganização do repositório;
> o `03` e o `06` estão em `simuladores/proximos_passos/`, e o `04` foi removido (continua no histórico do Git).

| Arquivo | O que faz |
|---|---|
| `parametros.py` | todos os números, com unidade e comentário |
| `comum.py` | carrega os arquivos numerados (`import 01_...` é sintaxe inválida) e salva figuras |
| `fisiologia.py` | os acoplamentos da seção 2.3 |
| `01_windkessel_base.py` | modelo RC base, adulto vs neonato; expõe `regime_estavel` |
| `02_balanco_volume_hemacias.py` | V(t), M(t), Hct(t) por 28 dias com coletas e transfusões |
| `03_coleta_aguda_windkessel.py` | efeito agudo de 1 mL e 3 mL, escala de segundos |
| `04_acoplamento_dias.py` | acopla as duas escalas; reserva alta vs baixa |
| `05_estrategias_coleta.py` | compara estratégias A/B/C/D |
| `06_recomendacao.py` | quanto ainda dá para coletar e quando dará |

**Resultados principais:**

`01` — Adulto 119/61, PAM 86,7, τ 1,20 s. Neonato 67/29, PAM 45,0, τ 0,47 s.

`03` — Coleta de 3 mL no prematuro: PAM cai 3,3% com reserva alta, **13,7% sem
barorreflexo**.

`04` — 28 dias de rotina: **R cai 45%** ao longo do mês — a queda do hematócrito
derruba a viscosidade mais do que o barorreflexo compensa estreitando o vaso. E
como PAM = Pv + R·DC, a anemia por si só já puxa a pressão para baixo. Dias com
PAM baixa: 14,8 (reserva alta) vs 25,4 (reserva baixa).

`05` — Estratégias (reserva baixa):

| | Estratégia | Punções | Coletado | % V₀ | Transf. | 1ª transf. | Hct dia 28 |
|---|---|---|---|---|---|---|---|
| A | Rotina | 28 | 22,4 mL | 32,9% | 2 | dia 11,8 | 0,366 |
| B | Agrupada | 21 | 18,2 mL | 26,8% | 2 | dia 13,7 | 0,387 |
| C | Micrométodo | 28 | **8,4 mL** | 12,4% | **1** | **dia 17,6** | 0,319 |
| D | Guiada | 28 | 18,9 mL | 27,8% | 2 | dia 13,4 | **0,386** |

Os 32,9% de V₀ em 28 dias da estratégia A são da ordem dos **28,5%** relatados
por Counsilman et al. (2019) em prematuros < 28 semanas.

**Verificações de sanidade que o código imprime:** PAM fechada vs média numérica
(~1e-5 mmHg); resíduo dos balanços de V e M (~1e-13 mL); PAM = Pv + R·DC em todos
os passos (~1e-14 mmHg).

---

## 5. O que já foi verificado na literatura

### 5.1 O Windkessel RC é válido para neonato? — **Sim, para a diástole**

**Evidência direta em prematuros.** Tese de doutorado de Ying Zhang (Nepean
Hospital, Sydney): 27 prematuros com IG 26,7 ± 1,8 semanas e peso 1010 ± 346 g,
pressão intra-arterial por cateter umbilical/periférico, 89 medidas nas
primeiras 36 h de vida. Ajuste exponencial do decaimento diastólico batimento a
batimento:

> "The individual exponential fit to the ABP pulses displayed high R² (0.99 ±
> 0.01), which provided justification of the Windkessel model for the analysis
> of pressure waveforms in infants."

**E o argumento inverte a crítica habitual:**

> "It has been suggested that in normal adults, the presence of arterial pulse
> wave reflection may affect the accuracy of the Windkessel model. However, it
> appears that in the preterm infants, wave reflection is not prominent as the
> arterial pulses often do not display clear secondary peaks. This may explain
> the good fit achieved by a simple Windkessel model."

Ou seja: a principal fraqueza do WK de 2 elementos no adulto (ignorar reflexão
de onda e impedância característica, que motiva os modelos de 3 e 4 elementos)
**pesa menos no neonato**, cuja árvore arterial é curta demais para gerar
reflexão significativa. O modelo RC é, em princípio, *mais* adequado ao neonato
que ao adulto.

*Ressalvas:* é tese, não artigo revisado por pares; e o ajuste usou só o **último
terço** da curva diastólica — a parte mais achatada —, o que infla o R² por
construção.

### 5.2 Invariância τ/T — e um provável erro no C do neonato

Burattini & Di Salvia (2007), *J Appl Physiol*, interpretaram impedância aórtica
de 0,8 a 54 anos com Windkessel de 4 elementos:

> "rapid reduction of Rd/Rp during early development is functional to modulation
> of decay time constant (taud) of pressure in diastole, such that
> **normalization over heart period (taud/T) is independent of body size**."

Aplicando aos parâmetros do projeto:

| | τ | T | **τ/T** |
|---|---|---|---|
| Adulto | 1,20 s | 0,857 s | **1,40** |
| Neonato | 0,468 s | 0,429 s | **1,09** |

Deveriam ser próximos; estão 28% distantes. Para igualar a razão do adulto, o
neonato precisaria de **C ≈ 0,17 mL/mmHg** (τ = 0,60 s) em vez de 0,13. Dois
indícios independentes apontam na mesma direção: as constantes de tempo medidas
nos prematuros da tese ficaram entre **0,8 e 2,3 s** (taxas de decaimento 0,2 a
1,8 Hz), bem acima de 0,47 s mesmo descontando que o método deles, por omitir Pv
no ajuste, superestima τ em ~13%. Isso também explica a PP exagerada do neonato
(38,5 mmHg; o normal a termo é 25–30 — com C = 0,17 cairia para 29).

**→ Pendência prioritária: rastrear a origem do C = 0,13 e decidir se corrige.**

### 5.3 A limitação específica de neonato que falta no modelo: canal arterial patente

O WK de 2 elementos assume que o **único** caminho de saída do capacitor é R. Um
**canal arterial patente (PDA)** abre um segundo caminho durante a diástole — o
*diastolic runoff* para a circulação pulmonar —, associado a pressão diastólica
baixa e, nos casos graves, inversão de fluxo na aorta descendente. Com dois
drenos em paralelo o decaimento deixa de ser a mono-exponencial para Pv que o
modelo prevê, e o τ ajustado não é mais R·C.

**Isso é crítico para este projeto:** o PDA é frequente exatamente na população
de prematuros simulada, e o modelo não o representa de forma alguma.

### 5.4 Modelos a parâmetros concentrados são prática corrente em neonatologia

Não é licença poética do grupo. Os modelos de referência da área são todos redes
RC concentradas: **Sá Couto et al. (2006)** para simulação educacional da
fisiologia cardiovascular neonatal, estendido para a **transição hemodinâmica ao
nascimento (2010)** e escalonado para prematuro de 28 semanas e 1 kg por Dat
(2010) e Jennekens (2011); e os modelos feto-neonatais de **Pennati**. Revisão de
2023 na *WIREs Mech Dis* cobre o campo.

### 5.5 Referências já levantadas

- Ying Zhang — *Application of signal processing techniques in the assessment of
  clinical risks in preterm infants* (tese) — https://arxiv.org/pdf/1404.5725
- Burattini R, Di Salvia PO — *Development of systemic arterial mechanical
  properties from infancy to adulthood interpreted by four-element windkessel
  models*, J Appl Physiol 2007 — https://pubmed.ncbi.nlm.nih.gov/17303709
- Westerhof N et al. — *The arterial Windkessel*, Med Biol Eng Comput 2009 —
  doi:10.1007/s11517-008-0359-2
- *Multiscale Modeling Is Required for the Patent Ductus Arteriosus in Preterm
  Infants* — https://pmc.ncbi.nlm.nih.gov/articles/PMC8984113/
- Sá Couto et al. — *A model for educational simulation of neonatal
  cardiovascular pathophysiology* — https://pubmed.ncbi.nlm.nih.gov/19088566/
- Sá Couto et al. — *A Model for Educational Simulation of Hemodynamic
  Transitions at Birth*, Pediatr Res 2010 — https://www.nature.com/articles/pr201029
- *From fetus to neonate: A review of cardiovascular modeling in early life*,
  WIREs Mech Dis 2023 — https://wires.onlinelibrary.wiley.com/doi/full/10.1002/wsbm.1608
- Counsilman et al. (2019) — perda sanguínea por coletas em prematuros < 28
  semanas (28,5% do volume) — *citado no projeto, referência completa ainda não
  conferida*

---

## 6. Limitações assumidas (já listadas na apresentação)

- WK de 2 elementos com sístole instantânea: superestima PAS e PP; a PAM é exata.
- Poiseuille aplicado à resistência periférica *total* é aproximação concentrada:
  não existe "um" vaso com "um" raio.
- Frank-Starling, barorreflexo e eritropoiese em forma linearizada e ilustrativa.
  O barorreflexo é proporcional e puramente estático — sem dinâmica, sem offset nulo.
- `μ = μ_plasma·exp(K_MU·Hct)`: R é linear em μ, mas não em Hct; a relação real
  é não linear de outra forma.
- A hemodinâmica **não realimenta** o balanço de volume e hemácias (quase
  estático). Por isso o Hct é idêntico nas duas reservas no arquivo `04`.
- Parâmetros ilustrativos (`TODO` no código).
- Ferramenta didática de comparação de cenários, não de decisão clínica.

---

## 7. Agenda de pesquisa — o que falta aprofundar

**Prioridade alta**

1. **C do neonato (0,13 mL/mmHg):** rastrear a fonte, confrontar com a
   invariância τ/T de Burattini e com valores medidos de complacência arterial
   total em RN a termo e prematuro. Decidir se corrige para ~0,17.
2. **Canal arterial patente:** quantificar o erro que a ausência do PDA introduz.
   Vale modelar como uma resistência em paralelo (`1/R_eff = 1/R + 1/R_PDA`)?
   Qual a prevalência de PDA hemodinamicamente significativo na faixa de 27
   semanas?
3. **Counsilman et al. (2019):** obter a referência completa e os números exatos,
   já que é a única validação externa do resultado do arquivo `05`.

**Prioridade média**

4. **Limiar de transfusão `HCT_LIMIAR = 0,30`:** confrontar com os ensaios
   clínicos ETTNO e TOP, que compararam limiares liberal vs restritivo em
   prematuros de extremo baixo peso.
5. **Viscosidade × hematócrito:** o fator `K_MU = 2,5` do exponencial. Procurar
   dados de viscosidade do sangue neonatal — hemoglobina fetal e Hct alto ao
   nascimento mudam a reologia em relação ao adulto.
6. **Eritropoiese / anemia da prematuridade:** `VIDA_HEMACIA = 45 dias` e
   `FRAC_PROD_BASAL = 0,60`. Há dados de sobrevida de hemácia fetal e de resposta
   de EPO no prematuro.
7. **`VOL_POR_KG = 85 mL/kg`:** valor para prematuro varia na literatura
   (80–100); checar dependência da idade gestacional e do clampeamento tardio.

**Prioridade baixa / extensões**

8. Comparar o WK de 2 elementos com o de 3 elementos no neonato — quanto muda a
   PAS/PP se a impedância característica entrar? (Esperado: pouco, dado 5.1.)
9. Limiar crítico de DO₂ no prematuro, para dar significado clínico ao eixo de
   oferta de oxigênio.
10. Circulação transicional (primeiras horas): RVP despencando e forame oval
    shuntando significam R não constante — o que o modelo já tem estrutura para
    representar.

---

## 8. Como pedir ajuda a partir daqui

O que seria mais útil agora, em ordem: (1) resolver a pendência do C com
referências sólidas; (2) decidir se o PDA entra no modelo ou vira limitação
declarada; (3) fechar as referências dos parâmetros marcados `TODO`, com valor,
faixa e fonte, para montar a tabela de parâmetros do relatório final.
