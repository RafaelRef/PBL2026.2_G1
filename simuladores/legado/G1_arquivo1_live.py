import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button, RadioButtons
from collections import deque


# ---------------------------------------------------------------- parametros

ADULTO = dict(nome="Adulto", HR=70.0, SV=70.0, C=1.20, R=1.0, Pv=5.0,
              cor="#2a78d6")
NEONATO = dict(nome="Neonato", HR=140.0, SV=5.0, C=0.13, R=3.6, Pv=3.0,
               cor="#eb6834")

PACIENTES = [ADULTO, NEONATO]

DT = 0.004                    # passo de desenho [s] (nao e erro numerico)
INTERVALO_MS = 20             # periodo de atualizacao da tela [ms]
VELOCIDADE = 1.0              # 1.0 = tempo real; 0.25 = camera lenta
JANELA = 6.0                  # segundos visiveis na tela

N_BUFFER = int(JANELA / DT)
PASSOS_POR_QUADRO = max(1, int(round(INTERVALO_MS / 1000 * VELOCIDADE / DT)))


# ---------------------------------------------------------------- modelo

def regime_estavel(e):
    """PAS, PAD e PAM que os parametros atuais dariam depois de estabilizar."""
    T = 60.0 / e["HR"]
    tau = e["R"] * e["C"]
    PAS = e["Pv"] + (e["SV"] / e["C"]) / (1 - np.exp(-T / tau))
    PAD = e["Pv"] + (PAS - e["Pv"]) * np.exp(-T / tau)
    PAM = e["Pv"] + e["R"] * e["SV"] / T
    return PAS, PAD, PAM, tau, T


def novo_estado(p):
    """Parametros correntes + buffers do traçado."""
    e = dict(HR=p["HR"], SV=p["SV"], R=p["R"], C=p["C"], Pv=p["Pv"],
             cor=p["cor"], t=0.0, t_prox=0.0, n_batidas=0, pausado=False,
             buf_t=deque(maxlen=N_BUFFER), buf_P=deque(maxlen=N_BUFFER),
             saltos=deque(maxlen=40))      # (t, P_antes, P_depois)
    e["P"] = regime_estavel(e)[2]          # comeca na PAM teorica
    return e


def bater(e):
    """Um batimento: degrau instantaneo de SV/C."""
    antes = e["P"]
    e["P"] += e["SV"] / e["C"]
    e["saltos"].append((e["t"], antes, e["P"]))
    e["n_batidas"] += 1


def passo(e):
    """Avanca DT segundos: batimento se for a hora, depois descarga do RC."""
    if e["t"] >= e["t_prox"]:
        bater(e)
        e["t_prox"] = e["t"] + 60.0 / e["HR"]

    e["buf_t"].append(e["t"])
    e["buf_P"].append(e["P"])

    tau = e["R"] * e["C"]
    e["P"] = e["Pv"] + (e["P"] - e["Pv"]) * np.exp(-DT / tau)
    e["t"] += DT


# ---------------------------------------------------------------- interface

