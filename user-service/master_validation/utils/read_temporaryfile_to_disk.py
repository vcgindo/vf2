import tempfile


import pandas as pd
from django.core.files.uploadedfile import UploadedFile

ALLOWED_EXTENSIONS = ('.xls', '.xlsx', '.csv')

def read_uploaded_master_file(uploaded_file: UploadedFile):

    if not uploaded_file.name.lower().endswith(ALLOWED_EXTENSIONS):
        raise ValueError("Invalid file type. Only .xls and .xlsx are allowed.")

    with tempfile.TemporaryFile(suffix='.xlsx') as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
    
        tmp.seek(0)
        master_df = pd.read_excel(tmp, engine='openpyxl', dtype=str)
        master_df.replace(
            to_replace=r'^\s*(null|nan|na|n/a)\s*$',
            value=None,
            regex=True,
            inplace=True
        )
        return master_df