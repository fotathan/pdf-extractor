import streamlit as st
import pdfplumber
import pandas as pd
import json
import requests
from io import BytesIO

st.set_page_config(page_title="Direct AI PDF Extractor", layout="wide")
st.title("🤖 AI-Powered PDF Extractor (Direct API)")

st.write("Αυτό το εργαλείο διαβάζει το κείμενο του PDF και το στέλνει απευθείας στο Gemini API χωρίς ενδιάμεσες βιβλιοθήκες.")

# 1. Πεδία εισαγωγής
api_key = st.text_input("1. Εισάγετε το Gemini API Key σας", type="password")
uploaded_file = st.file_uploader("2. Ανεβάστε το PDF της προκήρυξης", type="pdf")

if api_key and uploaded_file:
    # Βήμα 1: Ανάγνωση του κειμένου από το PDF
    all_text = ""
    with st.spinner("⏳ Διαβάζω το κείμενο του PDF (όλες τις σελίδες)..."):
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text += text + "\n"
                    
    if all_text.strip() == "":
        st.error("❌ Δεν βρέθηκε κείμενο στο PDF. Μήπως είναι σκαναρισμένη φωτογραφία;")
    else:
        # Βήμα 2: Αποστολή στο Gemini API μέσω Requests
        with st.spinner("🤖 Το AI επεξεργάζεται τα δεδομένα και φτιάχνει τον πίνακα..."):
            
            # Χρήση του ασφαλούς v1 endpoint και του σταθερού μοντέλου
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
            
            prompt = f"""
            Ανάλυσε το παρακάτω κείμενο που προέρχεται από μια προκήρυξη και εξήγαγε ΟΛΑ τα προϊόντα/υλικά από όλους τους πίνακες που υπάρχουν.
            Θέλω να μου επιστρέψεις ΜΟΝΟ μια έγκυρη JSON λίστα (array) από αντικείμενα (objects).
            Μην γράψεις κανένα άλλο κείμενο, εξήγηση ή σχόλιο πριν ή μετά το JSON.
            
            Κάθε αντικείμενο στη λίστα πρέπει να αντιπροσωπεύει μια γραμμή προϊόντος και να έχει τα εξής keys:
            - "Α/Α"
            - "Όνομα Υλικού"
            - "Ποσότητα"
            - "Συνολικό Κόστος"
            Αν υπάρχουν επιπλέον στήλες (π.χ. CPV, Μονάδα Μέτρησης, Τιμή Μονάδος), πρόσθεσέ τις ως έξτρα keys.
            Σιγουρέψου ότι δεν θα χάσεις κανένα προϊόν.
            
            Κείμενο:
            {all_text}
            """
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            headers = {'Content-Type': 'application/json'}
            
            try:
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code != 200:
                    st.error(f"Σφάλμα API ({response.status_code}): {response.text}")
                else:
                    res_json = response.json()
                    text_response = res_json['candidates'][0]['content']['parts'][0]['text']
                    
                    # --- Καθαρισμός του JSON αν το AI έβαλε ```json ή ``` ---
                    text_response = text_response.strip()
                    if text_response.startswith("```json"):
                        text_response = text_response[7:]
                    elif text_response.startswith("```"):
                        text_response = text_response[3:]
                    
                    if text_response.endswith("```"):
                        text_response = text_response[:-3]
                        
                    text_response = text_response.strip()
                    # --------------------------------------------------------
                    
                    # Μετατροπή του JSON κειμένου σε DataFrame
                    data = json.loads(text_response)
                    df = pd.DataFrame(data)
                    
                    st.success(f"Επιτυχία! Το AI εντόπισε {len(df)} προϊόντα.")
                    
                    # Εμφάνιση πίνακα
                    st.dataframe(df, use_container_width=True)
                    
                    # Εξαγωγή σε Excel
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)
                    
                    st.download_button("📥 Κατέβασμα Excel", output.getvalue(), "extracted_tender_data.xlsx")
                    
            except Exception as e:
                st.error(f"Κάτι πήγε στραβά κατά την επικοινωνία ή την ανάλυση: {e}")

else:
    if not api_key:
        st.info("ℹ️ Παρακαλώ εισάγετε το API Key σας για να ξεκινήσετε.")
    elif not uploaded_file:
        st.info("ℹ️ Παρακαλώ ανεβάστε ένα PDF αρχείο.")
