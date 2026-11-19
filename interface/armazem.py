"""armazem.py -- onde os dados ficam guardados.

Duas implementacoes com a mesma interface:

    ArmazemJSON      arquivo local (dados_clinicos.json) -- padrao, offline
    ArmazemSupabase  Postgres do Supabase via PostgREST  -- quando ha chave

`escolher()` decide sozinho: se SUPABASE_URL e SUPABASE_SERVICE_KEY estiverem
no ambiente, usa o Supabase; senao, o arquivo. Isso mantem o projeto rodando
sem internet (sala de aula, apresentacao) e hospedado (Render) sem trocar uma
linha de clinico.py.

Por que o Supabase e' necessario no Render: o disco de la e' descartavel --
cada deploy ou reinicio zera o arquivo. O Postgres nao.
"""

import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
_SIM = RAIZ / "simuladores"
if str(_SIM) not in sys.path:
    sys.path.insert(0, str(_SIM))

import parametros as P
import supabase_db


class JaExiste(Exception):
    """Login duplicado."""


def _agora_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ------------------------------------------------------------- arquivo local

class ArmazemJSON:
    """Documento unico em disco. Simples e sem rede; nao sobrevive ao Render."""

    nome = "arquivo local"

    def __init__(self, caminho=None):
        self.caminho = Path(caminho or RAIZ / P.ARQUIVO_DADOS)
        self._trava = threading.Lock()

    # -- baixo nivel
    def _ler(self):
        if not self.caminho.exists():
            return dict(usuarios={}, pacientes=[], proximo_id=1)
        with self.caminho.open(encoding="utf-8") as f:
            return json.load(f)

    def _gravar(self, dados):
        """Grava num temporario e troca: nunca deixa o arquivo pela metade."""
        tmp = self.caminho.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.caminho)

    # -- interface
    def buscar_usuario(self, login):
        return self._ler()["usuarios"].get(login)

    def criar_usuario(self, login, salt, hash_, nome):
        with self._trava:
            d = self._ler()
            if login in d["usuarios"]:
                raise JaExiste(login)
            d["usuarios"][login] = dict(salt=salt, hash=hash_, nome=nome,
                                        criado_em=_agora_iso())
            self._gravar(d)
        return d["usuarios"][login]

    @staticmethod
    def _completar(pac):
        """Pacientes gravados antes das transfusoes nao tem a chave."""
        pac.setdefault("coletas", [])
        pac.setdefault("transfusoes", [])
        pac.setdefault("dias_extra", 0.0)
        pac.setdefault("suporte_respiratorio", False)
        return pac

    def listar_pacientes(self):
        return [self._completar(p) for p in self._ler()["pacientes"]]

    def buscar_paciente(self, pid):
        for pac in self._ler()["pacientes"]:
            if pac["id"] == pid:
                return self._completar(pac)
        return None

    def criar_paciente(self, nome, peso, semana_vida, cadastrado_por,
                       suporte=False):
        with self._trava:
            d = self._ler()
            pid = d["proximo_id"]
            d["proximo_id"] = pid + 1
            pac = dict(id=pid, nome=nome, peso=peso, semana_vida=semana_vida,
                       cadastrado_por=cadastrado_por,
                       cadastrado_em=_agora_iso(), coletas=[],
                       transfusoes=[], dias_extra=0.0,
                       suporte_respiratorio=suporte)
            d["pacientes"].append(pac)
            self._gravar(d)
        return pac

    def avancar_dias(self, pid, dias):
        with self._trava:
            d = self._ler()
            for pac in d["pacientes"]:
                if pac["id"] == pid:
                    pac["dias_extra"] = pac.get("dias_extra", 0.0) + dias
                    self._gravar(d)
                    return
            raise KeyError(pid)

    def definir_suporte(self, pid, suporte):
        with self._trava:
            d = self._ler()
            for pac in d["pacientes"]:
                if pac["id"] == pid:
                    pac["suporte_respiratorio"] = bool(suporte)
                    self._gravar(d)
                    return
            raise KeyError(pid)

    def apagar_paciente(self, pid):
        with self._trava:
            d = self._ler()
            antes = len(d["pacientes"])
            d["pacientes"] = [p for p in d["pacientes"] if p["id"] != pid]
            if len(d["pacientes"]) == antes:
                raise KeyError(pid)
            self._gravar(d)

    def criar_coleta(self, pid, exame, volume, hora_vida, forcada=False):
        self._anexar(pid, "coletas", dict(exame=exame, volume=volume,
                                          hora_vida=hora_vida,
                                          forcada=forcada, em=_agora_iso()))

    def criar_transfusao(self, pid, volume, hct_antes, hora_vida, decidida_por):
        self._anexar(pid, "transfusoes", dict(
            volume=volume, hct_antes=hct_antes, hora_vida=hora_vida,
            decidida_por=decidida_por, em=_agora_iso()))

    def _anexar(self, pid, lista, item):
        with self._trava:
            d = self._ler()
            for pac in d["pacientes"]:
                if pac["id"] == pid:
                    pac.setdefault(lista, []).append(item)
                    self._gravar(d)
                    return
            raise KeyError(pid)


