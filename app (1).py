import io
import re
from html import escape

import pandas as pd
import pdfplumber
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="OF Analytics",
    layout="wide",
    page_icon="💎",
    initial_sidebar_state="collapsed",
)

# --- THEME START (bloc autonome : couleurs, CSS, carte) -------------------
SHIFT_COLORS = {
    "matin": "#FFC38A",
    "après-midi": "#8FD3FF",
    "soir": "#FF8FA3",
    "nuit": "#8C7BFF",
}

THEMES = {
    True: dict(  # sombre, ardoise indigo (pas de noir profond)
        ink="#1D2139", text="#F5F7FF", muted="#B2B8D8",
        glassA="rgba(150,160,230,.20)", glassB="rgba(60,68,120,.42)",
        line="rgba(255,255,255,.18)", hi="rgba(255,255,255,.28)", edge="rgba(0,0,0,0)",
        shadow="rgba(10,12,35,.45)", thbg="rgba(48,54,104,.96)",
        b1="rgba(110,122,255,.55)", b2="rgba(255,110,200,.34)", b3="rgba(70,180,255,.38)",
        frost="rgba(32,36,70,.28)", slabA="rgba(255,255,255,.22)", slabB="rgba(255,255,255,.04)",
        sweep="rgba(255,255,255,.16)", glow="rgba(170,182,255,.55)",
        noiseC="1", cardsh="0 40px 70px -20px rgba(124,140,255,.45),0 18px 30px rgba(10,12,35,.4)",
    ),
    False: dict(  # clair
        ink="#EAEDFB", text="#14172B", muted="#5B6283",
        glassA="rgba(255,255,255,.72)", glassB="rgba(255,255,255,.38)",
        line="rgba(255,255,255,.85)", hi="rgba(255,255,255,1)", edge="rgba(80,90,170,.12)",
        shadow="rgba(60,70,160,.35)", thbg="rgba(244,246,255,.96)",
        b1="rgba(140,155,255,.75)", b2="rgba(255,160,220,.60)", b3="rgba(130,210,255,.70)",
        frost="rgba(255,255,255,.35)", slabA="rgba(255,255,255,.75)", slabB="rgba(255,255,255,.12)",
        noiseC=".25", sweep="rgba(124,140,255,.22)", glow="rgba(110,125,255,.45)", cardsh="0 36px 60px -24px rgba(90,70,200,.55),0 14px 24px rgba(40,50,120,.18)",
    ),
}


def noise(alpha, c):
    """Grain fin en SVG : donne l'aspect dense du verre dépoli."""
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='n'>"
        "<feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/>"
        f"<feColorMatrix values='0 0 0 0 {c} 0 0 0 0 {c} 0 0 0 0 {c} 0 0 0 {alpha} 0'/></filter>"
        "<rect width='100%' height='100%' filter='url(%23n)'/></svg>"
    )
    return f'url("data:image/svg+xml;utf8,{svg}")'


CSS_TEMPLATE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&display=swap');
.stApp{
  --ink:__ink__;--text:__text__;--muted:__muted__;--line:__line__;--hi:__hi__;--edge:__edge__;
  --shadow:__shadow__;--thbg:__thbg__;
  --glass:__noiseLo__,linear-gradient(145deg,__glassA__,__glassB__);
  font-family:'Manrope',sans-serif;background:var(--ink);color:var(--text);
  isolation:isolate;min-height:100vh;transition:background .5s ease,color .4s ease;
}
html,body,[class*="css"]{font-family:'Manrope',sans-serif !important;}
#MainMenu,footer,header[data-testid="stHeader"]{visibility:hidden;height:0;}
.block-container{max-width:1080px;padding-top:2rem;padding-bottom:4rem;}
:where(.stApp p,.stApp label,.stApp span,.stApp h1,.stApp h2,.stApp h3){color:var(--text);}

/* Fond : taches de couleur + plaques de glace + givre dense par-dessus */
.ice{position:fixed;inset:0;z-index:-1;overflow:hidden;pointer-events:none;}
.ice::before{content:"";position:absolute;inset:-12%;
  background:
    radial-gradient(520px 420px at 12% 18%,__b1__,transparent 70%),
    radial-gradient(560px 460px at 88% 30%,__b2__,transparent 70%),
    radial-gradient(620px 480px at 55% 95%,__b3__,transparent 70%);
  animation:drift 40s ease-in-out infinite alternate;}
