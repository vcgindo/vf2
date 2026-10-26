"""Versioned PostBPR read references over the existing immutable BPR graph.

The old graph schema remains v2. New publication configuration and an explicit
recipe distinguish this extension; no old request adopts a new report roster.
"""
from dataclasses import replace
from django.db import connection, transaction
from mta.serialization import digest
from mta.presentation.context import PublicationUnavailable
from mta.presentation.request_scope import once_per_request

LEGACY_COMMIT = '59ca6cd311090da2305a56ba2f447f57e0c9dafd'
LEGACY_VIEW_RECIPE = 'c0cb3006571037d08bbee122ffc2db414363347cc5d6d63932bb060d468a97bd'
LEGACY_SELECTION_RECIPE = '885c44e7e2c5c4788eaa861d5e41785b6e5ba619f69017f6f3f20a958146adad'
LEGACY_DEPENDENCIES = {'mta.application.production_bor_contract': '81e6a3307ba2997f1b1e410c8e8bf43112ef45c8e4d3891ce485ce49d29a6249',
 'mta.application.production_output_policy': 'b81b3e244662f61e01c244814de83029b2f40dbc7b0e77785f48edf928b4852e',
 'mta.mdm.season_current': '1c1d55a3655e8c242a282655af9301eb14ecd1ce8319d6d2526c5d5fc6fc2cb2',
 'mta.presentation.bor_preparation': '50834a1dac0b70e31f4b518439e5796bc3ffc68bcb087cca32daf41b2f40321a',
 'mta.presentation.bor_sql': 'c652f3d7c2dbdb5b6d9d214afa9aa54fbe7ac50785753aa45fc19a4a3bb7639f',
 'mta.presentation.boroa_preparation': '337bc08ba747cabfc2c017a7009d8777dbaf0e6a0c302a4bb69a18405c97c51f',
 'mta.presentation.boroa_sql': '6ff64d65a01312fc5ba42e5af77edefd32f6c55467dae3dbb84a963c4208c802',
 'mta.presentation.bpr_export': 'ef490c325740e814c686399be4627afb01cdb1b20f0e9f3b391706aebab28060',
 'mta.presentation.bpr_prepared': 'e539f41fcf5a00db56a1a557d5e165db028d0bf1c77dcbeb7c6757ef87ef0d8e',
 'mta.presentation.bpr_remarks': 'dca51c1203360ff4cb90cc1b5a14bc11450284dfec6e9560c9b62660b6459cef',
 'mta.presentation.bpr_response': '47d6cd6bb8cd743b13c03c16f2b7259031a9675e2d266c13cc78def4c8208f36',
 'mta.presentation.btr': '7e964f2156ee7283ebd69d99fc1329fda410d65bbfc443b4743ef250a54a60d6',
 'mta.presentation.btr_display': '08caa3276738dc9ca3a1f982dd4f56528ae67b8c2b91d919989e075490cf1873',
 'mta.presentation.btr_export': 'cf645caf673fe6c525757e4143bf4b4fa22d575fcde57fe8ef6f378d732eec66',
 'mta.presentation.btr_sql': '05e006fabb38c89cd6abab1e8b467d65177cb71dc4008ac1c9c1c200cb1aa309',
 'mta.presentation.buffer_trends_sql': 'bfed6dd7aefd33caf3eb2c89a021545dadc7e03adedc7133175d700efda315f9',
 'mta.presentation.daily_git_custom': 'a2ad0d6ba646559e495d15260b44031df1d7cb4a29f5b487a99aca6be1ce7ef6',
 'mta.presentation.daily_git_read': '53d772bc095764d2da005c37689ae7b85fc99fe3b1c1de5fa9193b921ca5981c',
 'mta.presentation.daily_rrr_read': '90ef3695f2d7f23940220d83f5687eb97ffbea113911831eda040e412abce3ed',
 'mta.presentation.dbm': '7d0268a08c32a062845ab6cdfdede64c412275e3886fb6dc28fe4bcf7ab73790',
 'mta.presentation.dbm_filters': 'ac0e50d7c54cdd52bff55375850f4109c1dfd0bdf024c70b96cd9e49058468dd',
 'mta.presentation.excess_filters': 'b621688b7d3fe8788d84e38fbcddeea2a41b6580624a3c1b0e5c836a4bf50476',
 'mta.presentation.expedite_charts': 'ed577d233de29dc7225a64270ad5dcc80fd41e491ed3fa862edc61f331fcc687',
 'mta.presentation.expedite_child_sources': '3818b33fffd93d8833e79f59acd9863d31fa9e4ea21f2d2999eb4432d6ddd352',
 'mta.presentation.expedite_parent': '1823bb9297cb54a756b706482172f3042186bd5fc10cf80f52caff7ba6e2daa6',
 'mta.presentation.expedite_read': '6bdbb0255ae2268cab93d08ecc1f5405e5362827a6ec6626174b2d8a59f2e742',
 'mta.presentation.logistics_read': 'a2c20ce9899a9d3a25b14f9c93ff9e97b826747dd98e114687c90372b07ba70d',
 'mta.presentation.mdm_views': 'cae925d6b1084eb501c26ede7dd8f0a0fca647b049920df1c98a23c4fa5f77c6',
 'mta.presentation.native_report_colours': 'd209978f5f5081c504de3f631321ff8f9bc5663223f87dcc579fc1525ce99bcf',
 'mta.presentation.planning_chart_sql': 'e1600f5c2b11eb6ab1a279fa351c1e62fca50093f9962a20ec257986c1b03a3d',
 'mta.presentation.planning_custom_sql': '2578e1595fd8f92d8d20442dae348e95acfb4cc192e8d83f1c4f72d655da06f5',
 'mta.presentation.planning_expedite_chart_sql': '0ee42ae20a74e88aecd6d991951def9f3a304bf9915f48441f86f82b2b623e32',
 'mta.presentation.planning_expedite_charts': '2b3fb05802812789e94188f9a5c791acb24f0504a6688feb5e2ccbc5edebd698',
 'mta.presentation.planning_expedite_custom': '23946b2d182d0d21aea1d46019ab319842ea285b89be429dfa920aeaf7a4ed4d',
 'mta.presentation.planning_expedite_custom_sql': 'dee94efcceea0b9e81f280ccb4f4d6bac6677dcd3e79f439e1623be65103e48c',
 'mta.presentation.planning_expedite_grids': '4cbe0bd09b6f7e9f719a6e8f837fc37da7830b7a05646db2656ea62accd3e791',
 'mta.presentation.planning_expedite_sql': 'f34a7e1f1c518019eee43fc56da8386cc656bf1d5de399a3720763f0e6c5d29f',
 'mta.presentation.planning_expedite_transit': 'de329ba9571ac455ec870652ea2ca2a6d33ce617ff62d0f8503a943de977f3a3',
 'mta.presentation.planning_git_sql': '7ec8799bc70e216149adab5f5db9d334ed048cc991ef88125e2b17f7e99b1d00',
 'mta.presentation.planning_grid_sql': '86963a1c38ef3fc2bb5d6d8d891f970a5e0886937ccfab7fde1f3e9932936ddf',
 'mta.presentation.rrr_export': 'b91d90c5e64b1ce639a766224c0afdb795313aa6ffb2978303e0d1eee1c74d6a',
 'mta.presentation.rrr_prepared_sql': 'fdb6a9f89f2dac88fade799d646b219ccaf4317a35895fa86b761b42f3bc3739',
 'mta.presentation.rrr_sql': 'abdd11079c616d1bee8ed8affc212a5dd3136c21e840ebb8463788ee7683e03f',
 'mta.presentation.rrr_types': 'e4b739f68a724f8a41430f1a3b0ecb0ad8da8beafa456995a0737f5f0cda3487',
 'mta.presentation.scoped_action_writer': '4fdb2cdaa12710d771eac5f620b123e30657c6589860734a334c4ec879a9a962',
 'mta.presentation.scoped_artifacts': '6eb3ab87ebd779c2708a0e6e015680f69db5620aa15f7f7f4f6ad7aa24e5f86b',
 'mta.presentation.scoped_batch_downloads': 'f8e2ea3fa98485efa6269f5ad52e0f3c5434f1f9290b483981f674e1aa606c62',
 'mta.presentation.scoped_batch_files': 'c31ca676228e7a89ddda4c5cdf492384a81f2931841c9ccac0299e03eb5d998a',
 'mta.presentation.scoped_bor': '252edd378ec4e46eb7c980005b843d5121d6d62caa27147f6d3f9e328949bb64',
 'mta.presentation.scoped_btr': '88ea9ae66d8c5a8ed4750e8e0f8e5b4c0c01d52b1a46605edb642276a5476d89',
 'mta.presentation.scoped_dbm': '5b383ec4501948466e5b48113a3c3161abf7a112ab30c40b6c7d33f98482f092',
 'mta.presentation.scoped_dbm_stop': 'caa166c365621b9af8c46329b508e0e1f97c37a57121137404b00eaa4d642e84',
 'mta.presentation.scoped_dbm_view': '20eb399e4b0b3b7a0d9f150d0d032ca91bea026b920b85838aea90bf7101a9e0',
 'mta.presentation.scoped_expedite': 'c1587286c5cdb0dbb00d25ca35b0531e73c77d2ebb388a85a436639d40a6188b',
 'mta.presentation.scoped_history': '96f467f8f3e851c83192e039c382e435547957f5af159a6639bb72fbd87fc210',
 'mta.presentation.scoped_logistics': '030351f92748430403fe1eda1c5425527329dfac18765fb5063efc14045f83b9',
 'mta.presentation.scoped_overview': '2b5ab380684b8cc1e837a1d3fff419d040f92632d3c23d110317742209ca65c6',
 'mta.presentation.scoped_preparation': 'c649b079df96074a74977e502c20b3a7436d1a3ee30bc8d53080072b6853f60a',
 'mta.presentation.scoped_read_cut': '1bd942217aeb81c940602e81a7283a36760996c0f084411569047ae81a1c339e',
 'mta.presentation.scoped_read_graph': '53becfa0a78a302ed761d164242705784a9cc6fe993fe3199825a1ebef6a9131',
 'mta.presentation.scoped_remark_writer': 'dc937ff2236eb3f9956d6ec3efafc6f69c0234b324467858a5ab528d0cf1b976',
 'mta.presentation.scoped_rrr': 'e69a36385a9872b904054a941bbf8305bfa5def4c8f918a897143519cf2a90d9',
 'mta.presentation.views': '2d9da74e857335b42e48db12c388e70f609021b089ebbfda9561e397aad02a83',
 'release.phase_selection': '2ff72ae1ad25aad0d0011fb1429e992225fdc27880aecda30ea2de0019db00b6'}



