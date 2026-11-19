"""app.py -- servidor da interface clinica (PBL 2026.2, Grupo 1).

Uso:
    python app.py              # abre em http://127.0.0.1:8000
    python app.py --porta 8080

Em servico hospedado (Render e afins), HOST e PORT vem do ambiente:
    HOST=0.0.0.0 PORT=10000 python app.py --sem-navegador

Serve `interface.html` e uma API JSON fina por cima de `clinico.py`. Usa so
a biblioteca padrao -- nenhuma dependencia alem do numpy/matplotlib que o
projeto ja tem.

Escopo: prova de conceito didatica, presa a 127.0.0.1. Nao e' um sistema de
prontuario e nao deve guardar dado de paciente real.
"""

import argparse
import json
import os
import re
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

# O repositorio e' organizado em pastas (simuladores/, interface/, figuras/).
# Os modulos nao sao um pacote instalavel, entao apontamos o sys.path para as
# duas pastas que este servidor precisa importar.
for _pasta in (RAIZ / "simuladores", RAIZ / "interface"):
    if str(_pasta) not in sys.path:
        sys.path.insert(0, str(_pasta))

# clinico -> 02_balanco_volume_hemacias -> matplotlib.pyplot. Num servidor sem
# tela (Render, Docker) o backend interativo trava na importacao. Precisa vir
# ANTES do import de clinico.
os.environ.setdefault("MPLBACKEND", "Agg")

import parametros as P
import clinico

PAGINA = RAIZ / "interface" / "interface.html"
MAX_CORPO = 64 * 1024          # nenhum pedido legitimo chega perto disso
ROTA_PACIENTE = re.compile(r"^/api/pacientes/(\d+)$")
ROTA_COLETAS = re.compile(r"^/api/pacientes/(\d+)/coletas$")


class Handler(BaseHTTPRequestHandler):
    server_version = "SimuladorColetas/1.0"
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------ utilidades

    def _responder(self, status, corpo, tipo="application/json; charset=utf-8"):
        if not isinstance(corpo, (bytes, bytearray)):
            corpo = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _corpo(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        if n > MAX_CORPO:
            raise clinico.ErroClinico("Pedido grande demais.", 413)
        try:
            dados = json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise clinico.ErroClinico("Corpo do pedido não é JSON válido.")
        if not isinstance(dados, dict):
            raise clinico.ErroClinico("Corpo do pedido não é JSON válido.")
        return dados

    def _usuario(self):
        cab = self.headers.get("Authorization") or ""
        token = cab[7:].strip() if cab.lower().startswith("bearer ") else ""
        return clinico.sessao(token)

    def log_message(self, formato, *args):
        print(f"  {self.command} {self.path} -> {args[1]}")

    # ------------------------------------------------------ rotas

    def do_GET(self):
        try:
            if self.path in ("/", "/index.html", "/interface.html"):
                return self._responder(200, PAGINA.read_bytes(),
                                       "text/html; charset=utf-8")
            if self.path == "/api/config":
                return self._responder(200, dict(
                    exames=clinico.catalogo_exames(),
                    hct_limiar_fixo=P.HCT_LIMIAR,
                    vol_por_kg=P.VOL_POR_KG,
                    frac_max_24h=P.FRAC_MAX_24H,
                    margem_volume=P.MARGEM_VOLUME,
                    horizonte=P.HORIZONTE_ESPERA,
                    crescimento=clinico.crescimento(),
                    marca=dict(nome1=P.APP_NOME_1, nome2=P.APP_NOME_2,
                               subtitulo=P.APP_SUBTITULO,
                               rodape=P.APP_RODAPE)))
            if self.path == "/api/pacientes":
                self._usuario()
                return self._responder(200, dict(
                    pacientes=clinico.listar_pacientes()))
            m = ROTA_PACIENTE.match(self.path)
            if m:
                self._usuario()
                return self._responder(200, clinico.detalhar(int(m.group(1))))
            self._responder(404, dict(erro="Rota não encontrada."))
        except clinico.ErroClinico as e:
            self._responder(e.status, dict(erro=e.mensagem))
        except FileNotFoundError:
            self._responder(500, dict(erro="interface.html não encontrado."))
        except Exception as e:                       # nao derruba o servidor
            self._responder(500, dict(erro=f"Erro interno: {e}"))

    def do_POST(self):
        try:
            corpo = self._corpo()

            if self.path == "/api/registrar":
                return self._responder(201, clinico.registrar_usuario(
                    corpo.get("usuario"), corpo.get("senha"),
                    corpo.get("nome")))

            if self.path == "/api/login":
                return self._responder(200, clinico.autenticar(
                    corpo.get("usuario"), corpo.get("senha")))

            if self.path == "/api/logout":
                cab = self.headers.get("Authorization") or ""
                clinico.encerrar_sessao(cab[7:].strip())
                return self._responder(200, dict(ok=True))

            if self.path == "/api/pacientes":
                usuario = self._usuario()
                pac = clinico.criar_paciente(
                    usuario, corpo.get("nome"), corpo.get("peso"),
                    corpo.get("semana_vida"))
                return self._responder(201, clinico.detalhar(pac["id"]))

            m = ROTA_COLETAS.match(self.path)
            if m:
                self._usuario()
                return self._responder(201, clinico.registrar_coleta(
                    int(m.group(1)), corpo.get("exame")))

            self._responder(404, dict(erro="Rota não encontrada."))
        except clinico.ErroClinico as e:
            self._responder(e.status, dict(erro=e.mensagem))
        except Exception as e:
            self._responder(500, dict(erro=f"Erro interno: {e}"))


def main():
    # O Render injeta PORT mas NAO injeta HOST, e exige que o processo escute
    # em 0.0.0.0 -- preso em 127.0.0.1 o proxy dele nunca alcanca o app e a
    # requisicao fica pendurada. Entao PORT no ambiente significa "estou
    # hospedado": o host padrao vira 0.0.0.0. Rodando na maquina do aluno,
    # sem PORT, continua preso em 127.0.0.1 de proposito.
    hospedado = bool(os.environ.get("PORT"))
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--porta", type=int,
                    default=int(os.environ.get("PORT") or P.PORTA))
    ap.add_argument("--host", default=os.environ.get("HOST")
                    or ("0.0.0.0" if hospedado else P.HOST))
    ap.add_argument("--sem-navegador", action="store_true",
                    default=hospedado)
    args = ap.parse_args()

    # Sem isto o Python segura o stdout num buffer quando a saida nao e' um
    # terminal, e as mensagens abaixo nunca aparecem nos logs do Render.
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except AttributeError:                    # Python < 3.7
        pass

    endereco = f"http://{args.host}:{args.porta}"
    servidor = ThreadingHTTPServer((args.host, args.porta), Handler)
    print(f"{P.APP_NOME_1} {P.APP_NOME_2} -- {P.APP_SUBTITULO}")
    print(f"  interface:  {endereco}")
    print(f"  dados em:   {clinico.onde_estao_os_dados()}")
    if hospedado and clinico.onde_estao_os_dados() != "Supabase":
        print("  AVISO: sem SUPABASE_URL/SUPABASE_SERVICE_KEY no ambiente. "
              "O disco deste servico e' descartavel: os dados somem no "
              "proximo deploy.")
    print(f"  Ctrl+C para parar.\n")
    if not args.sem_navegador:
        webbrowser.open(endereco)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nservidor encerrado.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
