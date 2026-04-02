import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import json
import os
from io import BytesIO

# --- Ρυθμίσεις ---
st.set_page_config(page_title="AI PDF Extractor", layout="wide")
st.title("🤖 AI-Powered PDF Extractor (Gemini)")
st.write("Αυτό το εργαλείο χρησιμοποιεί Τεχνητή Νοημοσύνη για να διαβάσει τους πίνακες, ανεξάρτητα από το πόσο περίπλοκοι είναι.")

# 1. Πεδίο για το API Key
api_key = st.text_input("1. Εισάγετε το Gemini API Key σας", type="password")

# 2. Πεδίο για το PDF
uploaded_file = st.file_uploader("2. Ανεβάστε το PDF της προκήρυξης", type="pdf")

if api_key and uploaded_file:
    # Δημιουργία του client με τη νέα βιβλιοθήκη
    client = genai.Client(api_key=api_key)
    
    with st.spinner("🤖 Το AI διαβάζει το PDF... Αυτό μπορεί να πάρει 10-30 δευτερόλεπτα για μεγάλα αρχεία."):
        
        # Αποθηκεύουμε προσωρινά το αρχείο για να το στείλουμε στο API
        temp_filename = "temp_uploaded.pdf"
        with open(temp_filename, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        try:
            # Ανεβάζουμε το αρχείο στην Google με το νέο SDK
            ai_file = client.files.upload(file=temp_filename)
            
            prompt = """
            Ανάλυσε αυτό το έγγραφο και εξήγαγε ΟΛΑ τα προϊόντα από όλους τους πίνακες που υπάρχουν.
            Θέλω να μου επιστρέψεις μια λίστα (array) από αντικείμενα (objects).
            Κάθε αντικείμενο στη λίστα πρέπει να αντιπροσωπεύει μια γραμμή προϊόντος και να έχει τα εξής keys:
            - "Α/Α"
            - "Όνομα Υλικού"
            - "Ποσότητα"
            - "Συνολικό Κόστος"
            Αν υπάρχουν επιπλέον στήλες (π.χ. CPV, Μονάδα Μέτρησης, Τιμή Μονάδος), πρόσθεσέ τις ως έξτρα keys.
            Σιγουρέψου ότι δεν θα χάσεις κανένα προϊόν από καμία σελίδα.
            """
            
            # Κλήση του μοντέλου με τις νέες παραμέτρους
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=[ai_file, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            # Μετατροπή του JSON σε Πίνακα (DataFrame)
            data = json.loads(response.text)
            df = pd.DataFrame(data)
            
            st.success(f"Επιτυχία! Το AI εντόπισε {len(df)} προϊόντα.")
            
            # Εμφάνιση του πίνακα
            st.dataframe(df, use_container_width=True)
            
            # Δημιουργία αρχείου Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            # Κουμπί για κατέβασμα
            st.download_button("📥 Κατέβασμα Excel", output.getvalue(), "ai_extracted_data.xlsx")
            
        except Exception as e:
            st.error(f"Κάτι πήγε στραβά: {e}")
            
        # Διαγραφή του προσωρινού αρχείου
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

else:
    if not api_key:
        st.info("ℹ️ Παρακαλώ εισάγετε το API Key σας για να ξεκινήσετε.")
    elif not uploaded_file:
        st.info("ℹ️ Παρακαλώ ανεβάστε ένα PDF αρχείο.")
