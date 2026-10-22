"""Exact released guard-function transition, not another general DDL allowance."""
from importlib import import_module
from mta.serialization import digest

MIGRATION_NAME='0168_report_guard_owner_sets'
MIGRATION_SHA256='66c198d0d0273e2fe333b85f35bb2fdcef236a8b965dcac7177f36decf19347f'
PREVIOUS_RELEASE='7a544363876529927a7c7afecb05e6b16ab139ac3e91548443448742aa0a5f3a'
BEFORE_SCHEMA='ebc1ac032a171500383b8c12844b87ea6ac6942a36a330fac76cff11fae38b94'
BEFORE_GUARD='adb920a5925eefe2a4cb6e136ee0cd6e4248d2b155561717d9fdccb915cc2c93'


def migration_pins():
    return [[MIGRATION_NAME,MIGRATION_SHA256]]


def catalogue_delta():
    migration=import_module('mta.runtime.migrations.'+MIGRATION_NAME)
    result={}
    for name,old,new,definer,configuration in migration.FUNCTIONS:
        body=dict(name='mta.'+name+'()',owner='vectorflow_mta_owner',security_definer=definer,
            body=old,configuration=configuration,language='plpgsql',returns='trigger')
        result['functions:'+body['name']]=dict(before=body,after={**body,'body':new})
    return result


def approved_receipt(extension):
    return (extension.get('migration_pins')==migration_pins()
        and extension.get('catalogue_delta_digest')==digest(catalogue_delta())
        and extension.get('previous_release')==PREVIOUS_RELEASE
        and extension.get('before_schema_digest')==BEFORE_SCHEMA
        and extension.get('before_guard_digest')==BEFORE_GUARD)


def require_specification(spec):
    if (spec['migration_pins']!=migration_pins() or spec['catalogue_delta']!=catalogue_delta()
            or spec['previous_release']['manifest_sha256']!=PREVIOUS_RELEASE):
        raise ValueError('Only the exact released report guard migration/catalogue delta is supported')
