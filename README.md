# PBL 2026.2 · Grupo 1 · UTI Neonatal

**Simulador do impacto hemodinâmico das coletas de sangue em prematuros.**

Prova de conceito didática que percorre a cadeia **coleta → volume e hemácias →
hemodinâmica → oferta de O₂**, usando o Windkessel RC de 2 elementos visto na
disciplina. Não é ferramenta clínica.

Perguntas de pesquisa que o código responde:

1. Qual estratégia de coleta minimiza o impacto acumulado? → `03`
2. Como a reserva cardiovascular modifica a resposta à perda sanguínea? → relatório final
   (o antigo arquivo de reserva alta vs baixa foi removido; está no histórico do Git)

---

## Estrutura do repositório

```
PBL2026.2_G1/
├── README.md
├── requirements.txt
├── app.py                           servidor da interface clínica (BabyCare Hemo)
├── interface/                       interface web para o médico
│   ├── interface.html               a tela (HTML/CSS/JS, sem dependência externa)
│   ├── marca.png                    logotipo do grupo (opcional; sem ele, um SVG embutido)
│   ├── clinico.py                   login, pacientes, coletas e as regras
│   ├── armazem.py                   onde os dados ficam: arquivo local ou Supabase
│   ├── supabase_db.py               cliente PostgREST (só biblioteca padrão)
│   └── esquema.sql                  tabelas a criar no Supabase
├── simuladores/                     código do simulador (Python)
│   ├── parametros.py                todos os números do projeto
│   ├── comum.py                     importação dos arquivos numerados e caminhos das figuras
│   ├── fisiologia.py                acoplamentos ao Windkessel
│   ├── 01_windkessel_base.py
│   ├── 02_balanco_volume_hemacias.py
│   ├── 03_estrategias_coleta.py
│   ├── 04_figuras_relatorio.py
│   ├── proximos_passos/             análises para o relatório final (05 e 06)
│   └── legado/                      protótipo anterior (intacto)
├── figuras/
│   ├── simuladores/                 figuras geradas pelos arquivos 01, 02, 03 e 05
│   └── relatorio_parcial/           figuras 1, 2 e 3 do relatório parcial (arquivo 04)
└── referencias/
    ├── referencias_bibliograficas.txt   lista ABNT do relatório + literatura de apoio
    └── contexto_pesquisa.md             estado do projeto e o que já foi conferido na literatura
```

## Arquivos de `simuladores/`

| Arquivo | O que faz | Figura |
|---|---|---|
| `parametros.py` | todos os números do projeto, com unidade e comentário | — |
| `comum.py` | importa os arquivos numerados e salva as figuras | — |
| `fisiologia.py` | adaptações ao Windkessel: pré-carga, viscosidade, barorreflexo, DO₂ | — |
| `01_windkessel_base.py` | modelo RC base, adulto vs neonato; expõe `regime_estavel` e `curva_batimentos` | `figuras/simuladores/01_...png` |
| `02_balanco_volume_hemacias.py` | V(t), M(t) e Hct(t) por 28 dias, com coletas e transfusões | `figuras/simuladores/02_...png` |
| `03_estrategias_coleta.py` | compara as estratégias A, B, C e D | `figuras/simuladores/03_...png` |
| `04_figuras_relatorio.py` | figuras 1, 2 e 3 do relatório parcial e números da Tabela 2, **sem compensação** | `figuras/relatorio_parcial/` |

**`simuladores/proximos_passos/`** — análises que não entram no relatório parcial:

| Arquivo | O que faz | Figura |
|---|---|---|
| `05_coleta_aguda_windkessel.py` | efeito agudo de 1 mL e 3 mL na escala de segundos, com e sem barorreflexo | `figuras/simuladores/05_...png` |
| `06_recomendacao.py` | volume disponível agora e espera até a próxima coleta (módulo de recomendação) | — |

O `06` também é usado pela estratégia D (guiada) do `03`; o `comum.importar` encontra
arquivos nas duas pastas.

Os arquivos `G1_arquivo1.py` e `G1_arquivo1_live.py` são o protótipo anterior e
ficaram intactos em `simuladores/legado/` — `01_windkessel_base.py` é a versão
refatorada, com o modelo exposto em funções reutilizáveis. O
`G1_arquivo1_live.py` é um monitor interativo (sliders de HR, SV, R e C, preset
adulto/neonato, batimento extra, pausa) e continua rodando sozinho:

```bash
python simuladores/legado/G1_arquivo1_live.py
```

