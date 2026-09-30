# models.py
from django.db import models

class ExcelUpload(models.Model):
    class Meta:
       db_table = 'EXCEL_UPLOAD' 
    process_id = models.CharField(max_length=255, unique=True)
    progress = models.IntegerField(default=0)
    total_rows = models.IntegerField(default=0)
    
    def get_progress(self):
        return self.progress
    def get_total_rows(self):
        return self.total_rows
