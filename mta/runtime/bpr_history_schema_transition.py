"""Exact history-owner upgrade for the approved retained TEST database."""
from mta.serialization import digest

MIGRATION_NAME = '0223_bpr_history_completion'
MIGRATION_SHA256 = '26f63fb590ad7c818c57beab04ece5800cbfd7913d5d36bc5b5850910dc03b74'
INITIALIZATION = 'ed6ce944-372d-4038-aec4-89f91131648c'
PREVIOUS_COMMIT = '9bc51168d217983de4d88545a06ef4a30bf78f53'
PREVIOUS_RELEASE = '501215cd0f74979a7050136385c2553d8236220a2bd867c87b96f576b6826103'
BEFORE_SCHEMA = '46130086bf61e80291d6f5fcbeee7798bad1bee640a4571aa79ca31a1a5202b6'
BEFORE_GUARD = '4d953076c050ae2592528ec0c9d2855c67231c78fe6f7617be4f17afd2db7753'
# Full167-entry catalogue/ACL delta observed under rollback on database402363.
# Only the frozen ingestion_watch body changes; all other objects are additive.
DELTA = '507f6c7d3d02db81dde6c99af2d6b837922ca18bc8f840cc227f391971cfe103'


def migration_pins():
    return [[MIGRATION_NAME, MIGRATION_SHA256]]


def require_specification(spec):
    if (spec['initialization_id'] != INITIALIZATION or spec['migration_pins'] != migration_pins()
            or spec['previous_release']['source_commit'] != PREVIOUS_COMMIT
            or spec['previous_release']['manifest_sha256'] != PREVIOUS_RELEASE
            or digest(spec['catalogue_delta']) != DELTA
            or {key for key,value in spec['catalogue_delta'].items() if value['before'] is not None}
                != {'functions:mta.ingestion_watch()'}):
        raise ValueError('Only the exact approved late BPR history schema transition is supported')


def approved_receipt(extension):
    return (extension.get('initialization_id') == INITIALIZATION
        and extension.get('migration_pins') == migration_pins()
        and extension.get('previous_release') == PREVIOUS_RELEASE
        and extension.get('before_schema_digest') == BEFORE_SCHEMA
        and extension.get('before_guard_digest') == BEFORE_GUARD
        and extension.get('catalogue_delta_digest') == DELTA)
