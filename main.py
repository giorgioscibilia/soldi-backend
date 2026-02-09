import os
import gspread
from google.auth import default
from flask import Flask
from google.cloud import documentai_v1 as documentai
from googleapiclient.discovery import build

app = Flask(__name__)

# CONFIGURAZIONE - CONTROLLA QUESTI 3 VALORI
PROJECT_ID = "soldi-backend-486215"
LOCATION = "eu"  # <--- SE HAI CREATO IL PROCESSORE IN US, CAMBIA IN 'us'
PROCESSOR_ID = "2d7b989319d3eb7d"
FOLDER_ID = "15bx638Hoh87lZfMBlRBE4bnrcIKCswmN"
SHEET_ID = "1GUAQwmmjqi40Ni9x5m9pjEbCXfGf1HAslnhJPgOoWD4"

@app.route("/", methods=["GET", "POST"])
def index():
    status = []
    try:
        creds, _ = default()
        
        # 1. TEST SHEETS
        try:
            gc = gspread.authorize(creds)
            sh = gc.open_by_key(SHEET_ID)
            status.append("Google Sheets OK")
        except Exception as e:
            return f"Errore Sheets: {str(e)} (Verifica email service account nel foglio)", 500

        # 2. TEST DRIVE
        try:
            drive_service = build('drive', 'v3', credentials=creds)
            results = drive_service.files().list(
                q=f"'{FOLDER_ID}' in parents", fields="files(id, name)").execute()
            status.append(f"Drive OK ({len(results.get('files', []))} file trovati)")
        except Exception as e:
            return f"Errore Drive: {str(e)} (Verifica permessi cartella)", 500

        # 3. TEST DOCUMENT AI
        try:
            docai_client = documentai.DocumentProcessorServiceClient(credentials=creds)
            resource_name = docai_client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)
            status.append("Document AI OK")
        except Exception as e:
            return f"Errore Document AI: {str(e)}", 500

        return f"SISTEMA PRONTO: {' | '.join(status)}", 200

    except Exception as e:
        return f"Errore Generico: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
