import csv
from datetime import datetime

import pytz

from constants import MIN_SIDE_PADDING, SIDE_WHITE_SPACES, TIMEZONE, TITLE_LEN
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class logger:
    # TODO: отключение вывода в stdout
    @staticmethod
    def log_title(title: str, title_len: int = TITLE_LEN):
        final_len = max(
            title_len, len(title) + MIN_SIDE_PADDING * 2 + SIDE_WHITE_SPACES * 2
        )

        formatted = f"{SIDE_WHITE_SPACES * ' ' + title + ' ' * SIDE_WHITE_SPACES:=^{final_len}}"
        logging.info(formatted)

    @staticmethod
    def log_to_csv(csv_name: str, field_names: tuple[str], row: dict | None = None):
        field_names = list(map(lambda x: x.replace('_', ' '), field_names))
        if row is not None:
            row = {k.replace('_', ' '): v for k, v in row.items()}
        if isinstance(row, dict):
            with open(csv_name, 'a', encoding='utf-8', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=field_names)
                writer.writerow(row)
        elif row is None:
            with open(csv_name, 'w', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(field_names)
        else:
            raise TypeError(f"row has type {type(row)} but must be [ dict | None ]")

    @staticmethod
    def log_to_stdout(info: dict):
        logging.info(f"{info}")

    @staticmethod
    def log_sep():
        logging.info("-" * TITLE_LEN)

    @staticmethod
    def log_error(error: str):
        logging.error(error)

    @staticmethod
    def log_warning(warning: str):
        logging.warning(warning)


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
