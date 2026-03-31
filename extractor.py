import streamlit as st
import pdfplumber
import pandas as pd
from io import BytesIO

# --- Ρυθμίσεις ---
FIXED_COLUMNS = ["Α/Α", "Όνομα Υλικού", "Ποσότητα", "Συνολικό Κόστος"]

st.set_page_config(page_title="PDF Table Extractor", layout="wide")

st.title("📄 PDF to Excel Extractor")
st.write("Ανέβασε την προκήρυξη και πάρε αυτόματα τις στήλες που θέλεις!")

# --- Upload Αρχείου ---
uploaded_file = st.file_uploader("Επίλεξε το PDF αρχείο", type="pdf")

if uploaded_file is not None:
    all_dfs = []
    
    with pdfplumber.open(uploaded_file) as pdf:
        with st.spinner('Επεξεργασία PDF...'):
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if len(table) > 1:
                        headers = [str(h).replace('\n', ' ').strip() if h else f"Στήλη_{i+1}" 
                                   for i, h in enumerate(table[0])]
                        rows = table[1:]
                        try:
                            temp_df = pd.DataFrame(rows, columns=headers)
                            all_dfs.append(temp_df)
                        except:
                            continue

    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True, sort=False)
        combined_df.columns = [str(c).strip() for c in combined_df.columns]
        
        # Ταξινόμηση στηλών (Fixed + Extras)
        found_fixed = [col for col in FIXED_COLUMNS if col in combined_df.columns]
        extra_cols = [col for col in combined_df.columns if col not in FIXED_COLUMNS]
        final_df = combined_df[found_fixed + extra_cols].dropna(how='all')

        # Εμφάνιση Προεπισκόπησης
        st.subheader("👀 Προεπισκόπηση Δεδομένων")
        st.dataframe(final_df, use_container_width=True)

        # --- Μετατροπή σε Excel για κατέβασμα ---
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Κατέβασμα σε Excel (.xlsx)",
            data=output.getvalue(),
            file_name="extracted_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.success("Έτοιμο! Μπορείς να κατεβάσεις το αρχείο και να το κάνεις Import στο Google Sheets.")
    else:
        st.error("Δεν βρέθηκαν πίνακες στο αρχείο.")
