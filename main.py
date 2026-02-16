import os
import gspread
import re
from google.auth import default
from flask import Flask
from google.cloud import documentai_v1 as documentai
from googleapiclient.discovery import build

app = Flask(__name__)

# CONFIGURAZIONE
PROJECT_ID = "soldi-backend-486215"
LOCATION = "eu" 
PROCESSOR_ID = "2d7b989319d3eb7d"
FOLDER_ID = "15bx638Hoh87lZfMBlRBE4bnrcIKCswmN"
SHEET_ID = "1GUAQwmmjqi40Ni9x5m9pjEbCXfGf1HAslnhJPgOoWD4"

def extract_data_from_text(text):
    """Logica per estrarre data e importi specifici dal testo OCR"""
    data_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
    date_val = data_match.group(1) if data_match else "Data non trovata"
    
    # Esempio: Cerchiamo l'importo netto o il totale (adattabile alle tue keyword)
    # Cerchiamo una cifra decimale dopo una keyword tipica
    amount_match = re.search(r'(?:NET A PAYER|TOTAL|NET PAYE)\s*[:]*\s*([\d\s\.,]+)', text, re.IGNORECASE)
    amount_val = amount_match.group(1).replace(' ', '').replace(',', '.') if amount_match else "0.00"
    
    return date_val, amount_val

@app.route("/", methods=["GET", "POST"])
def run_ingestion():
    try:
        creds, _ = default()
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        log_sheet = sh.worksheet("Log_Compensation")
        
        drive_service = build('drive', 'v3', credentials=creds)

        # Forza l'uso del server Europeo con l'endpoint corretto
        endpoint = f"{LOCATION}-documentai.googleapis.com"
        client_options = {"api_endpoint": endpoint}
        
        docai_client = documentai.DocumentProcessorServiceClient(
            credentials=creds, 
            client_options=client_options # Assicurati che il nome sia client_options
        )
        
        resource_name = docai_client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)

        # 1. Recupera lista file
        results = drive_service.files().list(
            q=f"'{FOLDER_ID}' in parents and mimeType='application/pdf'",
            fields="files(id, name)"
        ).execute()
        files = results.get('files', [])

        processed_count = 0
        for file in files:
            # PROVA SOLO IL PRIMO FILE PER TESTARE I PERMESSI
            print(f"Processando: {file['name']}")
            
            # 2. Leggi il contenuto del PDF
            file_content = drive_service.files().get_media(fileId=file['id']).execute()
            
            # 3. Invia a Document AI
            raw_document = documentai.RawDocument(content=file_content, mime_type="application/pdf")
            request = documentai.ProcessRequest(name=resource_name, raw_document=raw_document)
            result = docai_client.process_document(request=request)
            
            # 4. Estrai e Scrivi
            date_val, amount_val = extract_data_from_text(result.document.text)
            log_sheet.append_row([date_val, amount_val, "Renault", "Fixed", f"Auto-ingested: {file['name']}"])
            processed_count += 1
            
            # FERMATI AL PRIMO PER EVITARE IL TIMEOUT
            break 

        return f"🚀 Test singolo riuscito! File: {files[0]['name']}. Controlla l'Excel!", 200

    except Exception as e:
        return f"Errore durante l'ingestione: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