@once_per_request
def require_legacy_dependencies():
    """Admit only the finite compatible reader; never grant producer rights."""
    from mta.presentation.legacy_scope_read_compatibility import verify
    verify()


def legacy_view_recipe():
    require_legacy_dependencies()
    return LEGACY_VIEW_RECIPE


def legacy_selection_recipe():
    require_legacy_dependencies()
    return LEGACY_SELECTION_RECIPE


def recipe_digest():
    from mta.presentation.legacy_scope_read_compatibility import POSTBPR_RECIPE
    require_legacy_dependencies()
    return POSTBPR_RECIPE


def applicable_reference(row):
    from mta.runtime.scope_runtime_reports import PUBLICATION_REFERENCE
    return row.metadata.get('runtime_reports', {}).get('schema') == PUBLICATION_REFERENCE


def configuration(run):
    from mta.runtime.input_reader import read_input
    from mta.runtime.production_scope import PUBLICATION_SCHEMA
    from mta.runtime.scope_runtime_reports import publication_configuration, require_test_database
    request = read_input(run, components=('scope_request',)).get('scope_request')
    if (type(request) is not dict or set(request) != {'schema','scope','command_key',
            'compatibility_digest','runtime_reports','report_hooks','publication_recipe'}
            or request['schema'] != PUBLICATION_SCHEMA or request['scope'] != 'UptoBPR'
            or type(request['command_key']) is not str or not 1 <= len(request['command_key']) <= 120):
        raise PublicationUnavailable('postbpr_read_request_required')
    from mta.runtime.ingestion_context import sha
    sha(request['compatibility_digest']); sha(request['publication_recipe'])
    require_test_database()
    _, hook, _ = publication_configuration(request['runtime_reports'])
    if hook != request['report_hooks']:
        raise PublicationUnavailable('postbpr_read_hook_differs')
    return request['runtime_reports'], digest(request)


