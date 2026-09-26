import csv
import atexit
from datetime import datetime
from functools import wraps
import traceback
import re
from time import monotonic

import pytz

from src.constants import MIN_SIDE_PADDING, SIDE_WHITE_SPACES, TIMEZONE, TITLE_LEN
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class logger:
    _csv_files = {}
    _csv_progress = {}
    _progress_log = logging.getLogger("export.progress")
    _progress_log.setLevel(logging.INFO)

    @staticmethod
    def close_csv_files():
        try:
            for file, _, _ in logger._csv_files.values():
                file.close()
            for csv_name, (count, _) in logger._csv_progress.items():
                logger._progress_log.info("CSV %s: total %d rows written", csv_name, count)
        finally:
            logger._csv_files.clear()
            logger._csv_progress.clear()

    @staticmethod
    def log_title(title: str, title_len: int = TITLE_LEN):
        final_len = max(
            title_len, len(title) + MIN_SIDE_PADDING * 2 + SIDE_WHITE_SPACES * 2
        )

        formatted = f"{SIDE_WHITE_SPACES * ' ' + title + ' ' * SIDE_WHITE_SPACES:=^{final_len}}"
        logging.debug(formatted)

    @staticmethod
    def log_to_csv(csv_name: str, field_names: tuple[str], row: dict | None = None):
        if row is not None and not isinstance(row, dict):
            raise TypeError(f"row has type {type(row)} but must be [ dict | None ]")
        field_names = tuple(x.replace('_', ' ') for x in field_names)
        cached = logger._csv_files.get(csv_name)
        if row is None or cached is None or cached[2] != field_names:
            if cached is not None:
                cached[0].close()
                del logger._csv_files[csv_name]
            file = open(csv_name, 'w' if row is None else 'a', encoding='utf-8', newline='')
            writer = csv.DictWriter(file, fieldnames=field_names)
            logger._csv_files[csv_name] = file, writer, field_names
        else:
            file, writer, _ = cached
        if row is None:
            writer.writeheader()
            logger._csv_progress[csv_name] = (0, monotonic())
        else:
            writer.writerow({k.replace('_', ' '): v for k, v in row.items()})
        file.flush()
        if row is not None:
            now = monotonic()
            count, last_progress = logger._csv_progress.get(csv_name, (0, now))
            count += 1
            if now - last_progress >= 5:
                logger._progress_log.info("CSV %s: %d rows written", csv_name, count)
                last_progress = now
            logger._csv_progress[csv_name] = (count, last_progress)

    @staticmethod
    def log_to_stdout(info: dict):
        logging.debug("%s", info)

    @staticmethod
    def log_sep():
        logging.debug("-" * TITLE_LEN)

    @staticmethod
    def log_error(error: str):
        logging.error(error)

    @staticmethod
    def log_warning(warning: str):
        logging.warning(warning)


atexit.register(logger.close_csv_files)


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


def log_exceptions(default_return=None, message="", print_stacktrace=True):
    """
    Декоратор обработки ошибок для методов класса.
    Логирует ошибки и возвращает default_return при исключении.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                class_name = args[0].__class__.__name__ if args else ""
                logging.error(f"{class_name=}")
                logging.error(f"{message} {func.__name__}: {e}")
                if print_stacktrace:
                    logging.error(traceback.format_exc())
                return default_return
        return wrapper
    return decorator


def validate_and_normalize_cell(cell: str):
    """
    Проверка на соответствие строки формату ячейки Google Sheets:
        - Идут буквы, потому идут цифры
        - Буквы латинские
        - Буквы в верхнем регистре (нижний регистр не вызывает ошибку -- принудительно переводится в верхний в return)
    """
    if not re.match(r'^[A-Za-z]+\d+$', cell):
        raise ValueError(f"Invalid cell format: '{cell}'. Must be letters followed by digits (e.g., 'A1', 'B3').")

    letters = re.findall(r'[A-Za-z]+', cell)[0]
    numbers = re.findall(r'\d+', cell)[0]

    if not re.match(r'^[A-Za-z]+$', letters):
        raise ValueError(f"Cell contains non-latin characters: '{letters}'. Only Latin letters allowed.")

    return letters.upper() + numbers
