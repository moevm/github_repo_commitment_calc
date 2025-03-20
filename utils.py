import csv

TITLE_LEN = 80
MIN_SIDE_PADDING = 4
SIDE_WHITE_SPACES = 1

class logger:
    @staticmethod
    def log_title(title: str, title_len: int = TITLE_LEN):
        if len(title) + MIN_SIDE_PADDING * 2 + SIDE_WHITE_SPACES * 2 > title_len:
            need_sz = title_len - MIN_SIDE_PADDING * 2 - SIDE_WHITE_SPACES * 2

            title = title[:need_sz]

        padding = title_len - (len(title) + SIDE_WHITE_SPACES * 2)

        right_padding = (padding + 1) // 2
        left_padding  = padding // 2

        print(f"{left_padding * '='}{SIDE_WHITE_SPACES * ' '}{title}{SIDE_WHITE_SPACES * ' '}{right_padding * '='}")

    @staticmethod
    def log_to_csv(csv_name: str, field_names: tuple[str], row: dict | None = None):
        if isinstance(row, dict):
            file = open(csv_name, 'a', newline='')
            writer = csv.DictWriter(file, fieldnames=field_names)
        elif row == None:
            file = open(csv_name, 'w', newline='')
            writer = csv.writer(file)
            row = field_names
        else:
            raise TypeError(f"row has type {type(row)} but must be [ dict | None ]")
        
        writer.writerow(row)

        file.close()

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