# ------------------------------------------------------------- Supabase

class ArmazemSupabase:
    """Tabelas usuarios / pacientes / coletas (ver esquema.sql).

    As coletas vem junto do paciente numa so chamada, pelo recurso embutido
    do PostgREST (`select=*,coletas(*)`), que usa a chave estrangeira.
    """

    nome = "Supabase"
    EMBUTIDO = "*,coletas(*),transfusoes(*)"

    @staticmethod
    def _arrumar(pac):
        """Normaliza a linha do Postgres para o formato que clinico.py espera."""
        pac = dict(pac)
        for lista in ("coletas", "transfusoes"):
            pac[lista] = sorted(pac.get(lista) or [],
                                key=lambda c: c["hora_vida"])
        pac["dias_extra"] = pac.get("dias_extra") or 0.0
        pac["suporte_respiratorio"] = bool(pac.get("suporte_respiratorio"))
        return pac

    def buscar_usuario(self, login):
        r = supabase_db.selecionar("usuarios",
                                   {"login": f"eq.{login}", "limit": "1"})
        return r[0] if r else None

    def criar_usuario(self, login, salt, hash_, nome):
        try:
            return supabase_db.inserir("usuarios", dict(
                login=login, salt=salt, hash=hash_, nome=nome))
        except supabase_db.ErroSupabase as e:
            if "duplicate key" in str(e).lower() or "23505" in str(e):
                raise JaExiste(login) from None
            raise

    def listar_pacientes(self):
        return [self._arrumar(p) for p in supabase_db.selecionar(
            "pacientes", {"select": self.EMBUTIDO, "order": "id.asc"})]

    def buscar_paciente(self, pid):
        r = supabase_db.selecionar("pacientes", {
            "id": f"eq.{pid}", "select": self.EMBUTIDO, "limit": "1"})
        return self._arrumar(r[0]) if r else None

    def criar_paciente(self, nome, peso, semana_vida, cadastrado_por,
                       suporte=False):
        pac = supabase_db.inserir("pacientes", dict(
            nome=nome, peso=peso, semana_vida=semana_vida,
            cadastrado_por=cadastrado_por, suporte_respiratorio=suporte))
        pac["coletas"] = []
        pac["transfusoes"] = []
        return pac

    def criar_coleta(self, pid, exame, volume, hora_vida, forcada=False):
        supabase_db.inserir("coletas", dict(
            paciente_id=pid, exame=exame, volume=volume,
            hora_vida=hora_vida, forcada=forcada))

    def criar_transfusao(self, pid, volume, hct_antes, hora_vida, decidida_por):
        supabase_db.inserir("transfusoes", dict(
            paciente_id=pid, volume=volume, hct_antes=hct_antes,
            hora_vida=hora_vida, decidida_por=decidida_por))

    def avancar_dias(self, pid, dias):
        atual = self.buscar_paciente(pid)
        if atual is None:
            raise KeyError(pid)
        supabase_db.atualizar("pacientes", {"id": f"eq.{pid}"},
                              {"dias_extra": (atual.get("dias_extra") or 0.0) + dias})

    def definir_suporte(self, pid, suporte):
        supabase_db.atualizar("pacientes", {"id": f"eq.{pid}"},
                              {"suporte_respiratorio": bool(suporte)})

    def apagar_paciente(self, pid):
        # coletas e transfusoes somem junto: as chaves estrangeiras do
        # esquema.sql tem ON DELETE CASCADE
        supabase_db.apagar("pacientes", {"id": f"eq.{pid}"})


# ------------------------------------------------------------- escolha

def escolher():
    """Supabase se houver chave no ambiente; arquivo local caso contrario."""
    if supabase_db.configurado():
        return ArmazemSupabase()
    return ArmazemJSON()


if __name__ == "__main__":
    a = escolher()
    print(f"armazem em uso: {a.nome}")
    print(f"pacientes: {len(a.listar_pacientes())}")