As figuras de `figuras/` estão versionadas: dá para ver os resultados direto no
GitHub, sem rodar nada. `referencias/contexto_pesquisa.md` reúne o estado do
projeto, as pendências de parâmetro e o que já foi conferido na literatura.

## Rodar

```bash
cd ~/Desktop/PBL2026.2
source .venv/bin/activate        # sempre que abrir um terminal novo
python simuladores/01_windkessel_base.py     # idem para 02, 03 e 04
python simuladores/proximos_passos/05_coleta_aguda_windkessel.py   # idem para 06
```

Cada arquivo roda sozinho (de qualquer pasta), imprime sua tabela, salva a figura em
`figuras/simuladores/` (o `04` salva em `figuras/relatorio_parcial/`) e
abre a janela do matplotlib. Só numpy e matplotlib.

Setup do venv (uma vez):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
```

---

## Interface do médico — BabyCare Hemo

Os arquivos de `simuladores/` rodam no terminal e geram as figuras. A interface
web põe o **mesmo modelo** na mão de quem está à beira do leito:

```bash
source .venv/bin/activate
python app.py                    # abre http://127.0.0.1:8000 no navegador
python app.py --porta 8080 --sem-navegador
```

Fluxo: **login do médico → cadastro do paciente → lista → coletas**.

1. **Login.** No primeiro acesso, "Cadastrar médico". A senha nunca é guardada
   em texto: só o hash PBKDF2-SHA256 com salt por usuário.
2. **Novo paciente.** Nome, peso atual e semana de vida. O volume sanguíneo sai
   na hora de `fisiologia.volume_referencia`: `V_ref = 85 mL/kg`.
3. **Lista.** Peso, idade, volume, Hct de hoje, o limiar crítico daquele bebê e
   quanto ainda cabe coletar.
4. **Registrar coleta.** Três exames, com o volume de cada um (`P.EXAMES`):
   gasometria 0,50 mL, hemograma 1,00 mL, glicemia 0,05 mL. Para cada um a tela
   responde **quantas punções ainda cabem**:

   | Número | Significado |
   |---|---|
   | cabem agora | respeita as três regras do `06_recomendacao` ao mesmo tempo |
   | restam nas 24 h | só a janela móvel (perda ≤ 3% de `V_ref` por dia) |
   | até o Hct crítico | quantas até o Hct projetado cruzar o limiar do bebê |

   O botão **nunca** fica desabilitado: existe exame de urgência, e a decisão
   de furar o limite é do médico, não do modelo. Fora do limite ele fica
   vermelho e abre um aviso dizendo qual regra está travando, o Hct atual, o
   crítico daquele peso e quanto já saiu nas últimas 24 h. Confirmando, a
   coleta é registrada e **marcada como fora do limite** no histórico — o
   registro mostra que a decisão foi consciente.

5. **Transfusão.** Quando o Hct cai abaixo do crítico, a interface abre um
   modal perguntando se o médico quer transfundir. O modal mostra o volume
   (`TRANSF_ML_KG` mL/kg), o hematócrito do concentrado (`HCT_CONCENTRADO`) e
   os dois Hct esperados: logo depois, com o volume ainda expandido, e ao
   estabilizar, quando o volume volta a `V_ref`. Também há um botão para
   transfundir fora do limiar.

   O modelo **não** transfunde sozinho na interface: `simular` roda com
   `transfundir=False` e recebe em `agenda_transfusoes` só o que o médico
   aceitou. A regra automática continua existindo para os arquivos numerados.

### Dois botões que não existiriam num sistema real

- **Avançar o tempo** (`+1 / +7 / +14 dias`), na tela do paciente. Numa UTI
  quem anda é o calendário; isto existe porque numa apresentação de dez
  minutos ninguém espera duas semanas para ver o hematócrito cair. O valor
  fica em `pacientes.dias_extra` e é somado à idade real em
  `clinico._idade`. A tela mostra quantos dias já foram avançados.
- **Apagar paciente** (o `×` na lista), com confirmação. As coletas e
  transfusões somem junto — as chaves estrangeiras do `esquema.sql` têm
  `ON DELETE CASCADE`.

Dois gráficos acompanham o bebê desde o nascimento: o **hematócrito** contra a
curva do limiar crítico (faixa rosa = zona de transfusão) e o **volume
sanguíneo**, com `V_ref` subindo pelo crescimento e `V` caindo a cada punção e
voltando em algumas horas (`TAU_V`), repondo plasma e não hemácias.

A interface não tem modelo próprio: `clinico.py` traduz "paciente + coletas"
para `02_balanco_volume_hemacias.simular` e `06_recomendacao.limites`. Nenhuma
constante nova — tudo vem de `parametros.py`, inclusive o nome e a paleta da
marca (`APP_NOME_1`, `APP_NOME_2`, `COR_*`), que o servidor entrega em
`/api/config` e a página aplica por cima do CSS. Trocar o nome ou uma cor é
uma linha num arquivo só.

O logotipo é `interface/marca.png`, servido em `/marca.png`. Se o arquivo não
existir, a página desenha uma gotinha em SVG embutido — o site nunca aparece
sem marca.

**Como a idade entra na conta.** O médico informa o peso de hoje e a semana de
vida; o arquivo 02 integra desde o nascimento. Estimamos o peso ao nascer
invertendo o ganho de `GANHO_PESO` g/kg/dia e simulamos do dia 0 até hoje — é
isso que faz um bebê de 3 semanas já chegar com a queda fisiológica de Hct
acumulada, em vez de começar sempre em `HCT0`. A simulação roda com
`transfundir=False`: a tela **sinaliza** a indicação de transfusão em vez de
transfundir sozinha.

### Hematócrito crítico variável

Os arquivos numerados usam `HCT_LIMIAR = 0.30`, valor único. A interface usa
`fisiologia.hct_critico(peso)`, que interpola `HCT_CRIT_PESOS` e
`HCT_CRIT_VALORES`: quanto menor o bebê, menos reserva e mais alto o limiar.

| Peso | Hct crítico |
|---|---|
| ≤ 0,75 kg | 0,330 |
| 1,00 kg | 0,310 |
| 1,50 kg | 0,280 |
| ≥ 2,50 kg | 0,250 |

Como o peso cresce na internação, **o limiar cai com o tempo**. `06_recomendacao`
aceita um *callable* em `limite_Hct` para reavaliar o limiar a cada passo da
projeção, já que o bebê cresce durante ela.

> Âncoras marcadas `TODO`. A literatura (PINT, ETTNO) indexa o limiar pela
> **idade pós-natal** e pelo **suporte respiratório**, não pelo peso; aqui o
> peso entra como proxy de maturidade. Valores centrados em `HCT_LIMIAR` no
> peso de referência, para seguirem comparáveis aos dos arquivos numerados.

### Ajustes do modelo apos conferencia com a literatura

Tres parametros do relatorio parcial foram revistos contra as fontes:

| | Antes | Agora | Por que |
|---|---|---|---|
| PAM basal | 45 mmHg | **33 mmHg** | Vesoulis et al. (2016) mede ~33 mmHg ao nascer em <28 semanas. Calibrado por `R` do `NEONATO`, o unico que preserva o debito cardiaco em 200 mL/kg/min e, com ele, a DO2 |
| Viscosidade | `exp(K·Hct)` | **linear** | A forma exponencial so foi confirmada em recem-nascidos **acima** de Hct 42%; o modelo percorre 45% → 30%. Em prematuros a relacao e praticamente linear nessa faixa (r = 0,877 entre 29% e 63%) |
| Reposicao de volume | τ = 6 h nos dois sentidos | **τ = 6 h / 24 h** | O mesmo τ repunha volume apos a coleta **e** drenava o excesso apos a transfusao. Sao mecanismos diferentes: refil transcapilar e excrecao renal, esta lenta no prematuro |

`MODELO_VISCOSIDADE` alterna entre `"linear"` e `"exponencial"` para comparar
as duas formas; `TAU_EXCRECAO = TAU_V` devolve o comportamento antigo.

### Onde os dados ficam

`armazem.py` tem duas implementações com a mesma interface, e `escolher()`
decide sozinho:

| Quando | Armazém |
|---|---|
| sem `SUPABASE_URL` no ambiente | arquivo local `dados_clinicos.json` |
| com as chaves definidas | Postgres do Supabase (ver `interface/esquema.sql`) |

São quatro tabelas: `usuarios`, `pacientes`, `coletas` e `transfusoes`. O
arquivo é **idempotente** (`if not exists` em tudo), então rode-o de novo
sempre que ele mudar — ele também carrega as migrações de colunas novas
(`coletas.forcada`, `pacientes.dias_extra`). Rodar duas vezes não quebra nada.

Assim o projeto roda offline (apresentação sem internet) e hospedado, sem
trocar uma linha de `clinico.py`.

**Configurar o Supabase:** rode `interface/esquema.sql` no *SQL Editor* do
painel; copie *Project URL* e a chave **secreta** em *Project Settings → API*;
crie um `.env` na raiz (modelo em `.env.exemplo`, e o `.env` está no
`.gitignore`):

```
SUPABASE_URL=https://<id>.supabase.co
SUPABASE_SERVICE_KEY=<a chave secreta>
```

Conferir: `python interface/supabase_db.py`.

> A chave secreta ignora as políticas de RLS — só pode viver no servidor, nunca
> no `interface.html` nem num arquivo versionado. O `esquema.sql` liga RLS **sem
> criar política nenhuma**: o padrão vira "nega tudo", então a chave pública
> (que aparece em qualquer navegador) não lê nada.

### Hospedar no Render

*Web Service* apontando para este repositório:

| Campo | Valor |
|---|---|
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python app.py` |
| Environment | `SUPABASE_URL` e `SUPABASE_SERVICE_KEY` |

