"""Exact registered-read compatibility after separating file and action cuts.

Only guard admission changes. Report calculations, file producers, action
writers and reference/selection formats retain their original identities.
The native build and consumed-schema transition are independently required;
this profile cannot reseal a capture, file, phase or existing read reference.
"""
import hashlib
import inspect
from importlib import import_module
from mta.presentation.context import PublicationUnavailable
from mta.presentation.request_scope import once_per_request

BASELINE_COMMIT = '18b9da4d5b1333d6f8409884e452bf12a7b0258f'
RECIPE = '4a8e21999d14a0aae89b6c5850bb2db38b3a34cd0073a15c91c4d46dc7ed2f38'
SELECTION_RECIPE = 'b2a0a38bb20c045eefc00d22b6dc5fcab3bc4f01634dbbf00a03cf9462ca678b'
ORIGINAL_DEPENDENCIES = {'mta.application.production_bor_contract': '81e6a3307ba2997f1b1e410c8e8bf43112ef45c8e4d3891ce485ce49d29a6249',
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
 'mta.presentation.chronic_sql': '2f0d6b3a523c25d8a528bfcb3f7cd17ecab3426c0d41553af565ca2f95a8b12d',
 'mta.presentation.daily_git_custom': 'a2ad0d6ba646559e495d15260b44031df1d7cb4a29f5b487a99aca6be1ce7ef6',
 'mta.presentation.daily_git_read': '53d772bc095764d2da005c37689ae7b85fc99fe3b1c1de5fa9193b921ca5981c',
 'mta.presentation.daily_native_prepared': '3bfd62df071eaae807ed33ea5c76cd9408869d227f6183f549ff752c7c0107c0',
 'mta.presentation.daily_rrr_read': '90ef3695f2d7f23940220d83f5687eb97ffbea113911831eda040e412abce3ed',
 'mta.presentation.dbm': '7d0268a08c32a062845ab6cdfdede64c412275e3886fb6dc28fe4bcf7ab73790',
 'mta.presentation.dbm_filters': 'ac0e50d7c54cdd52bff55375850f4109c1dfd0bdf024c70b96cd9e49058468dd',
 'mta.presentation.diagnostic_downloads': '37d4da2c65d1c6d6378c4440cbf9744cc80024ad5aff8bc79120f1cc64945f71',
 'mta.presentation.excess_filters': 'b621688b7d3fe8788d84e38fbcddeea2a41b6580624a3c1b0e5c836a4bf50476',
 'mta.presentation.expedite_charts': 'ed577d233de29dc7225a64270ad5dcc80fd41e491ed3fa862edc61f331fcc687',
 'mta.presentation.expedite_child_sources': '3818b33fffd93d8833e79f59acd9863d31fa9e4ea21f2d2999eb4432d6ddd352',
 'mta.presentation.expedite_parent': '1823bb9297cb54a756b706482172f3042186bd5fc10cf80f52caff7ba6e2daa6',
 'mta.presentation.expedite_read': '6bdbb0255ae2268cab93d08ecc1f5405e5362827a6ec6626174b2d8a59f2e742',
 'mta.presentation.guided_aggregates': 'da78431de87c0902fa72df0c38150075901dd8f6fa3ed7e197c4c3d6e5474635',
 'mta.presentation.guided_chronic': '6ef60416de80b5f9229ae8e82a87c4b725cfa037a7e85ecdca47366010b1e48d',
 'mta.presentation.guided_chronic_fields': '1934470a08d6f4a90ef19a5e50c1d4ab8f3bf559ecaff74901e6e1c3f38433d5',
 'mta.presentation.guided_dbm': '49688c990ebb6567e7b7cd1cf989a7f888e3f55a8b081b4590db1bee1b1ed1ff',
 'mta.presentation.guided_dbm_fields': 'e616d9fcd01cf4fccc979e2703517de7dcef565b7c0d1df05bfafdd51c35f271',
 'mta.presentation.guided_history_prepared': '104ec728730fc3538bfae7fc0f21346fd0da45de5cee575f36890841ab0ab4c3',
 'mta.presentation.insight_history_sql': '625ad45f184fe942bef9490d41cc06fa1b5405ae87fd08490ec4e3d66ff5fd5d',
 'mta.presentation.logistics_read': 'a2c20ce9899a9d3a25b14f9c93ff9e97b826747dd98e114687c90372b07ba70d',
 'mta.presentation.mdm_views': 'cae925d6b1084eb501c26ede7dd8f0a0fca647b049920df1c98a23c4fa5f77c6',
 'mta.presentation.native_excess_history': '06c7ecc3559455db07f061b749d86fc33a4eac664b3c7dd92b35dbea2da0cd73',
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
 'mta.presentation.registered_report_downloads': '7040d6652b7f3e1fe1cbbf22021c10c32e543492b8890f8c47186601aa938d10',
 'mta.presentation.registered_report_view': '54601d96060b2adf72f4f2bbe2b5f4e41a65ac5d61eb89a71082f500dfe12fe9',
 'mta.presentation.report_cache': '60cb72ccb7fc4f6cafd1a4f07c956a270ab6136b131e9316f959476704ec3063',
 'mta.presentation.research_read': 'c25585debdc6b925fbc24c71c59b272c00d7d8efcee7f9797748962a02056902',
 'mta.presentation.rrr_export': 'b91d90c5e64b1ce639a766224c0afdb795313aa6ffb2978303e0d1eee1c74d6a',
 'mta.presentation.rrr_prepared_sql': 'fdb6a9f89f2dac88fade799d646b219ccaf4317a35895fa86b761b42f3bc3739',
 'mta.presentation.rrr_sql': 'abdd11079c616d1bee8ed8affc212a5dd3136c21e840ebb8463788ee7683e03f',
 'mta.presentation.rrr_types': 'e4b739f68a724f8a41430f1a3b0ecb0ad8da8beafa456995a0737f5f0cda3487',
 'mta.presentation.runtime_report_downloads': '62ee73a83321718f7ca8fe2a0f45a3a3a7439473b21094d05fccee0129e85dc7',
 'mta.presentation.scoped_action_writer': '4fdb2cdaa12710d771eac5f620b123e30657c6589860734a334c4ec879a9a962',
 'mta.presentation.scoped_api': 'ccad0e5092687b436e6a3e6b413fe2ef9cf4ad30a7e0b7ff6bc8450307f03f07',
 'mta.presentation.scoped_artifacts': '6eb3ab87ebd779c2708a0e6e015680f69db5620aa15f7f7f4f6ad7aa24e5f86b',
 'mta.presentation.scoped_batch_downloads': 'f8e2ea3fa98485efa6269f5ad52e0f3c5434f1f9290b483981f674e1aa606c62',
 'mta.presentation.scoped_batch_files': 'c31ca676228e7a89ddda4c5cdf492384a81f2931841c9ccac0299e03eb5d998a',
 'mta.presentation.scoped_bor': '252edd378ec4e46eb7c980005b843d5121d6d62caa27147f6d3f9e328949bb64',
 'mta.presentation.scoped_btr': '88ea9ae66d8c5a8ed4750e8e0f8e5b4c0c01d52b1a46605edb642276a5476d89',
 'mta.presentation.scoped_dbm': '5b383ec4501948466e5b48113a3c3161abf7a112ab30c40b6c7d33f98482f092',
 'mta.presentation.scoped_dbm_stop': 'caa166c365621b9af8c46329b508e0e1f97c37a57121137404b00eaa4d642e84',
 'mta.presentation.scoped_dbm_view': '8f6fbb475537a1264ee53bf22bf5212f0bd3c6dedc4508f5b4b7d2de62353f19',
 'mta.presentation.scoped_expedite': 'c1587286c5cdb0dbb00d25ca35b0531e73c77d2ebb388a85a436639d40a6188b',
 'mta.presentation.scoped_guided': 'a17672804e168d0df9563edbd7b4c877a787f94348e267b2fad8b0581a477888',
 'mta.presentation.scoped_guided_availability': '377d982dc2d2b0e64c9b8c94aca451fd189c99228a1a6a4927f9e34130f5c49e',
 'mta.presentation.scoped_guided_chronic': '4022c6d63b3d43b0f264091a455ac8b697b14263cee18bb70aa5ad518e1cc4e4',
 'mta.presentation.scoped_guided_dbm': '9989438676d8f7502c758041a22800823db8adfb36a0dda9cc41a381e78528ea',
 'mta.presentation.scoped_guided_excess': 'c7020d2124426035fc24cca6fbfb68e749720b02b1d0a46461e03e10352d75b6',
 'mta.presentation.scoped_history': '96f467f8f3e851c83192e039c382e435547957f5af159a6639bb72fbd87fc210',
 'mta.presentation.scoped_logistics': '030351f92748430403fe1eda1c5425527329dfac18765fb5063efc14045f83b9',
 'mta.presentation.scoped_overview': '2b5ab380684b8cc1e837a1d3fff419d040f92632d3c23d110317742209ca65c6',
 'mta.presentation.scoped_preparation': 'c649b079df96074a74977e502c20b3a7436d1a3ee30bc8d53080072b6853f60a',
 'mta.presentation.scoped_read_cut': '1bd942217aeb81c940602e81a7283a36760996c0f084411569047ae81a1c339e',
 'mta.presentation.scoped_read_graph': '53becfa0a78a302ed761d164242705784a9cc6fe993fe3199825a1ebef6a9131',
 'mta.presentation.scoped_remark_writer': 'dc937ff2236eb3f9956d6ec3efafc6f69c0234b324467858a5ab528d0cf1b976',
 'mta.presentation.scoped_research': '467ea1f89dd5f0ccc7fad9e637f2cbcd04f85404857bb62d9b0c3da103eac4b0',
 'mta.presentation.scoped_rrr': 'e69a36385a9872b904054a941bbf8305bfa5def4c8f918a897143519cf2a90d9',
 'mta.presentation.scoped_selection': 'aa7cd5a9ceb48a5da1beb6f445607dfa7c721fa957e0a8a18fe6257d0f79dc31',
 'mta.presentation.scoped_view': 'b55cf315b2d5b6ded4d6e87ca3278fbada9287389d98076a1bcd659cf9921a1b',
 'mta.presentation.supplier_allocation': 'c5d5b6d79c476285fa3880c0f556792283925a0ac9126838564b39e963353e6d',
 'mta.presentation.views': 'b53981c460cfeaadcf6b85cea78aab1c970aea7e5cfc57c929472a0f3ff7c87a',
 'mta.runtime.diagnostic_publication': '9a37d00c2d0fad17169886e40dfc6f931c5f3b6a4231fbb08a513807e9bcbbd5',
 'mta.runtime.intake_diagnostic_models': '0deb10035783cb546ac573d02562b344f31104bdf4721e54353e1cc7b27ac5f3',
 'mta.runtime.intake_diagnostics': '9a7a72dbd88ea48fafc4798a684f8b33a26b01377ad565b54edfbe0cb3081696',
 'mta.runtime.runtime_report_registered_request': '44a92b00707e195dc0599e19efaa5804ae2f68313b13cd514b94a1d70f53000b',
 'release.phase_selection': '2ff72ae1ad25aad0d0011fb1429e992225fdc27880aecda30ea2de0019db00b6'}
