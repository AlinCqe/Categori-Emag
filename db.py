import gspread
from google.oauth2.service_account import Credentials
import json
from dotenv import load_dotenv
import os

load_dotenv()

creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if not creds_json:
    raise RuntimeError("Missing GOOGLE_SERVICE_ACCOUNT_JSON env var")

creds_dict = json.loads(creds_json)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
client = gspread.authorize(creds)


sheet = client.open("categori").worksheet("Hoja 1")

def get_db_data():


    raw_data = sheet.get_all_records()

    data = []
    for i, row in enumerate(raw_data, start=2):  
        row_dict = dict(row)
        
        row_dict["_sheet_row"] = i
        data.append(row_dict)

    return data

def update_cell(row: int, column: int, text:str):

    sheet.update_cell(row, column, text)


