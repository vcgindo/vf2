from typing import List, Type
from django.db import models


def get_column_name(column) -> str:
    return column.field.column


def get_columns_str_of_model(model: models.Model or Type[models.Model]) -> List[str]:
    return [field.name for field in model._meta.get_fields()]

