import pandas as pd
import pygsheets

INT_MASS = [{"one": 1, "two": 2, "what?": 3}]


def write_data_to_table(csv_path, google_token, table_id, sheet_id, start_cell="A1"):
    if google_token and sheet_id and table_id:
        gc = pygsheets.authorize(service_file=google_token)
        sh = gc.open_by_key(table_id)

    try:
        sh.worksheets('title', sheet_id)
    except Exception:
        sh.add_worksheet(sheet_id)

    wk_content = sh.worksheet_by_title(sheet_id)

    if csv_path:
        df = pd.read_csv(csv_path, delimiter=',', encoding='utf-8')
    else:
        df = pd.DataFrame(INT_MASS)

    # Очистка существующих данных
    wk_content.clear()

    # Запись новых данных
    wk_content.set_dataframe(df, start_cell, copy_head=True)