ADAPTED_DEPENDENCIES = {'mta.presentation.generic_terminal_delivery': 'cdc6e1669c208c1591b904716028dbe8a2c7ffb6573e6c829edef804dd05efb3',
 'mta.presentation.registered_report_view': '01ae33ab88694414a7f45c816439965ad52e939f87d67bff9dba1fc4027cb144',
 'mta.presentation.scoped_artifacts': '4f1a61db37335940b1ce6911eff464cf99284053f57ca1fa7c8a764f852b4821',
 'mta.presentation.scoped_batch_downloads': '6d9c48ed037902564217055005e167782b6a4fffb822660efe60d830d27efb9e',
 'mta.presentation.scoped_batch_files': '8cfc8221749c47e8646e3689256682890348ba2456dcd75728ff82d1f52188f8',
 'mta.presentation.scoped_bor': '6f0f61572e1ead503b90d7193f6442c8b93f95e520975660d354f9bc0cade727',
 'mta.presentation.scoped_selection': '69e8fbb4a5c168ad30dcba47a1ab640394d04dc25c6f917ae8f781687aad802a',
 'mta.presentation.scoped_view': 'b55cf315b2d5b6ded4d6e87ca3278fbada9287389d98076a1bcd659cf9921a1b',
 'mta.presentation.views': 'c7499957ed618bfa74a8f2a2d43db9a44be8042f339fb39d9b81035646c29cf3',
 'mta.runtime.migrations.0238_registered_read_action_cut': '572d225c31d4b707da9f22e273b1669274afd46c9334355c73c067cbcea4110b',
 'mta.runtime.migrations.0239_production_generic_scope_read': '44e28f4a8b34912540ee56767e26c22ab1565870f583cc88a993936f5a522297',
 'mta.runtime.migrations.0242_generic_read_sql_aliases': 'edaae0a3a0da675f6ada277a89cc941d540d5668fd1222989191344e1de0a50b',
 'mta.runtime.production_scope_policy': '88ab6efa6f77958d874fbcaecb049a32dc7bee2368b7ad61f28dacc52612ff0f',
 'mta.runtime.runtime_report_registered_request': 'fe94595e3241bcdf96ab7704b5a7fd7eae4c975049d905887b885e67956aa468',
 'mta.runtime.runtime_report_request': '2cc9ec5352fe08145d14027c6ebc39587827de3c126aaac022df05243ae9631f'}

