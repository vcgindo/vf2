"""One exact ownership upgrade through the existing schema authority.

No arbitrary sixth DDL admission, new authority table or rewritten old receipt.
The portable delta is derived from the frozen migration's declared participants.
"""
from importlib import import_module
from mta.serialization import digest

PINS = (
    ('0169_accepted_state_ownership', '2cc7316e8d1de3dc675d46b0777c9e36b4d44a31d7df67d6ed21edc95428f92a'),
    ('0170_command_writer_compatibility', '1a42728e2377485be7cc53413c0c0d0419432d59fd13e81f1b93bccdc1415d87'),
)
PREVIOUS_RELEASE = '7628dc2ab675692477969b59619819143cda193b8fdf6a554567de82eb57661d'
BEFORE_SCHEMA = '5d4be25affa0c711430dfc4b741472f4cf3278d404cbba584cc6c83139007d0f'
BEFORE_GUARD = '465a24941c54d39a93dbbae92ae2457f048f0a3ced4f2094f2f6e1ff995cc041'


def migration_pins():
    return [list(pin) for pin in PINS]


def catalogue_delta(*, owner='vectorflow_mta_owner'):
    frozen = import_module('mta.runtime.migrations.' + PINS[0][0])
    result = {}
    def added(key, value):
        result[key] = dict(before=None, after=value)
    for name, body in frozen.FUNCTIONS.items():
        qualified = 'mta.' + name + '()'
        added('functions:' + qualified, dict(name=qualified, owner=owner, security_definer=False,
              body=body, configuration=['search_path=pg_catalog, mta'], language='plpgsql', returns='trigger'))
        added('grants:' + qualified + ':None:' + owner + ':' + owner + ':EXECUTE',
              dict(scope='function', name=qualified, owner=owner, column=None, grantor=owner,
                   grantee=owner, privilege='EXECUTE', grantable=False))
    added('column:mta.fresh_mta_runcommand.state_sealed', [10, 'boolean', True, '', '', 'false'])
    added('constraint:mta.fresh_mta_runcommand.accepted_command_complete',
          ['t', True, 'TRIGGER DEFERRABLE INITIALLY DEFERRED'])
    for schema, table, name in frozen.TRIGGERS:
        target = schema + '.' + table
        prefix = 'CREATE TRIGGER ' + name
        if name.startswith('accepted_rows_'):
            operation = name.removeprefix('accepted_rows_').upper()
            reference = {'INSERT': 'NEW TABLE AS new_rows',
                         'UPDATE': 'OLD TABLE AS old_rows NEW TABLE AS new_rows',
                         'DELETE': 'OLD TABLE AS old_rows'}[operation]
            definition = prefix + ' AFTER ' + operation + ' ON ' + target + ' REFERENCING ' + reference
            argument = 'vf_run_id' if schema == 'mta_state' else 'run_id'
            definition += " FOR EACH STATEMENT EXECUTE FUNCTION guard_accepted_rows('" + argument + "')"
        elif name == 'accepted_no_truncate':
            definition = prefix + ' BEFORE TRUNCATE ON ' + target + \
                         ' FOR EACH STATEMENT EXECUTE FUNCTION deny_accepted_truncate()'
        elif name == 'terminal_run_immutable':
            definition = prefix + ' BEFORE DELETE OR UPDATE ON ' + target + \
                         ' FOR EACH ROW EXECUTE FUNCTION guard_terminal_run()'
        elif name == 'zz_accepted_command_seal':
            definition = prefix + ' BEFORE INSERT OR DELETE OR UPDATE ON ' + target + \
                         ' FOR EACH ROW EXECUTE FUNCTION guard_command_seal()'
        elif name == 'accepted_command_complete':
            definition = 'CREATE CONSTRAINT TRIGGER ' + name + ' AFTER INSERT ON ' + target + \
                         ' DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION require_command_complete()'
        else:
            raise ValueError('Undeclared accepted-state trigger')
        added('trigger:' + target + '.' + name, ['O', definition])
    return result


def approved_receipt(extension):
    return (extension.get('migration_pins') == migration_pins()
        and extension.get('catalogue_delta_digest') == digest(catalogue_delta())
        and extension.get('previous_release') == PREVIOUS_RELEASE
        and extension.get('before_schema_digest') == BEFORE_SCHEMA
        and extension.get('before_guard_digest') == BEFORE_GUARD)


def require_specification(spec):
    if (spec['migration_pins'] != migration_pins() or spec['catalogue_delta'] != catalogue_delta()
            or spec['previous_release']['manifest_sha256'] != PREVIOUS_RELEASE):
        raise ValueError('Only the exact accepted-state migration/catalogue delta is supported')
