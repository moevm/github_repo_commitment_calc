import argparse
import os
import json
from pathlib import Path
import pandas as pd
import pygsheets


def parse_arguments():
    parser = argparse.ArgumentParser(description="Скрипт для загрузки данных из JSON файлов в Google Таблицу")
    parser.add_argument('--data-dir', type=str, required=True, help="Директория с репозиториями")
    parser.add_argument('--table-id', type=str, required=True, help="ID таблицы Google Sheets")
    parser.add_argument('--oauth-file', type=str, required=True, help="Путь к файлу client_secret.json")
    return parser.parse_args()


def authorize_google_sheets(oauth_file):
    return pygsheets.authorize(service_file=oauth_file)


def open_spreadsheet(gc, table_id):
    return gc.open_by_key(table_id)


def read_and_normalize_json_file(json_path):
    with open(json_path, 'r') as f:
        data = [json.loads(line) for line in f]
    return pd.json_normalize(data)


def update_sheet(spreadsheet, worksheet_name, dataframe):
    try:
        spreadsheet.worksheets('title', worksheet_name)
    except:
        spreadsheet.add_worksheet(worksheet_name)

    wks = spreadsheet.worksheet_by_title(worksheet_name)
    wks.clear()
    wks.set_dataframe(dataframe, start=(1, 1), copy_index=False, copy_head=True, fit=True)


def process_repositories(data_dir, spreadsheet):
    for repo_dir in os.listdir(data_dir):
        repo_path = Path(data_dir) / repo_dir
        json_file_path = repo_path / 'commits.json'
        if json_file_path.exists():
            print(f"Parse commits from {repo_dir}")
            df = read_and_normalize_json_file(json_file_path)
            df = df[sorted(df.columns.to_list())]
            worksheet_name = repo_dir
            update_sheet(spreadsheet, worksheet_name, df)


def main():
    args = parse_arguments()
    gc = authorize_google_sheets(args.oauth_file)
    spreadsheet = open_spreadsheet(gc, args.table_id)
    process_repositories(args.data_dir, spreadsheet)
    print("Finished!")


if __name__ == "__main__":
    main()