GUIDED_STATISTICS_READERS = {
    'mta.presentation.guided_aggregates': 'ecd1250cb65b42c5946cd4248c40d51b47a875dde83e5dce0366a5e874cde911',
    'mta.presentation.scoped_guided_availability': '9a1b4f5a92f0293b08451d6e2a08531f23df587c9baff26b2d9dc68ab9948dc7',
}

# These readers use existing sealed sources without changing producer identities.
PREPARED_REPORT_READERS = {
    'mta.presentation.guided_history_prepared': '38e462ce6152ed8f3d4b1cae5d177c40a2386617c88180a19211c16d76bea6ba',
    'mta.presentation.bor_sql': '5a93dd942ad2f85bb361f182f085a46c316afabfebb99f53991faf076b7548fa',
    'mta.presentation.boroa_sql': '196e2fc9c1a837cdbe9d1113d374d322b2ad3d20afa73a29523ed4bf5d27ec32',
    'mta.presentation.bpr_prepared': '82ca88d63d9e86eb79cc5638f53865c629b9e78aa6db4509b294fa51925575b1',
    'mta.presentation.daily_rrr_read': '1e01b6ac9b63b175868675eda3f8f10bf2fd8b16f53d3808d26344730c87bda5',
    'mta.presentation.planning_chart_sql': '27a395793e3c377f7ae18bba0635af85e2e74fd59aec51b3063c75f687b7cde8',
    'mta.presentation.planning_grid_sql': 'a338b91893b952746245332cd80937a826cefddf006b852aabd106a0436e7148',
    'mta.presentation.rrr_export': 'bd925acb777406e0d2bfca89fa1b86c1637e115bcdab142032bbb817cdff7cba',
    'mta.presentation.rrr_prepared_sql': 'e1fee9afec1fe5c5ecfe14cc9ee6f8541e8cc45630f33e9bfa0451fb0a97da21',
    'mta.presentation.scoped_api': 'dbbc47158e87250f49b0473661873b6edddadd9bfa95d3c98d9485ff2a99f06b',
    'mta.presentation.scoped_rrr': '3a4b2a8e9072936be23e3ffd5160a7c885a97b4fa984550f6833c0b470222919',
    'mta.presentation.scoped_dbm': '5d45396607d62d9729543d00e6161bba714f1038075ee47bbdf87f4af7216730',
    'mta.presentation.scoped_history': '905f199f4da10d551b702c2231a677b3fa587a8a8468daf5d999b12d9c568477',
    'mta.presentation.scoped_read_graph': 'f1973894ed5f16a749e6c3eb4756d99e9c90ce9630c785c0e84adff8dba0f673',
    'mta.presentation.views': '54a5cc2951fa834e75e97dab8469cb8313cdbeb413522e89ca782ec9fb8f5fc8',
}


