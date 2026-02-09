import os
import gspread
from google.auth import default
from flask import Flask

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    # ID del tuo file di test
    sheet_id = "1GUAQwmmjqi40Ni9x5m9pjEbCXfGf1HAslnhJPgOoWD4"
    
    try:
        # Recupera credenziali dal Service Account di Cloud Run
        creds, _ = default()
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        
        # Prova a scrivere nel tab Log_Compensation
        sheet = sh.worksheet("Log_Compensation")
        sheet.append_row(["09/02/2026", "1.00", "FLASK_RUN_OK", "System", "Cloud Run is connected!"])
        
        return "Connessione riuscita! Riga scritta nel foglio.", 200
    except Exception as e:
        return f"Errore durante l'esecuzione: {str(e)}", 500

if __name__ == "__main__":
    # Cloud Run imposta automaticamente la variabile d'ambiente PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
