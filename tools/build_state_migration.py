"""Mechanical migration writer for the pinned relational column catalogue."""
import os
from pathlib import Path

os.environ.setdefault('VF_SECRET_KEY','migration-generation-not-serving')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.db import migrations
from django.db.migrations.writer import MigrationWriter
from mta.runtime.relational_state import schema_statements, CATALOG, table_sql

ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'mta/runtime/migrations/0006_relational_state_rows.py'
if target.exists():raise SystemExit('Existing migration identities are immutable')
migration=migrations.Migration('0006_relational_state_rows','fresh_mta')
migration.dependencies=[('fresh_mta','0005_validation_evidence_boundary')]
migration.operations=[migrations.RunSQL(schema_statements(),
    ['DROP TABLE mta_state.report_export_cell']+
    ['DROP TABLE '+table_sql(key) for key in sorted(CATALOG['tables'],reverse=True)]+['DROP SCHEMA mta_state'])]
target.write_text(MigrationWriter(migration).as_string(),encoding='utf-8',newline='\n')
print('Generated '+str(target)+' with '+str(len(CATALOG['tables']))+' explicit typed state tables and report cells')
