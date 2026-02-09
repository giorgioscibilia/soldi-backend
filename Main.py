import functions_framework
import gspread
from google.auth import default

@functions_framework.http
def process_payslips(request):
    # ID del tuo nuovo file di test
    sheet_id = "1GUAQwmmjqi40Ni9x5m9pjEbCXfGf1HAslnhJPgOoWD4"
    
    try:
        # Usa le credenziali del Service Account di GCP
        creds, _ = default()
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        sheet = sh.worksheet("Log_Compensation")
        
        sheet.append_row(["09/02/2026", "1.00", "GITHUB_TEST", "System", "Deploy da GitHub OK"])
        return "Connessione GitHub-Sheets riuscita!", 200
    except Exception as e:
        return f"Errore: {str(e)}", 500
