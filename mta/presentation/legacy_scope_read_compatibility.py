"""Finite read-only adapter profile for retained intermediate references.

The accepted recipes belong to the original build. Source pins below describe
this compatible reader, not a replacement execution/producer identity. Native
code/schema admission is independently required. No old reference is resealed.
"""
import hashlib
import inspect
from importlib import import_module

from mta.presentation.context import PublicationUnavailable
from mta.presentation.request_scope import once_per_request


BASELINE_COMMIT = '45055c8a47571803bba4fd3961f063022647c36e'
POSTBPR_RECIPE = '31fee0cee1f8b9008fd969da3585537af75a0321bbb3f2664a2d4490e03eff38'
POSTBPR_SELECTION_RECIPE = '2027c2fa7f1c192636249b928bbe19af0ecd0a98ddb464e7197df0b9c8bf2d1a'
# Exact candidate source pins are frozen after the bounded adapter change.
# A placeholder is fail-closed, never a wildcard or an environment override.
ADAPTED_DEPENDENCIES = {
 'mta.presentation.planning_expedite_transit': '28e75d9a64727d0ce58e05dadaea80ebb58988725d4cd460d46e54bba8c01a0a',
 'mta.presentation.scoped_expedite': '6dc5bf1695293353f2c305d626afc9df4e66e1ee5d8e7870780dd2692ab9f9c4',
 'mta.presentation.scoped_dbm_view': '8f6fbb475537a1264ee53bf22bf5212f0bd3c6dedc4508f5b4b7d2de62353f19',
 'mta.presentation.views': 'c7499957ed618bfa74a8f2a2d43db9a44be8042f339fb39d9b81035646c29cf3'}
DISPATCHERS = {
    'mta.presentation.diagnostic_downloads': '37d4da2c65d1c6d6378c4440cbf9744cc80024ad5aff8bc79120f1cc64945f71',
    'mta.runtime.diagnostic_publication': '9a37d00c2d0fad17169886e40dfc6f931c5f3b6a4231fbb08a513807e9bcbbd5',
    'mta.runtime.intake_diagnostics': '9a7a72dbd88ea48fafc4798a684f8b33a26b01377ad565b54edfbe0cb3081696',
    'mta.presentation.request_scope': '53d71c2b3a329720090a13f63049606479d9ef771983c7e3a4688da930a0bfdc',
    'mta.presentation.report_cache': '60cb72ccb7fc4f6cafd1a4f07c956a270ab6136b131e9316f959476704ec3063',
    'mta.presentation.guided_history_prepared': '104ec728730fc3538bfae7fc0f21346fd0da45de5cee575f36890841ab0ab4c3',
    'mta.presentation.insight_history_sql': '625ad45f184fe942bef9490d41cc06fa1b5405ae87fd08490ec4e3d66ff5fd5d',
    'mta.presentation.guided_chronic': '6ef60416de80b5f9229ae8e82a87c4b725cfa037a7e85ecdca47366010b1e48d',
    'mta.presentation.chronic_sql': '2f0d6b3a523c25d8a528bfcb3f7cd17ecab3426c0d41553af565ca2f95a8b12d',
    'mta.presentation.guided_dbm': '49688c990ebb6567e7b7cd1cf989a7f888e3f55a8b081b4590db1bee1b1ed1ff',
    'mta.presentation.research_read': 'c25585debdc6b925fbc24c71c59b272c00d7d8efcee7f9797748962a02056902',
    'mta.presentation.supplier_allocation': 'c5d5b6d79c476285fa3880c0f556792283925a0ac9126838564b39e963353e6d',
    'mta.presentation.scoped_api': 'ccad0e5092687b436e6a3e6b413fe2ef9cf4ad30a7e0b7ff6bc8450307f03f07',
    'mta.presentation.runtime_report_downloads': '62ee73a83321718f7ca8fe2a0f45a3a3a7439473b21094d05fccee0129e85dc7',
    'mta.presentation.scoped_view': '501572cdc61bc1eebcb61ba2c6bd42d3ee571988290daf08d4eee16789c68306',
    'mta.presentation.scoped_selection': 'aa7cd5a9ceb48a5da1beb6f445607dfa7c721fa957e0a8a18fe6257d0f79dc31',
    'mta.presentation.runtime_report_view': 'f1c6cafbc344f0939e149890cce9373e918f85015e86a9b94071973f752ea6ff',
}


@once_per_request
def verify():
    from mta.presentation.runtime_report_view import LEGACY_DEPENDENCIES
    from mta.presentation.registered_read_compatibility import PREPARED_REPORT_READERS
    if set(ADAPTED_DEPENDENCIES) - set(LEGACY_DEPENDENCIES):
        raise PublicationUnavailable('legacy_scope_read_profile_dependency_unknown')
    expected = dict(LEGACY_DEPENDENCIES, **ADAPTED_DEPENDENCIES, **DISPATCHERS)
    for name, checksum in expected.items():
        actual = hashlib.sha256(inspect.getsource(import_module(name)).encode()).hexdigest()
        if actual != checksum:
            if PREPARED_REPORT_READERS.get(name) == actual:
                continue
            raise PublicationUnavailable('legacy_scope_read_profile_source_differs:' + name)


@once_per_request
def verify_expedite():
    """Exact former composite reader boundary, without granting view writers.

    The original composite hashed these readers and its own module. Broader
    legacy view/archive profiles retain their independent strict admission.
    """
    from mta.presentation.runtime_report_view import LEGACY_DEPENDENCIES
    names=('planning_expedite_sql','planning_expedite_custom_sql','planning_expedite_chart_sql',
        'planning_expedite_transit','planning_expedite_grids','planning_expedite_custom','planning_expedite_charts',
        'expedite_read','expedite_charts','expedite_child_sources','planning_grid_sql','rrr_sql',
        'excess_filters','expedite_parent','scoped_expedite')
    expected=dict(LEGACY_DEPENDENCIES,**ADAPTED_DEPENDENCIES)
    for module in names:
        name='mta.presentation.'+module
        actual=hashlib.sha256(inspect.getsource(import_module(name)).encode()).hexdigest()
        if actual!=expected[name]:
            raise PublicationUnavailable('legacy_expedite_read_profile_source_differs:'+name)


def require_original_writer():
    raise PublicationUnavailable('legacy_scope_mutation_requires_original_build')
