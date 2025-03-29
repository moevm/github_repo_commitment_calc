import csv
from datetime import datetime
import pytz

TITLE_LEN = 80
MIN_SIDE_PADDING = 4
SIDE_WHITE_SPACES = 1

class logger:
    #TODO: отключение вывода в stdout
    @staticmethod
    def log_title(title: str, title_len: int = TITLE_LEN):
        final_len = max(
            title_len, len(title) + MIN_SIDE_PADDING * 2 + SIDE_WHITE_SPACES * 2
        )

        print(
            f"{SIDE_WHITE_SPACES * ' ' + title + ' ' * SIDE_WHITE_SPACES:=^{final_len}}"
        )

    @staticmethod
    def log_to_csv(csv_name: str, field_names: tuple[str], row: dict | None = None):
        if isinstance(row, dict):
            with open(csv_name, 'a', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=field_names)
                writer.writerow(row)
        elif row is None:
            with open(csv_name, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(field_names)
        else:
            raise TypeError(f"row has type {type(row)} but must be [ dict | None ]")

    @staticmethod
    def log_to_stdout(info: dict):
        print(info)

    @staticmethod
    def log_sep():
        print("-" * TITLE_LEN)

    @staticmethod
    def log_error(error: str):
        # или использовать logging, как в interface_wrapper
        pass

    @staticmethod
    def log_warning(warning: str):
        pass

TIMEZONE = 'Europe/Moscow'

def parse_time(datetime_str) -> datetime:
    start = (
        datetime_str[0].split('/') + datetime_str[1].split(':')
        if len(datetime_str) == 2
        else datetime_str[0].split('/') + ['00', '00', '00']
    )
    start = [int(i) for i in start]
    start_datetime = datetime(
        year=start[0],
        month=start[1],
        day=start[2],
        hour=start[3],
        minute=start[4],
        second=start[5],
    )
    return start_datetime.astimezone(pytz.timezone(TIMEZONE))
