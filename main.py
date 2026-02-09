import os
import gspread
from google.auth import default
from flask import Flask

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    sheet_id = "1GUAQwmmjqi40Ni9x5m9pjEbCXfGf1HAslnhJPgOoWD4"
    try:
        creds, _ = default()
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        sheet = sh.worksheet("Log_Compensation")
        
        sheet.append_row(["09/02/2026", "1.00", "RESET_OK", "System", "Ripartiti da zero con successo!"])
        return "Reset completato! Riga scritta.", 200
    except Exception as e:
        return f"Errore: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