O `app.py` lê `PORT` e `HOST` do ambiente e força `MPLBACKEND=Agg` antes de
importar `clinico` — sem isso o matplotlib, que vem junto pelo arquivo 02,
trava num servidor sem tela.

> No Render o Supabase é obrigatório: o disco de lá é descartável e zera a cada
> deploy. No plano grátis o serviço hiberna após ~15 min sem acesso e demora
> ~1 min para acordar; as sessões de login ficam em memória, então todo deploy
> desloga todo mundo.

## Saída esperada

**`01` — Windkessel base** (os valores do README anterior, 58/33, estavam
errados; estes saem da solução fechada):

| | PAS/PAD | PAM | PP | τ | DC |
|---|---|---|---|---|---|
| Adulto | 119/61 | 86,7 mmHg | 58,3 mmHg | 1,20 s | 4900 mL/min |
| Neonato | 67/29 | 45,0 mmHg | 38,5 mmHg | 0,47 s | 700 mL/min |

**`05` — efeito agudo** (prematuro de 0,8 kg, V₀ = 68 mL). Repare que o Hct
**não muda** na hora da coleta: sai sangue inteiro. Ele só cai horas depois,
quando o volume volta como plasma e dilui as hemácias que foram embora.

| Coleta | Momento | PAM com reserva alta | PAM sem barorreflexo |
|---|---|---|---|
| 1 mL | logo após | 44,5 (−1,0%) | 42,9 (−4,6%) |
| 3 mL | logo após | 43,5 (−3,3%) | **38,8 (−13,7%)** |
| 3 mL | 6 h depois | 44,2 (−1,8%) | 41,5 (−7,8%) |

