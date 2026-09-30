from apps.settings import DEFAULT_URL_CSV
import pandas as pd
import os

TYPE_FILE_TO_ENGINE = {
    'csv': None,
    'xlsx': None,
    'xlsb': 'pyxlsb'
}


class File:
    def __init__(self, file=None):
        self.path = DEFAULT_URL_CSV
        self.file = file
        self.get_type_file()

    def get_dataframe(self):
        try:
            if self.get_type_file() == 'csv':
                return pd.read_csv(
                    '{}'.format(self.get_full_path()),
                    low_memory=False,
                )
            return pd.read_excel(
                '{}'.format(self.get_full_path()))

        except Exception as e:
            raise ('Can not find dataframe {}'.format(e))

    def get_type_file(self):
        file_name, file_extension = os.path.splitext(self.get_full_path())
        return file_extension.replace('.', '')

    def get_full_path(self):
        path = '{}/{}'.format(self.path, self.file)
        return path
