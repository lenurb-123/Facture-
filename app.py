import streamlit as st
import re
import pdfplumber
import pandas as pd
import io

st.set_page_config(
    page_title="OF Analytics - Premium Invoice Parser",
    layout="wide",
    page_icon="💎",
    initial_sidebar_state="collapsed"
)

# Design Néon 3D Haut de Gamme style Awwwards
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
* {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.stApp {
    background: radial-gradient(circle at 50% 50%, #14151a 0%, #0b0c10 100%);
    color: #f3f4f6;
}
@keyframes slideUp {
    0% { opacity: 0; transform: translateY(40px) scale(0.98); }
    100% { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes glowPulse {
    0% { box-shadow: 0 0 10px rgba(0, 255, 178, 0.2); }
    50% { box-shadow: 0 0 25px rgba(0, 255, 178, 0.4); }
    100% { box-shadow: 0 0 10px rgba(0, 255, 178, 0.2); }
}
.premium-header {
    text-align: center;
    padding: 40px 20px;
    animation: slideUp 1s cubic-bezier(0.16, 1, 0.3, 1) both;
}
.premium-title {
    background: linear-gradient(135deg, #00ffb2 0%, #0077ff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 3.5rem !important;
    font-weight: 800 !important;
    letter-spacing: -1.5px;
    margin-bottom: 10px;
}
.premium-subtitle {
    color: #9ca3af;
    font-size: 1.2rem;
    font-weight: 300;
}
div[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 24px;
    padding: 25px !important;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3), inset 0 1px 1px rgba(255, 255, 255, 0.1);
    transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    animation: slideUp 1.2s cubic-bezier(0.16, 1, 0.3, 1) both;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-8px) scale(1.02);
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(0, 255, 178, 0.4);
    box-shadow: 0 30px 60px rgba(0, 255, 178, 0.15);
}
.stButton>button {
    background: linear-gradient(135deg, #00ffb2 0%, #00b8ff 100%) !important;
    color: #000000 !important;
    border: none !important;
    font-weight: 700 !important;
    border-radius: 14px !important;
    padding: 14px 28px !important;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
    box-shadow: 0 8px 20px rgba(0, 255, 178, 0.3) !important;
}
.stButton>button:hover {
    transform: scale(1.05) translateY(-2px) !important;
    box-shadow: 0 15px 30px rgba(0, 255, 178, 0.5) !important;
}
div[data-testid="stFileUploader"] {
    background: rgba(255, 255, 255, 0.02);
    border: 2px dashed rgba(0, 255, 178, 0.3);
    border-radius: 24px;
    padding: 30px !important;
    transition: all 0.4s ease;
}
div[data-testid="stFileUploader"]:hover {
    border-color: #00ffb2;
    background: rgba(0, 255, 178, 0.02);
    animation: glowPulse 2s infinite;
}
</style>""", unsafe_allow_html=True)

# Titre principal en HTML
st.markdown("""<div class='premium-header'>
    <h1 class='premium-title'>OF ANALYTICS ENGINE</h1>
    <p class='premium-subtitle'>L'extraction de factures nouvelle génération dotée d'une intelligence 3D</p>
</div>""")

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
                        if mots[-1] in ["N/A", "refund"] or (len(mots) > 2 and mots[-2] == "(refund)" and mots[-1] == "refund"):
                            if mots[-1] == "refund" and mots[-2] == "(refund)":
                                type_shift = "(refund) refund"
                                modele = " ".join(mots[:-2])
                            else:
                                type_shift = mots[-1]
                                modele = " ".join(mots[:-1])
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
                        "Shift": shift.strip(),
                        "Montant_USD": float(montant)
                    })
                    continue

                match_tot = regex_total.search(ligne_clean)
                if match_tot and total_brut_pdf == 0.0:
                    total_brut_pdf = float(match_tot.group(1))

                match_comm = regex_commission.search(ligne_clean)
                if match_comm:
                    commission_pdf = float(match_comm.group(2)) if len(match_comm.groups()) > 1 else float(match_comm.group(1))

                match_amende = regex_amendes.search(ligne_clean)
                if match_amende:
                    amendes_val = float(match_amende.group(1))
                    amendes_devise = match_amende.group(2)

    df = pd.DataFrame(donnees)
    return df, total_brut_pdf, commission_pdf, amendes_val, amendes_devise

fichier_charge = st.file_uploader("Déposez votre facture PDF ici", type="pdf")

if fichier_charge is not None:
    with st.spinner("Analyse du document..."):
        df, total_brut_pdf, commission_pdf, amendes_val, amendes_devise = extraire_donnees_pdf(fichier_charge)

    if not df.empty:
        st.success("Facture analysée avec succès !")

        repartition = df.groupby("Modele")["Montant_USD"].agg(Ventes_Cumulees="sum", Transactions="count").reset_index()
        repartition = repartition.sort_values(by="Ventes_Cumulees", ascending=False)

        total_calcule = df["Montant_USD"].sum()
        commission_calculee = total_calcule * 0.05

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Brut Cumulé", f"{total_calcule:.2f} $ USD")
        col2.metric("Commission d'Agence (5%)", f"{commission_calculee:.2f} $ USD")
        col3.metric("Amendes détectées", f"{amendes_val:.2f} {amendes_devise}" if amendes_val != 0 else "Aucune")
        
        net_estim = commission_calculee + amendes_val if amendes_val != 0 else commission_calculee
        col4.metric("Net Estimé (USD)", f"{net_estim:.2f} $")

        st.subheader("📈 Répartition par Modèle")
        st.dataframe(repartition, use_container_width=True)

        st.subheader("📋 Détail de toutes les transactions")
        st.dataframe(df, use_container_width=True)

        st.subheader("📥 Télécharger les résultats")
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            repartition.to_excel(writer, sheet_name='Repartition_Modeles', index=False)
            df.to_excel(writer, sheet_name='Transactions_Detaillees', index=False)

        st.download_button(
            label="📥 Télécharger au format Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name="Rapport_Facture_Analyse.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Aucune donnée de transaction n'a pu être extraite de ce PDF.")