**`03` — estratégias** (reserva baixa, pior caso):

| | Estratégia | Punções | Coletado | % V₀ | Transf. | 1ª transf. | Hct dia 28 |
|---|---|---|---|---|---|---|---|
| A | Rotina | 28 | 22,4 mL | 32,9% | 2 | dia 11,8 | 0,366 |
| B | Agrupada | 21 | 18,2 mL | 26,8% | 2 | dia 13,7 | 0,387 |
| C | Micrométodo | 28 | **8,4 mL** | 12,4% | **1** | **dia 17,6** | 0,319 |
| D | Guiada | 28 | 18,9 mL | 27,8% | 2 | dia 13,4 | **0,386** |

O volume coletado na estratégia A (32,9% de V₀ em 28 dias) é da ordem dos
**28,5%** relatados por Counsilman et al. (2019) em prematuros < 28 semanas.

Verificações de sanidade impressas pelos arquivos:
`01` PAM fechada vs média numérica da curva (erro ~1e-5 mmHg);
`02` resíduo do balanço de V e de M (~1e-13 mL);
`fisiologia` PAM = Pv + R·DC em todos os passos (~1e-14 mmHg).

---

**`04` — figuras do relatório parcial** (sem compensação cardiovascular,
`P.SEM_COMPENSACAO`; por isso a PAM e o DO₂ diferem do arquivo `03`,
que usam reserva alta/baixa — as transfusões são iguais):

| Estratégia | Coletado | Transf. | 1ª transf. | PAM média | PAM mín | DO₂/kg mín |
|---|---|---|---|---|---|---|
| Sem coleta | 0,0 mL | 1 | dia 21,5 | 37,0 | 31,5 | 24,7 |
| A. Rotina | 22,4 mL | 2 | dia 11,8 | 35,9 | 30,7 | 24,0 |
| B. Agrupada | 18,2 mL | 2 | dia 13,7 | 36,1 | 30,7 | 24,0 |
| C. Micrométodo | 8,4 mL | 1 | dia 17,6 | 36,3 | 31,5 | 24,7 |
| D. Guiada | 18,9 mL | 2 | dia 13,4 | 35,6 | 31,2 | 24,5 |