@once_per_request
def recipe():
    if set(ADAPTED_DEPENDENCIES) != {'mta.runtime.runtime_report_request', 'mta.presentation.generic_terminal_delivery', 'mta.runtime.migrations.0242_generic_read_sql_aliases', 'mta.presentation.scoped_artifacts', 'mta.runtime.production_scope_policy', 'mta.presentation.scoped_bor', 'mta.runtime.migrations.0238_registered_read_action_cut', 'mta.presentation.scoped_batch_files', 'mta.runtime.runtime_report_registered_request', 'mta.presentation.views', 'mta.presentation.scoped_selection', 'mta.runtime.migrations.0239_production_generic_scope_read', 'mta.presentation.registered_report_view', 'mta.presentation.scoped_view', 'mta.presentation.scoped_batch_downloads'}:
        raise PublicationUnavailable('registered_read_profile_roster_differs')
    guided_qualified = False
    for name, checksum in dict(ORIGINAL_DEPENDENCIES, **ADAPTED_DEPENDENCIES).items():
        actual = hashlib.sha256(inspect.getsource(import_module(name)).encode()).hexdigest()
        if actual != checksum:
            if PREPARED_REPORT_READERS.get(name) == actual:
                continue
            if GUIDED_STATISTICS_READERS.get(name) == actual:
                if not guided_qualified:
                    guided_qualified = all(
                        hashlib.sha256(inspect.getsource(import_module(module)).encode()).hexdigest() == pin
                        for module, pin in GUIDED_STATISTICS_READERS.items())
                if guided_qualified:
                    continue
            raise PublicationUnavailable('registered_read_profile_source_differs:' + name)
    return RECIPE


