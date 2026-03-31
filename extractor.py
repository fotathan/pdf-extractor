import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

# --- Ρυθμίσεις ---
FIXED_COLUMNS = ["Α/Α", "Όνομα Υλικού", "Ποσότητα", "Συνολικό Κόστος"]
# Λέξεις κλειδιά που υποδηλώνουν την ύπαρξη πίνακα προϊόντων
TARGET_KEYWORDS = ["ΥΛΙΚΟΥ", "ΠΟΣΟΤΗΤΑ", "ΕΙΔΟΣ", "ΠΕΡΙΓΡΑΦΗ", "CPV", "ΠΡΟΔΙΑΓΡΑΦΕΣ", "ΠΟΣΟΤ."]

st.set_page_config(page_title="AI Multi-Page Extractor", layout="wide")
st.title("📑 Full Document Product Extractor")
st.write("Αυτό το script σαρώνει και τις 122+ σελίδες για να βρει κάθε πίνακα προϊόντων.")

def clean_numeric(value):
    if value is None or str(value).strip() == "": return 0.0
    s = str(value).replace('€', '').replace('$', '').strip()
    if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
    elif ',' in s: s = s.replace(',', '.')
    try:
        res = re.sub(r'[^\d.]', '', s)
        return float(res) if res else 0.0
    except: return 0.0

def make_columns_unique(columns):
    new_cols = []
    counts = {}
    for col in columns:
        col = str(col).replace('\n', ' ').strip() if col else "Unnamed"
        if col in counts:
            counts[col] += 1
            new_cols.append(f"{col}_{counts[col]}")
        else:
            counts[col] = 0
            new_cols.append(col)
    return new_cols

uploaded_file = st.file_uploader("Ανέβασε το μεγάλο PDF", type="pdf")

if uploaded_file:
    all_rows = []
    headers_found = None
    
    with pdfplumber.open(uploaded_file) as pdf:
        progress_bar = st.progress(0)
        num_pages = len(pdf.pages)
        
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 1: continue
                
                # Μετατροπή σε κεφαλαία για έλεγχο
                first_row_str = " ".join([str(cell).upper() for cell in table[0] if cell])
                
                # Αν βρούμε τις λέξεις κλειδιά, ορίζουμε αυτόν τον πίνακα ως στόχο
                if any(key in first_row_str for key in TARGET_KEYWORDS):
                    if not headers_found:
                        headers_found = make_columns_unique(table[0])
                    
                    # Προσθήκη των δεδομένων (χωρίς την κεφαλίδα αν την έχουμε ήδη βρει)
                    start_index = 1 if any(key in first_row_str for key in TARGET_KEYWORDS) else 0
                    for row in table[start_index:]:
                        # Έλεγχος αν η γραμμή έχει δεδομένα (όχι μόνο κενά)
                        if any(cell and str(cell).strip() for cell in row):
                            # Προσαρμογή μήκους γραμμής αν διαφέρει από τα headers
                            if len(row) == len(headers_found):
                                all_rows.append(row)
            
            progress_bar.progress((i + 1) / num_pages)

    if all_rows and headers_found:
        final_df = pd.DataFrame(all_rows, columns=headers_found)
        
        # Καθαρισμός στηλών
        final_df.columns = [str(c).strip() for c in final_df.columns]
        
        # Φιλτράρισμα: Διώχνουμε γραμμές που ο Α/Α ή το Όνομα είναι κενά (π.χ. σύνολα, υπογραφές)
        # Προσαρμόζουμε το όνομα της στήλης Α/Α γιατί μπορεί να έχει κενά
        aa_col = [c for c in final_df.columns if "Α/Α" in c.upper() or "A/A" in c.upper()]
        if aa_col:
            final_df = final_df[final_df[aa_col[0]].fillna("").astype(str).str.strip() != ""]

        # Μετατροπή αριθμών
        numeric_cols = ["ΠΟΣΟΤΗΤΑ", "ΠΟΣΟΤ", "ΤΙΜΗ", "ΚΟΣΤΟΣ", "ΣΥΝΟΛΟ"]
        for col in final_df.columns:
            if any(n in col.upper() for n in numeric_cols):
                final_df[col] = final_df[col].apply(clean_numeric)

        # Ταξινόμηση
        found_fixed = [col for col in FIXED_COLUMNS if col in final_df.columns]
        extra_cols = [col for col in final_df.columns if col not in FIXED_COLUMNS]
        final_df = final_df[found_fixed + extra_cols]

        st.success(f"Επιτυχής σάρωση! Βρέθηκαν συνολικά {len(final_df)} γραμμές προϊόντων.")
        st.dataframe(final_df)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False)
        st.download_button("📥 Κατέβασμα Πλήρους Excel", output.getvalue(), "full_tender_data.xlsx")
    else:
        st.error("Δεν βρέθηκαν πίνακες προϊόντων. Βεβαιωθείτε ότι το PDF περιέχει κείμενο και όχι εικόνες.")