---

## Decisões de modelagem

Pontos onde o código foi além — ou se afastou — do documento de proposta:

1. **Dois módulos de apoio além do `parametros.py`.** `import 01_windkessel_base`
   é sintaxe inválida em Python (nome de módulo não pode começar com dígito),
   então `comum.importar()` carrega os arquivos numerados pelo caminho. As
   adaptações da seção 5 ficaram em `fisiologia.py`, usadas por `03`, `04` e `05`.

2. **O prematuro não usa os parâmetros `NEONATO` crus.** Os valores
   `SV = 5 mL, C = 0,13, R = 3,6` correspondem a um neonato a termo
   (~3,5 kg): aplicados a 0,8 kg dariam um débito cardíaco de 875 mL/kg/min,
   cerca de 4× o fisiológico. `fisiologia.windkessel_do_bebe()` reescala pelo
   volume sanguíneo — SV e C crescem com o volume, R cai na mesma proporção —
   o que preserva τ e a PAM basal (45 mmHg) e dá DC ≈ 200 mL/kg/min. O
   `NEONATO` original continua intacto e é o que o arquivo `01` plota.

3. **Barorreflexo resolvido por bissecção, não por iteração amortecida.** Como
   PAM cresce monotonicamente com o erro (mais vasoconstrição, mais
   taquicardia), a equação de ponto fixo tem raiz única e a bissecção sempre
   converge. A iteração amortecida oscila no "joelho" onde o reflexo satura —
   na prática ela devolvia estados não convergidos para perdas grandes.

4. **A estratégia D ganhou duas regras a mais.** Aplicada ao pé da letra ("só
   coleta se couber"), ela trava: depois que o Hct cai, nenhuma coleta cabe
   mais e o modelo simplesmente para de coletar — o que não é protocolo
   utilizável. Então D (a) protege o Hct com uma folga (`MARGEM_HCT`) acima do
   limiar de transfusão, em vez de coletar o paciente até transfundir, e (b)
   tem uma válvula de escape: pedido parado há mais de `ESPERA_MAX` horas sai
   no volume de micrométodo. Sem isso D é idêntica a A.

5. **Eritropoiese calibrada, não medida.** `FRAC_PROD_BASAL = 0,60` da
   destruição basal. Parece alto para "fração pequena", mas é profundamente
   insuficiente no contexto: **manter** o Hct durante o crescimento exigiria
   ~2,1× a destruição basal, e o teto `PROD_MAX` apenas empata com a
   destruição — nunca faz a massa de hemácias crescer. A anemia é inevitável no
   modelo, como é na clínica; o que as estratégias mudam é a velocidade.

6. **Hct mínimo não discrimina estratégias** quando há transfusão: ele fica
   colado no limiar, por construção. Quem discrimina é o **dia da 1ª
   transfusão**, **quantas** foram necessárias e o **Hct no fim**.

---

## Limitações (a dizer em voz alta na apresentação)

- Windkessel de 2 elementos com sístole instantânea: **superestima a PAS e a
  pressão de pulso**. A PAM, essa sim, é exata no modelo linear.
- Poiseuille aplicado à resistência periférica *total* é uma aproximação
  concentrada: não existe "um" vaso com "um" raio.
- Frank-Starling, barorreflexo e eritropoiese estão em forma linearizada e
  ilustrativa. O barorreflexo é proporcional e puramente estático — sem
  dinâmica, sem offset nulo.
- A relação viscosidade × hematócrito é exponencial no modelo; na realidade é
  não linear de outra forma. R é linear em μ, mas não em Hct.
- A hemodinâmica **não realimenta** o balanço de volume e hemácias (abordagem
  quase estática). Por isso o Hct é idêntico em qualquer reserva cardiovascular.
- Parâmetros ilustrativos, marcados com `TODO` em `parametros.py`, a conferir
  na literatura: Pennati 1997, Sá Couto 2006, Versmold 1981 (neonato);
  Westerhof 2009 (Windkessel); Counsilman 2019 (coletas).
- **Ferramenta didática de comparação de cenários, não de decisão clínica.**

---

## Notas

- `.venv/` e `__pycache__/` não devem ir para o Git; `figuras/` é versionada.
- Se a Área de Trabalho estiver sincronizada com o iCloud, ele pode tentar
  subir os milhares de arquivos do `.venv/`. Se incomodar, mantenha o venv
  fora da pasta (ex.: `~/.venvs/pbl2026`).
