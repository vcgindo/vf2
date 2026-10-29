"""Bulk transport for already validated initialization-owned model rows.

The caller retains the atomic transaction, owner markers and final independent
readback. COPY runs the installed guards; failures never retry through INSERT.
"""
from itertools import islice

from django.db import connection

from mta.application.stage_observation import stage
from mta.runtime.relational_state import copy_rows, INGESTION_COPY_MIN_ROWS


def create_rows(model, records, *, count):
    if not count:
        return
    fields = [field for field in model._meta.concrete_fields
              if not field.generated and not (field.primary_key and field.auto_created)]
    # pre_save on clock-managed fields needs an actual model instance. The
    # current owner rosters have none; retain ORM behavior for any future caller.
    use_copy = (connection.vendor == 'postgresql' and count >= INGESTION_COPY_MIN_ROWS
                and not any(getattr(field, 'auto_now', False) or
                            getattr(field, 'auto_now_add', False) for field in fields))
    with stage('initialization_master_write', model=model.__name__, rows=count,
               transport='copy' if use_copy else 'orm'):
        if use_copy:
            allowed = {field.attname for field in fields}

            def prepared():
                for record in records:
                    if set(record) - allowed:
                        raise ValueError('Unknown initialization model fields: ' + model.__name__)
                    yield tuple(field.get_db_prep_save(
                        record[field.attname] if field.attname in record else field.get_default(),
                        connection=connection) for field in fields)

            copy_rows(connection.ops.quote_name(model._meta.db_table),
                      [field.column for field in fields], prepared())
        else:
            iterator = (model(**record) for record in records)
            while batch := list(islice(iterator, 500)):
                model.objects.bulk_create(batch, batch_size=500)
