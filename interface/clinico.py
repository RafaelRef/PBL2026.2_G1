"""clinico.py -- camada clinica da interface web (PBL 2026.2, Grupo 1).

Traduz "paciente cadastrado + coletas registradas" para os modelos que ja
existem nos arquivos numerados. Nao ha modelo novo aqui, nem constante
numerica solta: tudo vem de parametros.py.

    peso          -> fisiologia.volume_referencia         V_ref = 85 mL/kg
    coletas       -> 02_balanco_volume_hemacias.simular   V, M e Hct no tempo
    estado atual  -> 06_recomendacao.limites              as tres regras

Como a idade entra na conta
---------------------------
O medico informa o peso de HOJE e a semana de vida. O modelo do arquivo 02
integra desde o nascimento, entao estimamos o peso de nascimento invertendo
o ganho de P.GANHO_PESO g/kg/dia e simulamos do dia 0 ate hoje. E' isso que
faz um bebe de 4 semanas chegar ao Hct de hoje ja com a queda fisiologica
acumulada, em vez de comecar sempre em P.HCT0.

A simulacao roda com transfundir=False: a interface mostra o Hct caindo e
sinaliza a indicacao de transfusao, em vez de transfundir sozinha.

O limiar de Hct nao e' o P.HCT_LIMIAR fixo dos arquivos numerados: a
interface usa fisiologia.hct_critico(peso), que cai conforme o bebe cresce.
Passamos a propria funcao (nao um numero) para 06_recomendacao, que a
reavalia a cada passo da projecao.
"""

import hashlib
import math
import secrets
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

# parametros/comum/fisiologia moram em simuladores/
_SIM = Path(__file__).resolve().parent.parent / "simuladores"
if str(_SIM) not in sys.path:
    sys.path.insert(0, str(_SIM))

import parametros as P
import comum
import fisiologia as fis
import armazem

bal = comum.importar("02_balanco_volume_hemacias")
rec = comum.importar("06_recomendacao")

# Supabase quando ha chave no ambiente, arquivo local caso contrario.
# Quem decide e' armazem.escolher(); clinico.py nao sabe a diferenca.
DADOS = armazem.escolher()
_TRAVA = threading.Lock()          # protege o "checa e insere" da coleta
_SESSOES = {}                      # token -> dict(usuario, expira)


class ErroClinico(Exception):
    """Erro previsto, devolvido ao navegador como mensagem legivel."""

    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


# ------------------------------------------------------------- persistencia

def _agora():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.replace(microsecond=0).isoformat()


# ------------------------------------------------------------- login

def _hash(senha, salt):
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"),
                               bytes.fromhex(salt), P.PBKDF2_ITER).hex()


def registrar_usuario(usuario, senha, nome=""):
    """Cadastra o medico. A senha e' guardada so como hash PBKDF2 + salt."""
    usuario = (usuario or "").strip().lower()
    if len(usuario) < 3:
        raise ErroClinico("O login precisa de ao menos 3 caracteres.")
    if len(senha or "") < 4:
        raise ErroClinico("A senha precisa de ao menos 4 caracteres.")
    salt = secrets.token_hex(16)
    try:
        DADOS.criar_usuario(usuario, salt, _hash(senha, salt),
                            (nome or "").strip() or usuario)
    except armazem.JaExiste:
        raise ErroClinico("Esse login já existe.", 409) from None
    return autenticar(usuario, senha)


def autenticar(usuario, senha):
    """Confere a senha e devolve um token de sessao."""
    usuario = (usuario or "").strip().lower()
    u = DADOS.buscar_usuario(usuario)
    # compare_digest mesmo quando o usuario nao existe: o tempo de resposta
    # nao denuncia quais logins estao cadastrados.
    alvo = u["hash"] if u else _hash("", "00" * 16)
    conferiu = secrets.compare_digest(
        _hash(senha or "", u["salt"] if u else "00" * 16), alvo)
    if not u or not conferiu:
        raise ErroClinico("Login ou senha incorretos.", 401)
    token = secrets.token_urlsafe(24)
    _SESSOES[token] = dict(usuario=usuario,
                           expira=_agora() + timedelta(hours=P.SESSAO_HORAS))
    return dict(token=token, usuario=usuario, nome=u["nome"])