def require_publication(run, phase, configuration_digest, request_digest):
    from mta.runtime.runtime_report_publication import read
    receipt = read(run.pk, placement='PostBPR', verify_bytes=False)
    if (receipt.owner_kind != 'SCOPED_PHASE' or receipt.phase_id != phase.pk
            or receipt.source_digest != phase.digest
            or receipt.configuration_digest != configuration_digest
            or receipt.scope_request_digest != request_digest):
        raise PublicationUnavailable('postbpr_read_publication_owner_differs')
    return receipt


def metadata(bpr, planning, git, expedition, files, configuration_value, request_digest):
    from mta.presentation import scoped_view
    value = dict(scoped_view._metadata(bpr, planning, git, expedition, files,
        configuration_value, request_digest))
    value['recipe_digest'] = recipe_digest()
    return value


def bind(row, expected_digest):
    from mta.presentation import scoped_view, scoped_read_graph
    scoped_view.verify_guards(publication=True)
    if (not applicable_reference(row) or row.digest != expected_digest
            or row.digest != digest(row.metadata) or row.recipe_digest != recipe_digest()
            or row.action_command_id is not None or row.previous_reference_id is not None):
        raise PublicationUnavailable('postbpr_read_reference_identity_differs')
    config, request_digest = configuration(row.report_generation.run)
    require_publication(row.report_generation.run, row.report_generation.phase,
        config['configuration_digest'], request_digest)
    bpr, planning, git, expedition = scoped_read_graph.bind(row)
    files = scoped_view._files(row.report_generation.phase, row)
    if (row.runtime_reports_digest != config['configuration_digest']
            or metadata(bpr,planning,git,expedition,files,config,request_digest) != row.metadata):
        raise PublicationUnavailable('postbpr_read_reference_dependencies_differ')
    return scoped_view.ViewBinding(row,bpr,planning,git,expedition)


