"""04 -- Figuras do relatorio parcial (Figuras 1, 2 e 3) e numeros da Tabela 2.

Usa as funcoes dos arquivos 02 e 03, SEM compensacao cardiovascular
(P.SEM_COMPENSACAO). Salva em figuras/relatorio_parcial/:
  fig1_estrutura_simulador.png
  fig2_efeito_coletas_3_dias.png
  fig3_comparacao_estrategias.png
"""
import numpy as np, parametros as P, comum, fisiologia as fis
import matplotlib.pyplot as plt
bal=comum.importar("02_balanco_volume_hemacias"); est=comum.importar("03_estrategias_coleta")
SC=P.SEM_COMPENSACAO
plt.rcParams.update({"font.family":"DejaVu Serif","font.size":9,"axes.spines.top":False,"axes.spines.right":False})
comum.FIGURAS_RELATORIO.mkdir(parents=True, exist_ok=True)
# ---------- Figura 1: diagrama dos modulos
from matplotlib.patches import FancyBboxPatch
fig,ax=plt.subplots(figsize=(8.6,2.1)); ax.set_xlim(0,100); ax.set_ylim(0,30); ax.axis("off")
B=[(0.5,"Entradas","peso $W(t)$, $H_0$\ncoletas e\ntransfusões","#EDEDED"),
   (21,"Módulo 1","balanço\nde volume\n$V(t)$","#F6E1DD"),
   (41,"Módulo 2","massa de\nhemácias\n$H=V_{HB}/V$","#F6E1DD"),
   (61,"Módulo 3","Windkessel RC\n+ barorreflexo","#E9C3BB"),
   (81,"Saídas","PAM, PP,\nDC, DO$_2$","#EDEDED")]
for x,t,s,c in B:
    ax.add_patch(FancyBboxPatch((x,9),17,15,boxstyle="round,pad=0.4",fc=c,ec="#7A1F12",lw=1))
    ax.text(x+8.5,20.5,t,ha="center",va="center",fontsize=9,weight="bold")
    ax.text(x+8.5,14,s,ha="center",va="center",fontsize=7.2)
for x in (18.6,38.6,58.6,78.6):
    ax.annotate("",xy=(x+2.2,16.5),xytext=(x,16.5),arrowprops=dict(arrowstyle="-|>",color="#7A1F12",lw=1.2))
ax.text(60,4.2,r"acoplamento:  $V\rightarrow$ pré-carga $\rightarrow SV$     |     $H\rightarrow\mu(H)\rightarrow R$     |     $H\rightarrow$ Hb $\rightarrow$ CaO$_2$",ha="center",fontsize=7.5,color="#7A1F12")
fig.savefig(comum.FIGURAS_RELATORIO / 'fig1_estrutura_simulador.png',dpi=250,bbox_inches='tight')

# ---------- Figura 2: uma rotina, dias 0-3
rA=bal.simular(bal.agenda_rotina()); sA=fis.serie_hemodinamica(rA,SC)
m=rA['dia']<=3
fig,ax=plt.subplots(3,1,figsize=(6.6,5.2),sharex=True)
ax[0].plot(rA['dia'][m],rA['V_ref'][m],'--',color='0.55',lw=1,label='volume normal para o peso')
ax[0].plot(rA['dia'][m],rA['V'][m],color='#2a78d6',lw=1.5,label='volume do bebê')
ax[0].set_ylabel('Volume (mL)'); ax[0].set_title('(a) Módulo 1: o volume cai a cada coleta e se recupera em horas',fontsize=9,loc='left')
ax[0].legend(fontsize=7,loc='lower right',frameon=False)
ax[1].plot(rA['dia'][m],100*rA['Hct'][m],color='#8e44ad',lw=1.5)
ax[1].set_ylabel('Hematócrito (%)'); ax[1].set_title('(b) Módulo 2: o hematócrito cai continuamente',fontsize=9,loc='left')
ax[2].plot(rA['dia'][m],sA['PAM'][m],color='#c0392b',lw=1.5)
ax[2].set_ylabel('PAM (mmHg)'); ax[2].set_xlabel('Tempo (dias)')
ax[2].set_title('(c) Módulo 3: a PAM cai em degraus a cada coleta e tende a cair com o hematócrito',fontsize=9,loc='left')
for t,_ in rA['coletas']:
    if t/24<=3:
        for a in ax: a.axvline(t/24,color='0.85',lw=0.8,zorder=0)
for a in ax: a.grid(axis='y',alpha=.3)
fig.tight_layout(); fig.savefig(comum.FIGURAS_RELATORIO / 'fig2_efeito_coletas_3_dias.png',dpi=220)
# ---------- Figura 3: estratégias
res=est.rodar(SC); r0=bal.simular([])
nomes={'Rotina':'Rotina','Agrupada':'Agrupada','Micrometodo':'Micrométodo','Guiada':'Guiada'}
cores={'0':'0.35','A':'#c0392b','B':'#e67e22','C':'#2a78d6','D':'#16a085'}
cen=[('0','Sem coleta',r0)]+[(e['id'],f"{e['id']}. {nomes[e['nome']]}",e['r']) for e in res]
fig,ax=plt.subplots(1,2,figsize=(7.4,3.2),gridspec_kw=dict(width_ratios=[1.35,1]))
a=ax[0]
for k,l,r in cen:
    a.plot(r['dia'],100*r['Hct'],color=cores[k],lw=1.3 if k!='0' else 1.4,ls='--' if k=='0' else '-',label=l)
    for t,_ in r['transfusoes']: a.plot(t/24,30,marker='v',color=cores[k],ms=6,zorder=5)
a.axhline(30,ls=':',color='k',lw=0.8); a.text(0.3,29.3,'limite de transfusão (30%)',fontsize=6.8)
a.set(xlabel='Tempo (dias)',ylabel='Hematócrito (%)',ylim=(28.8,46)); a.set_title('(a) Hematócrito (▼ = transfusão)',fontsize=9,loc='left')
a.legend(fontsize=6.6,ncol=2,frameon=False,loc='upper right'); a.grid(alpha=.3)
a=ax[1]
lab=[l for _,l,_ in cen][::-1]; vol=[r['coletado'] for _,_,r in cen][::-1]; cs=[cores[k] for k,_,_ in cen][::-1]
tr=[r['transfusoes'] for _,_,r in cen][::-1]
y=np.arange(len(lab)); a.barh(y,vol,color=cs,height=0.6)
for yi,v,t in zip(y,vol,tr):
    a.text(v+0.4,yi,f"{len(t)} transf. (1ª: dia " + f"{t[0][0]/24:.1f}".replace(".",",") + ")",va='center',fontsize=6.8)
a.set_yticks(y); a.set_yticklabels(lab,fontsize=7.5); a.set_xlim(0,38)
a.set_xlabel('Sangue coletado em 28 dias (mL)'); a.set_title('(b) Volume coletado e transfusões',fontsize=9,loc='left')
fig.tight_layout(); fig.savefig(comum.FIGURAS_RELATORIO / 'fig3_comparacao_estrategias.png',dpi=220)

# tabela 2 (PAM e DO2 sem compensacao)
for k,l,r in cen:
    s=fis.serie_hemodinamica(r,SC)
    print(f"{l:<16s} coletado {r['coletado']:5.1f} mL  transf {len(r['transfusoes'])}  1a dia {r['transfusoes'][0][0]/24:5.1f}  PAM media {s['PAM'].mean():5.1f}  PAM min {s['PAM'].min():5.1f}  DO2 min {s['DO2_kg'].min():5.1f}")