def sessao(token):
    s = _SESSOES.get(token or "")
    if not s:
        raise ErroClinico("Sessão não encontrada. Faça login de novo.", 401)
    if s["expira"] < _agora():
        _SESSOES.pop(token, None)
        raise ErroClinico("Sessão expirada. Faça login de novo.", 401)
    return s["usuario"]


def encerrar_sessao(token):
    _SESSOES.pop(token or "", None)


# ------------------------------------------------------------- pacientes

def _num(valor, campo, minimo, maximo):
    try:
        x = float(valor)
    except (TypeError, ValueError):
        raise ErroClinico(f"{campo}: informe um número.")
    if not math.isfinite(x) or not (minimo <= x <= maximo):
        raise ErroClinico(f"{campo}: use um valor entre {minimo:g} e {maximo:g}.")
    return x


def criar_paciente(usuario, nome, peso, semana_vida):
    """Cadastra o bebe. O volume sanguineo sai de V_ref = 85 mL/kg."""
    nome = (nome or "").strip()
    if not nome:
        raise ErroClinico("Informe o nome do paciente.")
    peso = _num(peso, "Peso (kg)", 0.3, 6.0)
    semana = _num(semana_vida, "Semana de vida", 0, 52)
    return DADOS.criar_paciente(nome, peso, semana, usuario)


def _buscar(pid):
    pac = DADOS.buscar_paciente(pid)
    if pac is None:
        raise ErroClinico("Paciente não encontrado.", 404)
    return pac


def listar_pacientes():
    saida = []
    for pac in DADOS.listar_pacientes():
        a = avaliar(pac)
        saida.append(dict(
            id=pac["id"], nome=pac["nome"], peso_cadastro=pac["peso"],
            semana_vida=a["semana_vida"], peso=a["peso"], Hct=a["Hct"],
            V_ref=a["V_ref"], hct_limiar=a["hct_limiar"],
            coletas=len(pac["coletas"]),
            disponivel=a["disponivel"],
            transfusao_indicada=a["transfusao_indicada"]))
    return saida


def registrar_coleta(pid, exame):
    """Registra a puncao. Recusa o que fura qualquer uma das tres regras."""
    if exame not in P.EXAMES:
        raise ErroClinico("Tipo de exame desconhecido.")
    volume = P.EXAMES[exame]["volume"]
    # a trava fecha a janela entre "verificar se cabe" e "gravar": sem ela,
    # dois pedidos simultaneos poderiam furar a regra juntos
    with _TRAVA:
        pac = _buscar(pid)
        a = avaliar(pac)
        if volume > a["disponivel"] + 1e-9:
            raise ErroClinico(
                f"{P.EXAMES[exame]['nome']} pede {volume:.2f} mL, mas só "
                f"cabem {a['disponivel']:.2f} mL agora "
                f"(regra que limita: {a['regra_limitante']}). "
                f"{a['exames'][exame]['texto_espera']}", 409)
        DADOS.criar_coleta(pid, exame, volume, a["hora_vida"])
    return detalhar(pid)


def detalhar(pid):
    pac = _buscar(pid)
    return dict(paciente=dict(id=pac["id"], nome=pac["nome"],
                              peso_cadastro=pac["peso"],
                              semana_vida_cadastro=pac["semana_vida"],
                              cadastrado_por=pac["cadastrado_por"],
                              cadastrado_em=pac["cadastrado_em"],
                              coletas=list(reversed(pac["coletas"]))),
                avaliacao=avaliar(pac))


# ------------------------------------------------------------- avaliacao

def _idade(pac):
    """(hora de vida agora, peso estimado ao nascer)."""
    nasceu_ha = pac["semana_vida"] * 7.0                      # dias no cadastro
    desde = (_agora() - datetime.fromisoformat(pac["cadastrado_em"]))
    hora_vida = round((nasceu_ha + desde.total_seconds() / 86400.0) * 24.0)
    # inverte peso_no_dia: peso(d) = peso0 . exp(GANHO_PESO/1000 . d)
    peso0 = pac["peso"] / math.exp(P.GANHO_PESO / 1000.0 * nasceu_ha)
    return max(0, int(hora_vida)), peso0