.ice i{position:absolute;border-radius:44px;background:linear-gradient(145deg,__slabA__,__slabB__);
  border:1px solid __slabA__;box-shadow:inset 0 1px 0 __slabA__;}
.ice i:nth-child(1){width:540px;height:340px;top:-90px;right:-130px;transform:rotate(14deg);}
.ice i:nth-child(2){width:440px;height:300px;bottom:-110px;left:-110px;transform:rotate(-18deg);}
.ice i:nth-child(3){width:260px;height:180px;top:46%;right:6%;transform:rotate(-8deg);opacity:.7;}
.ice::after{content:"";position:absolute;inset:0;
  backdrop-filter:blur(34px) saturate(1.25);-webkit-backdrop-filter:blur(34px) saturate(1.25);
  background:__noiseHi__,__frost__;}
@keyframes drift{from{transform:translate(-2%,-1%) scale(1);}to{transform:translate(3%,2%) scale(1.08);}}

/* En-tête */
.top{display:flex;align-items:center;gap:.6rem;color:var(--muted);font-weight:500;padding-top:.5rem;}
.top .dot{width:10px;height:10px;border-radius:50%;background:linear-gradient(135deg,#7C8CFF,#FF8AD8);}
.h1{font-size:clamp(2rem,4.2vw,3.1rem);font-weight:800;letter-spacing:-.03em;line-height:1.05;margin:1.4rem 0 .6rem;color:var(--text);}
.lead{color:var(--muted);font-size:1.05rem;max-width:34rem;margin:0 0 1.5rem;}
.sec{font-size:1.4rem;font-weight:800;letter-spacing:-.02em;margin:2rem 0 .8rem;color:var(--text);}

/* Verre épais : même traitement partout */
.kpi,.shifts,.tw,div[data-testid="stFileUploader"] section{
  background:var(--glass) !important;
  backdrop-filter:blur(26px) saturate(1.4);-webkit-backdrop-filter:blur(26px) saturate(1.4);
  border:1px solid var(--line) !important;
  box-shadow:0 0 0 1px var(--edge),inset 0 1px 0 var(--hi),0 24px 48px -24px var(--shadow);
}
div[data-testid="stFileUploader"] section{border-radius:22px !important;padding:1.3rem !important;border-style:dashed !important;}
div[data-testid="stFileUploader"] section *{color:var(--text) !important;}
div[data-testid="stFileUploader"] small{color:var(--muted) !important;}
div[data-testid="stFileUploader"] button{background:transparent !important;border:1px solid var(--line) !important;border-radius:12px !important;}
[data-testid="stToggle"] p,[data-testid="stWidgetLabel"] p{color:var(--text) !important;font-weight:600;}
[data-testid="stSpinner"] *{color:var(--muted) !important;}

/* Survols : balayage lumineux, relief, lignes de tableau */
.kpi,.shifts,div[data-testid="stFileUploader"] section{position:relative;overflow:hidden;
  transition:transform .4s cubic-bezier(.2,.8,.2,1),box-shadow .4s ease,border-color .3s ease;}
.kpi::before,.shifts::before,div[data-testid="stFileUploader"] section::before{
  content:"";position:absolute;top:0;bottom:0;left:-70%;width:45%;pointer-events:none;
  background:linear-gradient(100deg,transparent,var(--sweep),transparent);transform:skewX(-18deg);
  transition:left .9s cubic-bezier(.2,.8,.2,1);}
.kpi:hover::before,.shifts:hover::before,div[data-testid="stFileUploader"] section:hover::before{left:140%;}
.kpi:hover,.shifts:hover,div[data-testid="stFileUploader"] section:hover{
  transform:translateY(-4px);border-color:var(--glow) !important;
  box-shadow:0 0 0 1px var(--edge),inset 0 1px 0 var(--hi),0 30px 60px -22px var(--glow);}
.bar span{transition:transform .25s ease,filter .25s ease;}
.bar span:hover{transform:scaleY(1.7);filter:brightness(1.15);}
.legend div{transition:transform .2s ease;}.legend div:hover{transform:translateY(-2px);}
.tw td{transition:background .2s ease,box-shadow .2s ease;}
.tw tr:hover td{background:rgba(124,140,255,.14);}
.tw tr:hover td:first-child{box-shadow:inset 3px 0 0 #7C8CFF;}
.stDownloadButton button{position:relative;overflow:hidden;}
.stDownloadButton button::after{content:"";position:absolute;top:0;bottom:0;left:-60%;width:40%;pointer-events:none;
  background:linear-gradient(100deg,transparent,rgba(255,255,255,.55),transparent);transform:skewX(-18deg);
  transition:left .7s cubic-bezier(.2,.8,.2,1);}
.stDownloadButton button:hover::after{left:130%;}
.stDownloadButton button:active{transform:scale(.97) !important;}
[data-testid="stNumberInput"] div[data-baseweb="input"],[data-testid="stNumberInput"] div[data-baseweb="base-input"]{
  background:var(--glass) !important;border:1px solid var(--line) !important;border-radius:16px !important;
  backdrop-filter:blur(26px);-webkit-backdrop-filter:blur(26px);transition:border-color .3s ease,box-shadow .3s ease;}
[data-testid="stNumberInput"] div[data-baseweb="input"]:focus-within{border-color:var(--glow) !important;box-shadow:0 0 0 3px var(--sweep);}
[data-testid="stNumberInput"] input{color:var(--text) !important;font-weight:700;font-variant-numeric:tabular-nums;}
[data-testid="stNumberInput"] button{background:transparent !important;color:var(--text) !important;border:0 !important;}
[data-testid="stNumberInput"] button:hover{background:var(--sweep) !important;}

/* KPI */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin:1.2rem 0;}
.kpi{border-radius:22px;padding:1.2rem 1.3rem;}
.kpi .l{color:var(--muted);font-size:.85rem;font-weight:500;}
.kpi .v{font-size:1.7rem;font-weight:800;letter-spacing:-.02em;margin-top:.35rem;font-variant-numeric:tabular-nums;color:var(--text);}
.neg{color:#FF6F8E !important;}

/* Barre des shifts */
.shifts{border-radius:22px;padding:1.3rem;}
.shifts .t{font-weight:700;margin-bottom:.9rem;color:var(--text);}
.bar{display:flex;height:12px;gap:3px;border-radius:99px;overflow:hidden;background:rgba(127,127,160,.15);}
.bar span{display:block;height:100%;border-radius:99px;transform-origin:left;animation:grow .9s cubic-bezier(.2,.8,.2,1) backwards;}
@keyframes grow{from{transform:scaleX(0);}to{transform:scaleX(1);}}
.legend{display:flex;flex-wrap:wrap;gap:1.4rem;margin-top:1rem;color:var(--muted);font-size:.9rem;}
.legend b{color:var(--text);font-variant-numeric:tabular-nums;}
.legend i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:.45rem;}

/* Tableaux */
.tw{border-radius:20px;overflow:auto;max-height:420px;}
.tw table{width:100%;border-collapse:collapse;font-size:.92rem;font-variant-numeric:tabular-nums;}
.tw th,.tw td{padding:.7rem 1rem;text-align:left;white-space:nowrap;border-bottom:1px solid var(--line);color:var(--text);}
.tw th{position:sticky;top:0;background:var(--thbg);color:var(--muted);font-weight:500;}
.tw tr:last-child td{border-bottom:0;}
.tw .r{text-align:right;}

/* Boutons */
.stDownloadButton button{
  background:linear-gradient(135deg,#7C8CFF,#FF8AD8) !important;color:#0C0E1A !important;
  font-weight:700 !important;border:none !important;border-radius:14px !important;padding:.7rem 1.4rem !important;
  transition:transform .25s ease,box-shadow .25s ease !important;}
.stDownloadButton button:hover{transform:translateY(-2px);box-shadow:0 12px 28px rgba(124,140,255,.4) !important;}
.stDownloadButton button:focus-visible{outline:2px solid var(--text);outline-offset:3px;}
@media (prefers-reduced-motion:reduce){.ice::before,.bar span{animation:none;}}
</style>
"""


def build_css(dark: bool) -> str:
    t = THEMES[dark]
    css = CSS_TEMPLATE
    css = css.replace("__noiseLo__", noise(".10", t["noiseC"]))
    css = css.replace("__noiseHi__", noise(".16", t["noiseC"]))
    for k, v in t.items():
        css = css.replace(f"__{k}__", v)
    return css


ICE_HTML = '<div class="ice"><i></i><i></i><i></i></div>'

CARD_HTML = """
<!doctype html><html><head><meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&display=swap');
html,body{margin:0;background:transparent;font-family:'Manrope',sans-serif;color:#fff;}
.stage{height:330px;display:flex;align-items:center;justify-content:center;perspective:1100px;--sh:__SH__;}
.card{
  position:relative;width:min(460px,92vw);aspect-ratio:1.62;border-radius:26px;padding:26px 28px;
  box-sizing:border-box;overflow:hidden;
  background:linear-gradient(135deg,#2A2F7A 0%,#5A3FA8 48%,#C0509E 100%);
  box-shadow:var(--sh),inset 0 1px 1px rgba(255,255,255,.35);
  transform-style:preserve-3d;
  transform:rotateX(var(--rx,8deg)) rotateY(var(--ry,-14deg));
  transition:transform .15s ease-out;
  animation:enter 1.1s cubic-bezier(.2,.8,.2,1) both, float 6s ease-in-out 1.1s infinite;
}
.card::before{
  content:"";position:absolute;inset:0;pointer-events:none;mix-blend-mode:soft-light;
  background:
    repeating-radial-gradient(circle at 15% 130%,transparent 0 7px,rgba(255,255,255,.10) 7px 8px),
    repeating-radial-gradient(circle at 95% -30%,transparent 0 9px,rgba(255,255,255,.08) 9px 10px);
}
.card::after{
  content:"";position:absolute;top:0;bottom:0;width:40%;left:-60%;pointer-events:none;
  background:linear-gradient(100deg,transparent,rgba(255,255,255,.28),transparent);
  transform:skewX(-18deg);animation:shine 1.6s ease-out .9s 1 both;
}
.glare{position:absolute;inset:0;pointer-events:none;mix-blend-mode:soft-light;background:radial-gradient(circle at var(--mx,25%) var(--my,0%),rgba(255,255,255,.34),transparent 48%);}
.row{position:relative;display:flex;justify-content:space-between;align-items:center;transform:translateZ(30px);}
.chip{font-size:12px;font-weight:700;padding:5px 11px;border-radius:99px;background:rgba(255,255,255,.16);}
.dots{display:flex;gap:5px;}
.dots i{width:9px;height:9px;border-radius:50%;display:block;}
.mid{position:relative;margin-top:30px;transform:translateZ(55px);}
.lab{font-size:13px;opacity:.75;font-weight:500;}
.amt{font-size:42px;font-weight:800;letter-spacing:-.03em;margin-top:2px;font-variant-numeric:tabular-nums;}
.bot{position:absolute;left:28px;right:28px;bottom:22px;display:flex;justify-content:space-between;
     font-size:12.5px;font-weight:600;opacity:.9;transform:translateZ(30px);}
.bot span{opacity:.7;font-weight:500;display:block;font-size:11.5px;}
@keyframes enter{from{opacity:0;transform:rotateX(35deg) rotateY(-30deg) translateY(50px) scale(.92);}}
@keyframes float{0%,100%{translate:0 0;}50%{translate:0 -10px;}}
@keyframes shine{to{left:130%;}}
@media (prefers-reduced-motion:reduce){.card,.card::after{animation:none;}}
</style></head><body>
<div class="stage" id="stage"><div class="card" id="card"><div class="glare"></div>
  <div class="row"><div class="chip">Facture OFM</div>
    <div class="dots"><i style="background:#FFC38A"></i><i style="background:#8FD3FF"></i><i style="background:#FF8FA3"></i><i style="background:#8C7BFF"></i></div></div>
  <div class="mid"><div class="lab">__LABEL__</div><div class="amt" data-raw="__RAW__">__AMOUNT__</div></div>
  <div class="bot"><div><span>Commission __PCT__ % du CA net</span>__COMM__</div><div style="text-align:right"><span>Transactions</span>__NB__</div></div>
</div></div>
<script>
const c=document.getElementById('card'),s=document.getElementById('stage'),a=document.querySelector('.amt');
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
if(!reduced){
  s.addEventListener('pointermove',e=>{
    const r=s.getBoundingClientRect();
    const x=(e.clientX-r.left)/r.width-.5, y=(e.clientY-r.top)/r.height-.5;
    c.style.setProperty('--ry',(x*28)+'deg'); c.style.setProperty('--rx',(-y*22)+'deg');
    c.style.setProperty('--mx',((x+.5)*100)+'%'); c.style.setProperty('--my',((y+.5)*100)+'%');
  });
  s.addEventListener('pointerleave',()=>{c.style.setProperty('--ry','-14deg');c.style.setProperty('--rx','8deg');});
  const raw=parseFloat(a.dataset.raw);
  if(raw){const t0=performance.now();
    const f=t=>{const p=Math.min((t-t0)/1100,1),k=1-Math.pow(1-p,3);
      a.textContent=(raw*k).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})+' $';
      if(p<1)requestAnimationFrame(f);};
    requestAnimationFrame(f);}
}
</script></body></html>
"""
# --- THEME END -------------------------------------------------------------


def html(block: str):
    """Affiche du HTML : pas d'indentation (sinon bloc de code Markdown) et
    '$' échappé (sinon Streamlit le prend pour du LaTeX)."""
    clean = "\n".join(l.strip() for l in block.splitlines() if l.strip())
    st.markdown(clean.replace("$", "&#36;"), unsafe_allow_html=True)


def carte_3d(net, commission, nb, dark, pct):
    page = (
        CARD_HTML.replace("__SH__", THEMES[dark]["cardsh"])
        .replace("__LABEL__", "Net estimé")
        .replace("__RAW__", f"{net:.2f}")
        .replace("__AMOUNT__", f"{net:,.2f} $")
        .replace("__COMM__", f"{commission:,.2f} $")
        .replace("__NB__", str(nb))
        .replace("__PCT__", f"{pct:g}")
    )
    components.html(page, height=340)


LIBELLES = {"Modele": "Modèle", "Montant_USD": "Montant USD", "Ventes_Cumulees": "Ventes cumulées"}


def tableau(df, num=(), entiers=()):
    cols = list(df.columns)
    tete = "".join(
        f'<th class="{"r" if c in num else ""}">{escape(LIBELLES.get(c, c))}</th>' for c in cols
    )
    lignes = []
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            if c in num:
                v = float(r[c])
                txt = f"{int(v)}" if c in entiers else f"{v:,.2f}"
                cells.append(f'<td class="r{" neg" if v < 0 else ""}">{txt}</td>')
            else:
                cells.append(f"<td>{escape(str(r[c]))}</td>")
        lignes.append("<tr>" + "".join(cells) + "</tr>")
    html(f'<div class="tw"><table><tr>{tete}</tr>{"".join(lignes)}</table></div>')


def normaliser_shift(s: str) -> str:
    return s.lower().strip().replace("apres-midi", "après-midi")


# ─────────────────────────────────────────────────────────────
# EXTRACTION (logique inchangée)
# ─────────────────────────────────────────────────────────────
def extraire_donnees_pdf(pdf_file):
    donnees = []
    total_brut_pdf = 0.0
    commission_pdf = 0.0
    amendes_val = 0.0
    amendes_devise = "EUR"

    regex_transaction = re.compile(
        r"^(\d{2}/\d{2}/\d{4})\s+(.*?)\s+(matin|après-midi|apres-midi|soir|nuit)\s+(-?\d+\.\d{2})\s+\$\s+USD"
    )
    regex_total = re.compile(r"TOTAL\s+(\d+\.\d{2})\s+\$\s+USD")
    regex_commission = re.compile(r"Commission\s+USD\s+\(.*?\)\s+(\d+\.\d{2})\s*\$")
    regex_amendes = re.compile(r"Amendes\s+déduites\s+(-?\d+\.\d{2})\s*(€|\$)", re.IGNORECASE)

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            texte = page.extract_text()
            if not texte:
                continue
            for ligne in texte.split("\n"):
                ligne_clean = ligne.strip()

                match_tx = regex_transaction.search(ligne_clean)
                if match_tx:
                    date, reste_texte, shift, montant = match_tx.groups()
                    mots = reste_texte.split()
                    if len(mots) >= 2:
                        if mots[-1] == "refund" and mots[-2] == "(refund)":
                            type_shift = "(refund) refund"
                            modele = " ".join(mots[:-2])
                        else:
                            type_shift = mots[-1]
                            modele = " ".join(mots[:-1])
                    else:
                        modele = reste_texte
                        type_shift = "N/A"

                    donnees.append({
                        "Date": date,
                        "Modele": modele.strip(),
                        "Type": type_shift.strip(),
                        "Shift": normaliser_shift(shift),
                        "Montant_USD": float(montant),
                    })
                    continue

                match_tot = regex_total.search(ligne_clean)
                if match_tot and total_brut_pdf == 0.0:
                    total_brut_pdf = float(match_tot.group(1))

                match_comm = regex_commission.search(ligne_clean)
                if match_comm:
                    commission_pdf = float(match_comm.group(1))

                match_amende = regex_amendes.search(ligne_clean)
                if match_amende:
                    amendes_val = float(match_amende.group(1))
                    amendes_devise = match_amende.group(2)

    df = pd.DataFrame(donnees)
    return df, total_brut_pdf, commission_pdf, amendes_val, amendes_devise


# ─────────────────────────────────────────────────────────────
# INTERFACE
# ─────────────────────────────────────────────────────────────
col_marque, col_theme = st.columns([5, 1])
with col_marque:
    html('<div class="top"><span class="dot"></span>OF Analytics</div>')
with col_theme:
    dark = st.toggle("Mode sombre", value=True, key="dark")

st.markdown(build_css(dark), unsafe_allow_html=True)
st.markdown(ICE_HTML, unsafe_allow_html=True)

html("""
<h1 class="h1">Vos factures OFM,<br>lues en quelques secondes.</h1>
<p class="lead">Déposez le PDF de la facture. Les ventes sont regroupées par modèle et par moment de la journée, puis exportées en Excel.</p>
""")

col_taux, col_pdf = st.columns([1, 3])
with col_taux:
    pct = st.number_input(
        "Commission (% du CA net)", min_value=0.0, max_value=100.0, value=5.0, step=0.5, format="%.1f", key="pct", help="Pourcentage appliqué au CA net de la facture."
    )
with col_pdf:
    fichier_charge = st.file_uploader("Facture PDF", type="pdf")

if fichier_charge is None:
    carte_3d(0, 0, 0, dark, pct)
else:
    with st.spinner("Lecture de la facture…"):
        df, total_brut_pdf, commission_pdf, amendes_val, amendes_devise = extraire_donnees_pdf(fichier_charge)

    if df.empty:
        st.error("Aucune transaction trouvée. Vérifiez que le PDF est bien une facture OFM au format attendu.")
    else:
        repartition = (
            df.groupby("Modele")["Montant_USD"]
            .agg(Ventes_Cumulees="sum", Transactions="count")
            .reset_index()
            .sort_values(by="Ventes_Cumulees", ascending=False)
        )

        ca_net = df["Montant_USD"].sum()
        commission_calculee = ca_net * pct / 100
        net_estim = commission_calculee + amendes_val

        carte_3d(net_estim, commission_calculee, len(df), dark, pct)

        amende_txt = f"{amendes_val:.2f} {amendes_devise}" if amendes_val != 0 else "Aucune"
        amende_cls = "neg" if amendes_val < 0 else ""
        html(f"""
        <div class="kpis">
        <div class="kpi"><div class="l">CA net</div><div class="v">{ca_net:,.2f} $</div></div>
        <div class="kpi"><div class="l">Commission ({pct:g} % du CA net)</div><div class="v">{commission_calculee:,.2f} $</div></div>
        <div class="kpi"><div class="l">Amendes</div><div class="v {amende_cls}">{amende_txt}</div></div>
        </div>
        """)

        par_shift = df.groupby("Shift")["Montant_USD"].sum()
        ordre = [s for s in SHIFT_COLORS if s in par_shift.index]
        positifs = {s: max(par_shift[s], 0) for s in ordre}
        somme = sum(positifs.values()) or 1
        segments = "".join(
            f'<span style="width:{positifs[s] / somme * 100:.2f}%;background:{SHIFT_COLORS[s]};'
            f'animation-delay:{i * 0.12:.2f}s"></span>'
            for i, s in enumerate(ordre)
        )
        legende = "".join(
            f'<div><i style="background:{SHIFT_COLORS[s]}"></i>{s.capitalize()} <b>{par_shift[s]:,.2f} $</b></div>'
            for s in ordre
        )
        html(f"""
        <div class="shifts"><div class="t">Ventes par moment de la journée</div>
        <div class="bar">{segments}</div>
        <div class="legend">{legende}</div></div>
        """)

        html('<h2 class="sec">Répartition par modèle</h2>')
        tableau(repartition, num=("Ventes_Cumulees", "Transactions"), entiers=("Transactions",))

        html('<h2 class="sec">Toutes les transactions</h2>')
        tableau(df, num=("Montant_USD",))

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            repartition.to_excel(writer, sheet_name="Repartition_Modeles", index=False)
            df.to_excel(writer, sheet_name="Transactions_Detaillees", index=False)

        st.write("")
        st.download_button(
            label="Télécharger le rapport Excel",
            data=buffer.getvalue(),
            file_name="Rapport_Facture_Analyse.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
