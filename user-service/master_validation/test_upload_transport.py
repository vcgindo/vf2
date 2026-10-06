"""Transport compatibility checks, with no database or master mutation."""
from io import BytesIO
from unittest.mock import patch

import pandas as pd
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from master_validation.models.excel_upload import ExcelUpload
from master_validation.utils.read_temporaryfile_to_disk import read_uploaded_master_file
from master_validation.views.get_upload_progress import GetUploadProgressView


class UploadTransportTests(SimpleTestCase):
    def test_csv_and_xlsx_preserve_same_text_and_empty_cells(self):
        expected=pd.DataFrame({'SKU Code':['0001','0002'],
            'Description':['quoted, value','second'], 'Weight':['1.250','invalid']})
        workbook=BytesIO()
        expected.to_excel(workbook,index=False,engine='openpyxl')
        files=[('owned.csv',expected.to_csv(index=False).encode()),('owned.xlsx',workbook.getvalue())]
        for name,data in files:
            with self.subTest(name=name):
                actual=read_uploaded_master_file(SimpleUploadedFile(name,data))
                pd.testing.assert_frame_equal(actual,expected)

    def test_progress_reads_each_poll_and_preserves_missing_response(self):
        user=type('Actor',(),{'is_authenticated':True})()
        view=GetUploadProgressView.as_view()
        def request():
            req=APIRequestFactory().get('/progress/owned')
            force_authenticate(req,user=user)
            return view(req,processId='owned')
        with patch.object(ExcelUpload.objects,'only') as query:
            query.return_value.get.side_effect=[
                ExcelUpload(process_id='owned',progress=1,total_rows=10),
                ExcelUpload(process_id='owned',progress=7,total_rows=10),
                ExcelUpload.DoesNotExist()]
            first,second,missing=request(),request(),request()
            self.assertEqual(first.data,{'progress':1,'totalRows':10})
            self.assertEqual(second.data,{'progress':7,'totalRows':10})
            self.assertEqual(missing.status_code,404)
            self.assertEqual(missing.data,{'error':'Process Not Found'})