def avaliar(pac):
    """Estado de hoje + as tres regras + quantas coletas ainda cabem."""
    hora_vida, peso0 = _idade(pac)
    agenda = [(c["hora_vida"], c["volume"]) for c in pac["coletas"]]
    r = bal.simular(agenda, dias=hora_vida / 24.0, peso0=peso0,
                    transfundir=False)
    e = rec.estado_de(r, -1)
    hct_crit = fis.hct_critico(e["peso"])          # varia com o peso do dia
    L = rec.limites(e, fis.hct_critico)
    disponivel = rec.volume_disponivel(e, fis.hct_critico)

    nomes = dict(janela_24h=f"janela de 24 h (máx. "
                            f"{100 * P.FRAC_MAX_24H:.0f}% de V_ref)",
                 hct=f"hematócrito crítico ({hct_crit:.3f})",
                 volume=f"volume circulante (mín. "
                        f"{100 * (1 - P.MARGEM_VOLUME):.0f}% de V_ref)")
    limitante = min(L, key=L.get)

    exames = {}
    for chave, ex in P.EXAMES.items():
        v = ex["volume"]
        cabe = int(max(0.0, disponivel) // v)
        if cabe:
            espera, texto = 0.0, "Pode coletar agora."
        else:
            espera = rec.tempo_ate_proxima_coleta(
                e, v, peso0=peso0, limite_Hct=fis.hct_critico)
            texto = (f"Próxima janela em ~{espera:.0f} h."
                     if math.isfinite(espera) else
                     f"Não cabe nas próximas {P.HORIZONTE_ESPERA:.0f} h "
                     f"sem transfusão.")
        exames[chave] = dict(
            chave=chave, nome=ex["nome"], volume=v,
            cabe_agora=cabe,
            restante_24h=int(max(0.0, L["janela_24h"]) // v),
            teto_diario=int((P.FRAC_MAX_24H * e["V_ref"]) // v),
            ate_hct_critico=int(max(0.0, L["hct"]) // v),
            espera_h=(None if not math.isfinite(espera) else round(espera)),
            texto_espera=texto)

    return dict(
        hora_vida=hora_vida,
        dia_vida=hora_vida / 24.0,
        semana_vida=hora_vida / 168.0,
        peso=e["peso"], peso_nascimento=peso0,
        V=e["V"], V_ref=e["V_ref"], M=e["M"], Hct=e["Hct"],
        hct_limiar=hct_crit,
        hct_limiar_fixo=P.HCT_LIMIAR,
        transfusao_indicada=e["Hct"] < hct_crit,
        coletado_24h=rec.coletado_em_24h(e),
        coletado_total=float(r["coletado"]),
        frac_coletado=(float(r["coletado"]) / float(r["V0"])
                       if r["V0"] else 0.0),
        limites={k: float(v) for k, v in L.items()},
        nomes_regras=nomes,
        regra_limitante=nomes[limitante],
        disponivel=disponivel,
        exames=exames,
        serie=_serie(r))


def _serie(r, pontos=400):
    """Hct e volume por dia, reduzidos para o grafico da interface."""
    n = len(r["dia"])
    passo = max(1, n // pontos)
    idx = list(range(0, n, passo))
    if idx[-1] != n - 1:
        idx.append(n - 1)
    return dict(dia=[round(float(r["dia"][i]), 4) for i in idx],
                Hct=[round(float(r["Hct"][i]), 5) for i in idx],
                V=[round(float(r["V"][i]), 3) for i in idx],
                V_ref=[round(float(r["V_ref"][i]), 3) for i in idx],
                hct_crit=[round(fis.hct_critico(float(r["peso"][i])), 5)
                          for i in idx])


def onde_estao_os_dados():
    """Texto curto para o servidor imprimir ao subir."""
    return DADOS.nome


def crescimento():
    """Taxa de ganho de peso usada na projecao, para a interface exibir."""
    return dict(ganho_g_kg_dia=P.GANHO_PESO, vol_por_kg=P.VOL_POR_KG,
                tau_v_h=P.TAU_V, vida_hemacia_dias=P.VIDA_HEMACIA)


def catalogo_exames():
    return [dict(chave=k, nome=v["nome"], volume=v["volume"])
            for k, v in P.EXAMES.items()]
