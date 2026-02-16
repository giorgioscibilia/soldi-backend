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
    """Logica specifica per buste paga Renault/Ampere"""
    
    # 1. Estrazione DATA DI PAIEMENTO (più precisa dell'anzianità)
    # Cerca la data che segue "DATE DE PAIEMENT"
    date_match = re.search(r'DATE DE PAIEMENT:\s*(\d{2}\.\d{2}\.\d{4})', text)
    if date_match:
        date_val = date_match.group(1).replace('.', '/') # Trasforma 31.12.2025 in 31/12/2025
    else:
        # Backup: cerca comunque una data se la prima fallisce
        data_any = re.search(r'(\d{2}/\d{2}/\d{4})', text)
        date_val = data_any.group(1) if data_any else "Non trovata"

    # 2. Estrazione IMPORTO (NET A PAYER)
    # Cerchiamo la cifra che appare DOPO "NET A PAYER" (gestendo i \n e gli spazi)
    # Questa regex cattura numeri come 4.334,06 o 4334,06
    amount_match = re.search(r'NET A PAYER\s*[\n]*\s*([\d\s\.,]+)', text)
    
    if amount_match:
        raw_amount = amount_match.group(1).strip()
        # Pulizia: togliamo punti delle migliaia e cambiamo virgola in punto decimale
        # Es: 4.334,06 -> 4334.06
        amount_val = raw_amount.replace('.', '').replace(',', '.')
    else:
        amount_val = "0.00"
    
    return date_val, amount_val

@app.route("/", methods=["GET", "POST"])
def run_ingestion():
    try:
        creds, _ = default()
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        log_sheet = sh.worksheet("Log_Compensation")
        
        # Leggiamo i file già processati per evitare duplicati
        existing_files = log_sheet.col_values(5) # Colonna E (Note) dove scriviamo il nome file

        drive_service = build('drive', 'v3', credentials=creds)
        
        endpoint = f"{LOCATION}-documentai.googleapis.com"
        client_options = {"api_endpoint": endpoint}
        docai_client = documentai.DocumentProcessorServiceClient(credentials=creds, client_options=client_options)
        resource_name = docai_client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)

        # Recupera la lista di tutti i PDF (aumentiamo a 10 per volta per sicurezza)
        results = drive_service.files().list(
            q=f"'{FOLDER_ID}' in parents and mimeType='application/pdf'",
            fields="files(id, name)",
            pageSize=10 
        ).execute()
        files = results.get('files', [])

        processed_count = 0
        for file in files:
            # SALTA SE GIÀ PROCESSATO
            if any(file['name'] in s for s in existing_files):
                print(f"DEBUG: Salto {file['name']}, già presente.")
                continue

            print(f"DEBUG: Inizio OCR su {file['name']}...")
            
            # Download
            request = drive_service.files().get_media(fileId=file['id'])
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            # Document AI
            raw_document = documentai.RawDocument(content=fh.getvalue(), mime_type="application/pdf")
            request = documentai.ProcessRequest(name=resource_name, raw_document=raw_document)
            result = docai_client.process_document(request=request)
            
            # Estrazione
            date_val, amount_val = extract_data_from_text(result.document.text)
            
            # Scrittura
            log_sheet.append_row([date_val, amount_val, "Renault", "Fixed", f"Auto-ingested: {file['name']}"])
            processed_count += 1
            
            # Liberiamo memoria
            del result

        return f"🚀 Processati {processed_count} nuovi file. Controlla l'Excel!", 200

    except Exception as e:
        return f"Errore: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
