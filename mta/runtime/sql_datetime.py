"""Canonical SQL datetime cells have no timezone or implicit local conversion."""
from datetime import datetime
from django.db import models


class SqlDateTimeField(models.DateTimeField):
    def db_type(self,connection):
        return 'timestamp without time zone' if connection.vendor=='postgresql' else super().db_type(connection)

    def get_prep_value(self,value):
        if isinstance(value,str):value=datetime.fromisoformat(value)
        if value is not None and (not isinstance(value,datetime) or value.tzinfo is not None):
            raise ValueError('Canonical SQL datetime requires a timezone-free datetime')
        return value
