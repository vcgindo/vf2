from asyncio.log import logger
from django.test import TestCase
from master_validation.services import DatabaseSyncServices
from master_validation.models.prefinal_models import *
from master_validation.models.final_models import *
from io import StringIO
from api.utils import RSAUtil

from django.db import transaction, connection
from sqlalchemy import create_engine, MetaData, Table, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import psycopg2
import os
DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PORT = os.environ.get('DB_PORT')
DB_PASSWORD = RSAUtil.decrypt_rsa(os.environ.get('DB_PASSWORD'))


import pandas as pd
# Create your tests here.


class DatabaseSyncServicesTestCase(TestCase):
    def setUp(self):
        self.service = DatabaseSyncServices()
        self.engine = self.make_conn()
        Session = sessionmaker(bind=self.engine)
        self.session = Session()


    def test_sync_prefinal_table_to_final_table(self):
        test_master_data = pd.read_csv('D:\DevOps\\vflow-retail-backend\\vector\master_validation\\test_master_data\\ContactMaster.csv')
        self.insert_data(test_master_data,'PRE_FINAL_CONTACT_DETAILS_MASTER', is_truncate=False)
        self.service.sync_prefinal_table_to_final_table(PreFinalContactDetailMasterModel,FinalContactDetail)
        source_total_rows = len(PreFinalContactDetailMasterModel.objects.all())
        destination_total_rows = len(FinalContactDetail.objects.all())
        if  source_total_rows != 0 and (source_total_rows == destination_total_rows):
            logger.info('Test Passed')
        else:
            logger.info('Test Failed')
    def make_conn(self):
        return create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}')
    def insert_data(self,df:pd.DataFrame, table_name, is_truncate = True):
        # metadata = MetaData(bind=self.engine)
        # table =Table(table_name, metadata, autoload=True)

        # with self.session.begin():
        #     if is_truncate:
        #         self.session.execute(table.delete())
        #     buffer = StringIO()
        #     df['id'] = range(1, len(df) + 1) 
        #     df = df[['id'] + [col for col in df.columns if col != 'id']]
        #     df.to_csv(buffer, sep='\t', header=False, index=False)
        #     buffer.seek(0)

        #     try:
        #         conn = self.engine.raw_connection()
        #         cursor = conn.cursor()
        #         cursor.copy_from(buffer, f"{table_name}", sep='\t')
        #         conn.commit()
        #     except Exception as e:
        #         print(f"An error occured {e}")
        #         self.session.rollback()
        #         return

        for index, row in df.iterrows():
            obj = PreFinalContactDetailMasterModel.objects.create(
                wh_code = row['wh_code'],
                contact_name = row['contact_name'],
                contact_phone = row['contact_phone'],
                contact_email = row['contact_email']
            )
            obj.save()
    