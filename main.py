import os
import io
import gspread
import re
from google.auth import default
from flask import Flask
from google.cloud import documentai_v1 as documentai
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

app = Flask(__name__)

# CONFIGURAZIONE
PROJECT_ID = "767049280707"
LOCATION = "eu" 
PROCESSOR_ID = "2d7b989319d3eb7d"
FOLDER_ID = "15bx638Hoh87lZfMBlRBE4bnrcIKCswmN"
SHEET_ID = "1GUAQwmmjqi40Ni9x5m9pjEbCXfGf1HAslnhJPgOoWD4"

def extract_data_from_text(text):
    """Logica per estrarre data e importi specifici dal testo OCR"""
    # Estrazione Data
    data_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
    date_val = data_match.group(1) if data_match else "Data non trovata"
    
    # Estrazione Importo (Netto a pagare, Totale, ecc.)
    # Usiamo IGNORECASE (senza underscore) per evitare errori di attributo
    amount_match = re.search(r'(?:NET A PAYER|TOTAL|NET PAYE)\s*[:]*\s*([\d\s\.,]+)', text, re.IGNORECASE)
    
    if amount_match:
        # Pulizia dell'importo: togliamo spazi, cambiamo virgola in punto
        raw_amount = amount_match.group(1).strip()
        amount_val = raw_amount.replace(' ', '').replace(',', '.')
    else:
        amount_val = "0.00"
    
    return date_val, amount_val

@app.route("/", methods=["GET", "POST"])
def run_ingestion():
    try:
        print("DEBUG: Avvio procedura di ingestione...")
        creds, _ = default()
        
        # Inizializzazione Google Sheets
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        log_sheet = sh.worksheet("Log_Compensation")
        
        # Inizializzazione Drive
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Configurazione Document AI con Endpoint EU
        # endpoint = f"{LOCATION}-documentai.googleapis.com"
        # client_options = {"api_endpoint": endpoint}
        # docai_client = documentai.DocumentProcessorServiceClient(
        #     credentials=creds, 
        #     client_options=client_options
        # )
        docai_client = documentai.DocumentProcessorServiceClient(credentials=creds)
        
        resource_name = docai_client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)

        # 1. Recupera la lista file - LIMITATA A 1 PER TEST
        print(f"DEBUG: Cerco file nella cartella {FOLDER_ID}...")
        results = drive_service.files().list(
            q=f"'{FOLDER_ID}' in parents and mimeType='application/pdf'",
            fields="files(id, name)",
            pageSize=1  # Testiamo un solo file alla volta per evitare timeout
        ).execute()
        files = results.get('files', [])

        if not files:
            return "Nessun file trovato nella cartella!", 200

        processed_count = 0
        for file in files:
            print(f"DEBUG: Processando file: {file['name']}")
            
            # 2. Download del PDF con gestione memoria (Stream)
            request = drive_service.files().get_media(fileId=file['id'])
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            file_content = fh.getvalue()
            
            # 3. Invia a Document AI
            raw_document = documentai.RawDocument(content=file_content, mime_type="application/pdf")
            request = documentai.ProcessRequest(name=resource_name, raw_document=raw_document)
            
            print(f"DEBUG: Chiamata a Document AI per {file['name']}...")
            result = docai_client.process_document(request=request)
            
            # 4. Estrazione dati e scrittura su Excel
            date_val, amount_val = extract_data_from_text(result.document.text)
            
            print(f"DEBUG: Dati estratti: Data={date_val}, Importo={amount_val}")
            log_sheet.append_row([
                date_val, 
                amount_val, 
                "Renault", 
                "Fixed", 
                f"Auto-ingested: {file['name']}"
            ])
            processed_count += 1

        return f"🚀 Successo! Processato file: {files[0]['name']}. Controlla l'Excel!", 200

    except Exception as e:
        error_msg = f"Errore critico: {str(e)}"
        print(f"DEBUG ERROR: {error_msg}")
        return f"Errore durante l'ingestione: {error_msg}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
