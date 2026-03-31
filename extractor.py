import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

# --- Ρυθμίσεις ---
# Ορίζουμε τις στήλες που "κλειδώνουν" αριστερά
FIXED_COLUMNS = ["Α/Α", "Όνομα Υλικού", "Ποσότητα", "Συνολικό Κόστος"]
# Λέξεις κλειδιά για να καταλάβουμε αν ένας πίνακας είναι αυτός που θέλουμε
TARGET_KEYWORDS = ["ΥΛΙΚΟΥ", "ΠΟΣΟΤΗΤΑ", "ΕΙΔΟΣ", "ΠΕΡΙΓΡΑΦΗ"]

st.set_page_config(page_title="Prokirixi AI Extractor", layout="wide")
st.title("📊 Smart PDF Prokirixi Extractor")

def clean_numeric(value):
    """Μετατρέπει κείμενο σε καθαρό αριθμό (π.χ. '1.246,00 €' -> 1246.00)"""
    if value is None: return 0.0
    s = str(value).replace('€', '').replace('$', '').strip()
    # Αν έχει μορφή 1.000,00 (ελληνική)
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    
    try:
        return float(re.sub(r'[^\d.]', '', s))
    except:
        return 0.0

uploaded_file = st.file_uploader("Ανέβασε το PDF", type="pdf")

if uploaded_file:
    all_tables = []
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2: continue
                
                # Έλεγχος αν ο πίνακας περιέχει τις λέξεις-κλειδιά μας στις κεφαλίδες
                headers = [str(h).upper() for h in table[0] if h]
                is_target_table = any(key in " ".join(headers) for key in TARGET_KEYWORDS)
                
                if is_target_table:
                    df_tmp = pd.DataFrame(table[1:], columns=table[0])
                    all_tables.append(df_tmp)

    if all_tables:
        # Ένωση όλων των σωστών πινάκων σε έναν
        final_df = pd.concat(all_tables, ignore_index=True, sort=False)
        
        # 1. Καθαρισμός ονομάτων στηλών
        final_df.columns = [str(c).replace('\n', ' ').strip() for c in final_df.columns]
        
        # 2. Φιλτράρισμα: Κράτα μόνο γραμμές που έχουν Α/Α ή Όνομα (διώχνει τις κενές)
        final_df = final_df[final_df.iloc[:, 0].astype(str).str.strip() != ""]

        # 3. Μετατροπή Numerical Data
        numeric_targets = ["Ποσότητα", "Κόστος", "Συνολικό Κόστος", "Τιμή", "ΠΟΣΟΤΗΤΑ"]
        for col in final_df.columns:
            if any(target in col for target in numeric_targets):
                final_df[col] = final_df[col].apply(clean_numeric)

        # 4. Ταξινόμηση στηλών
        found_fixed = [col for col in FIXED_COLUMNS if col in final_df.columns]
        extra_cols = [col for col in final_df.columns if col not in FIXED_COLUMNS]
        final_df = final_df[found_fixed + extra_cols]

        st.subheader("✅ Τελικά Δεδομένα")
        st.dataframe(final_df)

        # Download
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False)
        
        st.download_button("Κατέβασμα Excel", output.getvalue(), "cleaned_data.xlsx")
    else:
        st.warning("Δεν βρέθηκε πίνακας με προϊόντα. Σιγουρέψου ότι το PDF δεν είναι σκαναρισμένη εικόνα.")
