import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

# --- Ρυθμίσεις ---
FIXED_COLUMNS = ["Α/Α", "Όνομα Υλικού", "Ποσότητα", "Συνολικό Κόστος"]
# Λέξεις κλειδιά που ΠΡΕΠΕΙ να υπάρχουν στην κεφαλίδα
REQUIRED_KEYWORDS = ["ΥΛΙΚΟΥ", "ΕΙΔΟΣ", "ΠΕΡΙΓΡΑΦΗ", "ΠΟΣΟΤΗΤΑ", "CPV", "ΠΡΟΥΠΟΛΟΓΙΣΜΟΣ"]

st.set_page_config(page_title="Refined Extractor", layout="wide")
st.title("📑 Precision Product Extractor")

def clean_numeric(value):
    if value is None or str(value).strip() == "": return 0.0
    s = str(value).replace('€', '').replace('$', '').strip()
    if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
    elif ',' in s: s = s.replace(',', '.')
    try:
        res = re.sub(r'[^\d.]', '', s)
        return float(res) if res else 0.0
    except: return 0.0

def is_valid_table(table_headers):
    """Ελέγχει αν ο πίνακας είναι όντως αυτός με τα προϊόντα"""
    header_str = " ".join([str(h).upper() for h in table_headers if h])
    matches = [key for key in REQUIRED_KEYWORDS if key in header_str]
    return len(matches) >= 2  # Πρέπει να βρει τουλάχιστον 2 λέξεις-κλειδιά

uploaded_file = st.file_uploader("Ανέβασε το PDF", type="pdf")

if uploaded_file:
    all_dfs = []
    
    with pdfplumber.open(uploaded_file) as pdf:
        num_pages = len(pdf.pages)
        progress_bar = st.progress(0)
        
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2: continue
                
                # Έλεγχος αν η πρώτη γραμμή μοιάζει με κεφαλίδα προϊόντων
                if is_valid_table(table[0]):
                    headers = [str(h).replace('\n', ' ').strip() if h else f"Col_{idx}" 
                               for idx, h in enumerate(table[0])]
                    
                    df_page = pd.DataFrame(table[1:], columns=headers)
                    all_dfs.append(df_page)
            
            progress_bar.progress((i + 1) / num_pages)

    if all_dfs:
        # Ένωση όλων των πινάκων
        final_df = pd.concat(all_dfs, ignore_index=True, sort=False)
        
        # Καθαρισμός διπλότυπων επικεφαλίδων που μπορεί να μπήκαν ως γραμμές
        # (Συμβαίνει όταν ο πίνακας συνεχίζει σε νέα σελίδα)
        for col in REQUIRED_KEYWORDS:
            if col in final_df.columns:
                final_df = final_df[~final_df[col].astype(str).str.contains(col, case=False, na=False)]

        # 1. Καθαρισμός κενών
        final_df = final_df.dropna(how='all')
        
        # 2. Εύρεση στήλης Α/Α και Όνομα Υλικού με "έξυπνο" τρόπο
        cols = final_df.columns
        aa_col = next((c for c in cols if "Α/Α" in c.upper() or "A/A" in c.upper()), None)
        descr_col = next((c for c in cols if any(k in c.upper() for k in ["ΥΛΙΚΟΥ", "ΕΙΔΟΣ", "ΠΕΡΙΓΡΑΦΗ"])), None)
        qty_col = next((c for c in cols if "ΠΟΣΟΤ" in c.upper()), None)
        cost_col = next((c for c in cols if "ΣΥΝΟΛ" in c.upper() or "ΠΡΟΥΠ" in c.upper()), None)

        # Μετονομασία για να ταιριάζουν με τα FIXED_COLUMNS μας
        rename_dict = {}
        if aa_col: rename_dict[aa_col] = "Α/Α"
        if descr_col: rename_dict[descr_col] = "Όνομα Υλικού"
        if qty_col: rename_dict[qty_col] = "Ποσότητα"
        if cost_col: rename_dict[cost_col] = "Συνολικό Κόστος"
        
        final_df = final_df.rename(columns=rename_dict)

        # 3. Φιλτράρισμα: Κρατάμε μόνο γραμμές που έχουν Α/Α (αριθμό)
        if "Α/Α" in final_df.columns:
            final_df = final_df[final_df["Α/Α"].fillna("").astype(str).str.strip().str.match(r'^\d+')]

        # 4. Μετατροπή Αριθμών
        for col in ["Ποσότητα", "Συνολικό Κόστος"]:
            if col in final_df.columns:
                final_df[col] = final_df[col].apply(clean_numeric)

        # Ταξινόμηση
        available_fixed = [c for c in FIXED_COLUMNS if c in final_df.columns]
        others = [c for c in final_df.columns if c not in FIXED_COLUMNS]
        final_df = final_df[available_fixed + others]

        st.success(f"Βρέθηκαν {len(final_df)} προϊόντα!")
        st.dataframe(final_df)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False)
        st.download_button("📥 Κατέβασμα Excel", output.getvalue(), "tender_results.xlsx")
    else:
        st.error("Δεν βρέθηκαν πίνακες που να ταιριάζουν με τα κριτήρια.")