def monitor():
    e = novo_estado(ADULTO)

    fig = plt.figure(figsize=(11.5, 6.4))
    fig.suptitle("Windkessel RC simples - ao vivo "
                 r"(pulso $SV/C$ + decaimento $e^{-t/\tau}$)")

    ax_p = fig.add_axes([0.07, 0.40, 0.69, 0.48])

    (linha_p,) = ax_p.plot([], [], lw=2, color=e["cor"])
    (hastes,) = ax_p.plot([], [], lw=1.6, color=e["cor"])
    (pontas,) = ax_p.plot([], [], ls="none", marker="^", ms=7,
                          color=e["cor"])

    ax_p.set_ylabel("Pressao (mmHg)")
    ax_p.set_xlabel("Tempo (s)")
    ax_p.set_xlim(0, JANELA)
    ax_p.set_ylim(0, 140)

    texto = fig.text(0.79, 0.88, "", va="top", family="monospace", fontsize=10)

    # --- widgets
    ax_hr = fig.add_axes([0.13, 0.26, 0.55, 0.03])
    ax_sv = fig.add_axes([0.13, 0.19, 0.55, 0.03])
    ax_r = fig.add_axes([0.13, 0.12, 0.55, 0.03])
    ax_c = fig.add_axes([0.13, 0.05, 0.55, 0.03])

    s_hr = Slider(ax_hr, "HR [bpm]", 30, 220, valinit=e["HR"], valstep=1)
    s_sv = Slider(ax_sv, "SV [mL]", 1, 120, valinit=e["SV"])
    s_r = Slider(ax_r, "R [mmHg.s/mL]", 0.2, 6.0, valinit=e["R"])
    s_c = Slider(ax_c, "C [mL/mmHg]", 0.03, 3.0, valinit=e["C"])

    ax_radio = fig.add_axes([0.79, 0.31, 0.17, 0.14])
    ax_radio.set_title("paciente", fontsize=9)
    radio = RadioButtons(ax_radio, [p["nome"] for p in PACIENTES])

    b_extra = Button(fig.add_axes([0.79, 0.19, 0.17, 0.06]), "batimento extra")
    b_pausa = Button(fig.add_axes([0.79, 0.10, 0.17, 0.06]), "pausa")

    def ao_mudar(_):
        e["HR"], e["SV"], e["R"], e["C"] = s_hr.val, s_sv.val, s_r.val, s_c.val

    for s in (s_hr, s_sv, s_r, s_c):
        s.on_changed(ao_mudar)

    def ao_trocar_paciente(nome):
        p = next(x for x in PACIENTES if x["nome"] == nome)
        e["Pv"], e["cor"] = p["Pv"], p["cor"]
        for artista in (linha_p, hastes, pontas):
            artista.set_color(p["cor"])
        for s, chave in ((s_hr, "HR"), (s_sv, "SV"), (s_r, "R"), (s_c, "C")):
            s.set_val(p[chave])          # dispara ao_mudar

    radio.on_clicked(ao_trocar_paciente)

    def extra(_=None):
        """Batimento fora do ritmo, agora."""
        bater(e)
        e["t_prox"] = e["t"] + 60.0 / e["HR"]

    def pausar(_=None):
        e["pausado"] = not e["pausado"]
        b_pausa.label.set_text("continuar" if e["pausado"] else "pausa")

    def limpar(_=None):
        for b in ("buf_t", "buf_P", "saltos"):
            e[b].clear()
        e["P"] = regime_estavel(e)[2]

    b_extra.on_clicked(extra)
    b_pausa.on_clicked(pausar)

    def ao_teclar(evento):
        if evento.key == " ":
            pausar()
        elif evento.key == "e":
            extra()
        elif evento.key == "r":
            limpar()

    fig.canvas.mpl_connect("key_press_event", ao_teclar)

    # --- laco de animacao
    def quadro(_):
        if not e["pausado"]:
            for _ in range(PASSOS_POR_QUADRO):
                passo(e)

        if not e["buf_t"]:
            return ()

        t = np.fromiter(e["buf_t"], float)
        P = np.fromiter(e["buf_P"], float)
        linha_p.set_data(t, P)

        # setas verticais dos batimentos ainda visiveis na janela
        xs, ys, tx, ty = [], [], [], []
        for tb, p0, p1 in e["saltos"]:
            if tb >= t[0]:
                xs += [tb, tb, np.nan]
                ys += [p0, p1, np.nan]
                tx.append(tb)
                ty.append(p1)
        hastes.set_data(xs, ys)
        pontas.set_data(tx, ty)

        # janela rolante
        t_fim = max(t[-1], JANELA)
        ax_p.set_xlim(t_fim - JANELA, t_fim)
        margem = max(5.0, 0.12 * (P.max() - P.min()))
        ax_p.set_ylim(P.min() - margem, P.max() + margem)

        PAS, PAD, PAM, tau, T = regime_estavel(e)
        texto.set_text(
            f"regime estavel dos\n"
            f"parametros atuais:\n\n"
            f"PAS  {PAS:6.1f} mmHg\n"
            f"PAD  {PAD:6.1f} mmHg\n"
            f"PAM  {PAM:6.1f} mmHg\n"
            f"PP   {PAS - PAD:6.1f} mmHg\n\n"
            f"SV/C {e['SV'] / e['C']:6.1f} mmHg\n"
            f"tau  {tau:6.2f} s\n"
            f"T    {T:6.2f} s\n"
            f"DC   {e['HR'] * e['SV'] / 1000:6.2f} L/min\n\n"
            f"t    {e['t']:6.1f} s\n"
            f"bat  {e['n_batidas']:6d}"
        )
        return linha_p, hastes, pontas, texto

    ani = FuncAnimation(fig, quadro, interval=INTERVALO_MS,
                        blit=False, cache_frame_data=False)
    fig._ani = ani          # evita que o garbage collector mate a animacao
    plt.show()


if __name__ == "__main__":
    monitor()