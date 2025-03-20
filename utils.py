import csv

TITLE_LEN = 80
MIN_SIDE_PADDING = 4
SIDE_WHITE_SPACES = 1


class logger:
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
    def log_error(error: str):
        # или использовать logging, как в interface_wrapper
        pass

    @staticmethod
    def log_warning(warning: str):
        pass
