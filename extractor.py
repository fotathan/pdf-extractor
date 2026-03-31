import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

# --- Ρυθμίσεις ---
FIXED_COLUMNS = ["Α/Α", "Όνομα Υλικού", "Ποσότητα", "Συνολικό Κόστος"]
TARGET_KEYWORDS = ["ΥΛΙΚΟΥ", "ΠΟΣΟΤΗΤΑ", "ΕΙΔΟΣ", "ΠΕΡΙΓΡΑΦΗ", "CPV"]

st.set_page_config(page_title="Prokirixi AI Extractor", layout="wide")
st.title("📊 Smart PDF Prokirixi Extractor")

def clean_numeric(value):
    """Μετατρέπει κείμενο σε καθαρό αριθμό"""
    if value is None or str(value).strip() == "": return 0.0
    s = str(value).replace('€', '').replace('$', '').strip()
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        # Κρατάμε μόνο νούμερα και την τελεία
        res = re.sub(r'[^\d.]', '', s)
        return float(res) if res else 0.0
    except:
        return 0.0

def make_columns_unique(columns):
    """Διορθώνει το πρόβλημα των διπλότυπων στηλών (π.χ. ['A', 'A'] -> ['A', 'A_1'])"""
    new_cols = []
    counts = {}
    for col in columns:
        col = str(col).strip() if col else "Unnamed"
        if col in counts:
            counts[col] += 1
            new_cols.append(f"{col}_{counts[col]}")
        else:
            counts[col] = 0
            new_cols.append(col)
    return list(new_cols)

uploaded_file = st.file_uploader("Ανέβασε το PDF", type="pdf")

if uploaded_file:
    all_tables = []
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2: continue
                
                # Καθαρισμός και έλεγχος αν είναι ο πίνακας που θέλουμε
                headers = [str(h).upper() if h else "" for h in table[0]]
                is_target_table = any(key in " ".join(headers) for key in TARGET_KEYWORDS)
                
                if is_target_table:
                    # Διόρθωση διπλότυπων στηλών πριν το DataFrame
                    unique_headers = make_columns_unique(table[0])
                    df_tmp = pd.DataFrame(table[1:], columns=unique_headers)
                    all_tables.append(df_tmp)

    if all_tables:
        try:
            # Ένωση των πινάκων
            final_df = pd.concat(all_tables, ignore_index=True, sort=False)
            
            # Καθαρισμός ονομάτων (newline κλπ)
            final_df.columns = [str(c).replace('\n', ' ').strip() for c in final_df.columns]
            
            # Αφαίρεση γραμμών που είναι τελείως κενές
            final_df = final_df.dropna(how='all')
            # Αφαίρεση γραμμών που ο Α/Α είναι κενός (συνήθως είναι άσχετα κείμενα)
            if "Α/Α" in final_df.columns:
                final_df = final_df[final_df["Α/Α"].fillna("").astype(str).str.strip() != ""]

            # Μετατροπή σε Αριθμούς
            numeric_cols = ["Ποσότητα", "Κόστος", "Συνολικό Κόστος", "Τιμή", "ΠΟΣΟΤΗΤΑ", "Ποσ."]
            for col in final_df.columns:
                if any(n in col for n in numeric_cols):
                    final_df[col] = final_df[col].apply(clean_numeric)

            # Ταξινόμηση Στηλών
            found_fixed = [col for col in FIXED_COLUMNS if col in final_df.columns]
            extra_cols = [col for col in final_df.columns if col not in FIXED_COLUMNS]
            final_df = final_df[found_fixed + extra_cols]

            st.success(f"Βρέθηκαν {len(final_df)} προϊόντα!")
            st.dataframe(final_df, use_container_width=True)

            # Excel Export
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                final_df.to_excel(writer, index=False)
            
            st.download_button("📥 Κατέβασμα Excel", output.getvalue(), "tender_data.xlsx")

        except Exception as e:
            st.error(f"Σφάλμα κατά την επεξεργασία: {e}")
    else:
        st.warning("Δεν εντοπίστηκε πίνακας με τα ζητούμενα προϊόντα.")
