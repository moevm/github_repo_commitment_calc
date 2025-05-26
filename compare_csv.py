import csv
import sys

def compare_csv_files(actual_path, expected_path):
    with open(actual_path, newline='', encoding='utf-8') as actual_file, \
         open(expected_path, newline='', encoding='utf-8') as expected_file:
        actual_reader = csv.DictReader(actual_file)
        expected_reader = csv.DictReader(expected_file)

        actual_rows = list(actual_reader)
        expected_rows = list(expected_reader)

        common_fields = set(actual_reader.fieldnames) & set(expected_reader.fieldnames)
        if not common_fields:
            print('Нет общих столбцов для сравнения!')
            sys.exit(1)

        def rows_to_set(rows):
            return set(tuple(row[field] for field in sorted(common_fields)) for row in rows)

        actual_set = rows_to_set(actual_rows)
        expected_set = rows_to_set(expected_rows)

        if actual_set != expected_set:
            print('Файлы отличаются по общим столбцам:')
            print('Только в output.csv:')
            for row in actual_set - expected_set:
                print(row)
            print('Только в reference.csv:')
            for row in expected_set - actual_set:
                print(row)
            sys.exit(1)
        else:
            print('Файлы совпадают по общим столбцам.')

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <actual_csv> <expected_csv>")
        sys.exit(1)
    compare_csv_files(sys.argv[1], sys.argv[2])

