import os

import gspread
import pandas as pd
import unidecode
from dotenv import load_dotenv

load_dotenv()
sheet_id = os.getenv("SHEET_ID")


def _get_path(spreadsheet, worksheet):
    path = os.path.join("data", unidecode.unidecode(spreadsheet.title).replace(" ", "_").lower())
    os.makedirs(path, exist_ok=True)
    path = os.path.join(path, unidecode.unidecode(f"{worksheet.title}.csv").replace(" ", "_").lower())
    return path


def read_results():
    if not sheet_id:
        raise ValueError("SHEET_ID environment variable not set.")
    gc = gspread.service_account(filename='credentials.json')
    spreadsheet = gc.open_by_key(sheet_id)
    worksheets = spreadsheet.worksheets()

    for worksheet in worksheets:
        headers_row = worksheet.range(1, 1, 1, worksheet.col_count)
        column_names = [col.value for col in headers_row if col.value]
        data = worksheet.range(2, 1, worksheet.row_count, len(column_names))
        data_resized = []
        current_row = []
        for item in data:
            current_row.append(item.value)
            if item.col == len(column_names):
                data_resized.append(current_row)
                current_row = []
        df = pd.DataFrame(data_resized, columns=column_names)
        df.to_csv(_get_path(spreadsheet, worksheet), index=False)