def selection_recipe(observed):
    recipe()
    if observed != OBSERVED_SELECTION_RECIPE:
        raise PublicationUnavailable('registered_selection_profile_source_differs')
    return SELECTION_RECIPE




OBSERVED_SELECTION_RECIPE = '222870d577e1b2e71a5ae339351f55eb344e6a07431b7e861d9b87f55d4a4b4a'


# The guard-admission refactor reads this exact earlier producer format. These
# are historical identities, never values returned by current recipe_digest().
# Owner, sealed metadata, complete fields/occurrences and data digests remain
# independently checked by every binder. Unknown formats still fail closed.
GUARD_ADMISSION_PREDECESSOR = '5cb02c29343df69284f676e636d99545fa00dea0'
GUARD_ADMISSION_RECIPES = {'scoped_report_storage': '800d7ee3f1fb602be7caa3dcff16da0c765ce50a6433fb83019bd09279c2c7c3', 'scoped_prepared': 'f4b973520fc2a8f54fe03ddf86a348db97bc4e471975190a4be6eb57df2e342b', 'scoped_planning': '46a7c0e06b1a40320ec665d6a188edcacd0751e4282f20bd51f48c2e56e6175d', 'scoped_transit_storage': 'd9e0e25bdc86b927d4fa761a006ef10201b07919925b85d13a69949ba9c27894', 'scoped_pick_storage': 'ae87f82469b7e5241365df16bb93d15f01d23710c01afa29fe6b1627503ade8b', 'scoped_expedite_storage': '11d7313d408ccf14512dd4b5e62b4dd4a68974d3432d53a3fefdf644368f0a7c', 'scoped_expedite_parent': '264c1697a55d2a05cfab31ae94db54357b51682e890ba6b219f6a9e205913da0', 'scoped_git': '648e985e191dfeb384aa6bb79175c6891b5ba58680d4f17933c125d702848b9e', 'scoped_remarks': '943e61294f73a2c24ec882956a3344badde6f9666ef930b228ebafa4483fc01f', 'scoped_requests': '7982419d90f4e018f105ff89253fe6f84fbc32b1272bf7eeba4bc2ebe06aff1a'}

GUARD_ADMISSION_RECIPES['scoped_expedite'] = '8aabac8c3ccb42b238fd5983f7e85adb0015f434f3df6658d8c75325b60f8067'

# The terminal Planning page change leaves Expedite's shared filters unchanged.
TERMINAL_PLANNING_EXPEDITE_READER = (
    '8689ef5816bdc0325a1b54c29f932ca1cd5c3b28b3504dbbf473fd05947c0127',
    'f575f734075dcb05bb85a3097f934d186affd7e1eb49944d452cfc5865d7352b',
)

def compatible_guard_recipe(family, observed, current):
    if family not in GUARD_ADMISSION_RECIPES:
        raise ValueError('Unknown guard-admission report contract')
    return (observed == current or observed == GUARD_ADMISSION_RECIPES[family]
            or (family == 'scoped_expedite'
                and (observed, current) == TERMINAL_PLANNING_EXPEDITE_READER))