@transaction.atomic
def prepare(phase_id, *, expected_digest, action_revision):
    from mta.presentation.legacy_scope_read_compatibility import require_original_writer
    require_original_writer()
    from mta.runtime.models import RunPhaseAcceptance, CalculationRun, ScopeReadReference, RemarkOwner
    from mta.presentation import (scoped_view, scoped_sources, scoped_requests,
        scoped_report_storage, scoped_prepared, scoped_planning, scoped_transit_storage,
        scoped_pick_storage, scoped_expedite_storage, scoped_git, scoped_remarks,
        scoped_expedite_parent, scoped_expedite)
    from mta.runtime import scoped_pick_files
    phase = RunPhaseAcceptance.objects.select_related('snapshot').get(pk=phase_id)
    from mta.runtime.scope_execution import _source_lock
    _source_lock(phase.run_id)
    run = CalculationRun.objects.select_for_update().get(pk=phase.run_id)
    config, request_digest = configuration(run)
    require_publication(run,phase,config['configuration_digest'],request_digest)
    scoped_view.verify_guards(publication=True)
    sources = scoped_sources.bind(phase_id,expected_digest=expected_digest,
        action_revision=action_revision,include_nms=True,include_inherited_btr=True)
    if sources.inherited_btr is None:
        raise PublicationUnavailable('bpr_read_reference_inherited_btr_required')
    scoped_requests.bind(sources)
    files = scoped_pick_files.prepare(phase_id,expected_digest=expected_digest)
    nms = replace(sources,inherited_btr=None)
    plain = replace(nms,_images={key:item for key,item in sources._images.items()
        if key!='closing/consumer_context/NMSAllItems'})
    reports = scoped_report_storage._prepare(phase,plain)
    prepared = scoped_prepared._prepare(reports,plain)
    nms_prepared = replace(prepared,sources=nms)
    planning = scoped_planning._prepare(nms_prepared)
    transit = scoped_transit_storage._prepare(phase,plain)
    pick = scoped_pick_storage._prepare(phase,plain)
    core = scoped_expedite_storage._prepare(nms_prepared,pick)
    git = scoped_git._prepare(replace(prepared,transit=transit))
    RemarkOwner.objects.select_for_update().get(pk='BPRReport_RemarkDetails')
    remarks = scoped_remarks.bind(nms,configuration_digest=reports.generation.configuration_digest)
    parent = scoped_expedite_parent._prepare(core,remarks,
        expected_core_digest=core.generation.digest,action_revision=action_revision)
    expedition = scoped_expedite.ExpediteBinding(core,parent,transit,scoped_requests.bind(sources))
    bpr = replace(prepared,sources=sources,remarks=remarks,transit=transit)
    value = metadata(bpr,planning,git,expedition,files,config,request_digest)
    checksum = digest(value)
    row = ScopeReadReference.objects.filter(digest=checksum).first()
    if row is None:
        row = ScopeReadReference(report_generation=reports.generation,git_generation=git.generation,
            expedite_parent_generation=parent.generation,pick_files=files,
            recipe_digest=recipe_digest(),runtime_reports_digest=config['configuration_digest'],
            metadata=value,digest=checksum)
        with scoped_view._owner(row.pk):row.save(force_insert=True)
    return bind(row,checksum)
