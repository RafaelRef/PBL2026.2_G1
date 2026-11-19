"""supabase_db.py -- cliente minimo do Supabase (PostgREST), so biblioteca padrao.

O projeto inteiro evita dependencia: o servidor e' http.server, nao Flask. Aqui
seguimos igual -- o Supabase expoe as tabelas por REST, entao urllib resolve.
Unica dependencia extra e' certifi, para o SSL funcionar tanto no macOS quanto
no Linux do Render.

As credenciais vem do ambiente, NUNCA do codigo:

    SUPABASE_URL          https://<id>.supabase.co
    SUPABASE_SERVICE_KEY  chave secreta (service_role / sb_secret_...)

A chave secreta ignora as politicas de Row Level Security. Ela so pode viver
no servidor: nunca no interface.html, nunca num arquivo versionado.
"""

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import certifi
    _CONTEXTO = ssl.create_default_context(cafile=certifi.where())
except ImportError:                       # usa os certificados do sistema
    _CONTEXTO = ssl.create_default_context()

TEMPO_LIMITE = 20.0                       # s


class ErroSupabase(Exception):
    pass


def carregar_env(caminho=".env"):
    """Le o .env para o ambiente, sem sobrescrever o que ja estiver definido.

    No Render nao existe .env: as variaveis vem do painel, e por isso o
    `setdefault` -- o ambiente real sempre ganha do arquivo.
    """
    p = Path(__file__).resolve().parent.parent / caminho
    if not p.exists():
        return
    for linha in p.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def configurado():
    carregar_env()
    return bool(os.environ.get("SUPABASE_URL")
                and os.environ.get("SUPABASE_SERVICE_KEY"))


def _credenciais():
    carregar_env()
    url = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    chave = os.environ.get("SUPABASE_SERVICE_KEY") or ""
    if not url or not chave:
        raise ErroSupabase("SUPABASE_URL ou SUPABASE_SERVICE_KEY nao definidos.")
    if "/dashboard/" in url or not url.endswith(".supabase.co"):
        raise ErroSupabase(
            "SUPABASE_URL parece ser a URL do painel. Use a de "
            "Project Settings > API > Project URL (https://<id>.supabase.co).")
    return url, chave


def pedir(metodo, caminho, corpo=None, params=None, prefer=None):
    """Chamada crua ao PostgREST. Devolve a lista/dict decodificado, ou [].

    `params` vira a query string no formato do PostgREST, por exemplo
    {"login": "eq.dra.ana"} -> ?login=eq.dra.ana
    """
    url, chave = _credenciais()
    destino = f"{url}/rest/v1/{caminho}"
    if params:
        destino += "?" + urllib.parse.urlencode(params)
    dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    cabecalhos = {
        "apikey": chave,
        "Authorization": f"Bearer {chave}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if prefer:
        cabecalhos["Prefer"] = prefer
    req = urllib.request.Request(destino, data=dados, headers=cabecalhos,
                                 method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=TEMPO_LIMITE,
                                    context=_CONTEXTO) as r:
            bruto = r.read()
            return json.loads(bruto) if bruto else []
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode("utf-8", "replace")[:400]
        try:
            msg = json.loads(detalhe).get("message", detalhe)
        except ValueError:
            msg = detalhe
        raise ErroSupabase(f"Supabase respondeu {e.code}: {msg}") from None
    except urllib.error.URLError as e:
        raise ErroSupabase(f"Nao consegui falar com o Supabase: {e.reason}") from None


def selecionar(tabela, params=None):
    return pedir("GET", tabela, params=params)


def inserir(tabela, linha):
    """Insere e devolve a linha gravada (com o id gerado pelo banco)."""
    r = pedir("POST", tabela, corpo=[linha], prefer="return=representation")
    return r[0] if r else {}


def testar():
    """Checagem de fumaca: as tabelas existem e respondem?"""
    faltando = []
    for tabela in ("usuarios", "pacientes", "coletas"):
        try:
            selecionar(tabela, {"select": "count", "limit": "1"})
        except ErroSupabase as e:
            faltando.append(f"{tabela}: {e}")
    return faltando


if __name__ == "__main__":
    print("configurado:", configurado())
    problemas = testar()
    if problemas:
        print("\ntabelas com problema:")
        for p in problemas:
            print("  -", p)
        print("\nRode o conteudo de esquema.sql no SQL Editor do Supabase.")
    else:
        print("as tres tabelas responderam: usuarios, pacientes, coletas")
