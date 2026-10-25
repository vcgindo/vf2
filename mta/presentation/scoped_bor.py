"""Read-only BOR projections of an explicitly selected, accepted TEST BPR phase.

The normal BOR amendment consumes the original same-run dispatch colour:
r1_rationed_report.rationed_report projects r1_requirement.colours.dispatch.band
directly; late_bpr_transfer preserves that report. No calculation is replayed.
"""
from dataclasses import dataclass
import hashlib
import json

from django.conf import settings
from mta.application import production_bor_contract, production_output_policy
from mta.presentation.context import PublicationUnavailable
from mta.runtime import phase_state
from mta.runtime.relational_state import load_image, quote, table_sql


def policy(view):
    """Validate the pinned opt-in without selecting or changing a serving view."""
    from mta.runtime.scope_runtime_reports import require_test_database
    sources = view.bpr.sources
    expected = dict(purpose='owned-scoped-test', run_id=str(view.run_id),
        phase_id=str(sources.acceptance_id), phase_digest=sources.acceptance_digest,
        snapshot_digest=sources.snapshot_digest, output_contract=production_output_policy.contract())
    if getattr(settings, 'VF_MTA_SCOPED_BOR_OUTPUT_POLICY', None) != expected:
        raise PublicationUnavailable('bpr_bor_test_output_policy_required')
    try:
        require_test_database()
    except ValueError as error:
        raise PublicationUnavailable('bpr_bor_owned_test_database_required') from error
    return expected


def require_binding(run, view):
    from mta.presentation.scoped_view import ViewBinding
    from mta.presentation import scoped_sources
    if not isinstance(view, ViewBinding) or view.run_id != run.pk:
        raise PublicationUnavailable('bpr_bor_view_owner_differs')
    declaration = policy(view)
    sources = view.bpr.sources
    current = scoped_sources.bind(sources.acceptance_id,
        expected_digest=sources.acceptance_digest, action_revision=sources.action_revision,
        read_reference=view.reference)
    if (current.run.pk != run.pk or current.source_digest != sources.source_digest
            or current.snapshot_digest != sources.snapshot_digest):
        raise PublicationUnavailable('bpr_bor_view_owner_differs')
    phase = scoped_sources._accepted_phase(sources.acceptance_id, sources.acceptance_digest)
    return BorBinding(run, view, phase, declaration['output_contract'])


def _values(rows, fields):
    from mta.presentation.bpr_sql import _values_cte
    values = [dict(vf_ordinal=i, **row) for i, row in enumerate(rows)]
    typed = dict(vf_ordinal='bigint', **fields)
    return _values_cte(values, tuple(typed), {name: '::'+kind for name, kind in typed.items()})


@dataclass(frozen=True)
class BorBinding:
    run: object
    view: object
    phase: object
    output_policy: dict

    def _image(self, node, table, required):
        from mta.presentation import scoped_sources
        manifest = self.phase.snapshot.manifest
        logical = scoped_sources._image(manifest, node)
        if logical is None:
            raise PublicationUnavailable('bpr_bor_source_unavailable:'+'/'.join(node))
        item = scoped_sources._checked(manifest['images'].get(logical))
        if (not logical.startswith('phase/BPR/') or item['table'] != table
                or item['image'] not in (logical, logical.replace('phase/BPR/', 'phase/PRE_BPR/', 1))):
            raise PublicationUnavailable('bpr_bor_source_owner_differs')
        # The manifest's physical locator owns reused PRE_BPR images.
        try:
            rows = load_image(self.run, item, table_registry=phase_state.REGISTRY)
        except ValueError as error:
            raise PublicationUnavailable('bpr_bor_source_rows_differ:'+table) from error
        fields = {field for field, _, _ in item['fields']}
        if not fields and item['count'] == 0:
            fields = {field for field, _ in phase_state.REGISTRY[table]}
        if not set(required) <= fields or any(not set(required) <= set(row) for row in rows):
            raise PublicationUnavailable('bpr_bor_source_fields_missing:' + table)
        selected = ','.join(quote(column)+' AS '+quote(field) for field, column, _ in item['fields'])
        if not selected:
            selected = ','.join(quote(field) for field, _ in phase_state.REGISTRY[table])
        return rows, ('SELECT vf_ordinal,'+selected+' FROM '+table_sql(table)+
            ' WHERE vf_run_id=%s AND vf_image=%s', [self.run.pk, item['image']])

    def source_query(self, name):
        from mta.presentation.bor_contract import FIELDS
        from mta.presentation.boroa_contract import PREPARED_FIELDS
        if name == 'SupplierDispatchReq':
            rows, _ = self._image(('state','complete',name), 'complete/BPR/'+name,
                                  production_bor_contract.INPUT_FIELDS)
            report = self.view.bpr.sources.rows('reports/bpr/vf_RationedReqReport')
            try:
                colours = [dict(SKUCode=row['SKUCode'], WHCode=row['WhCode'], DispatchColor=row['DispatchColor'])
                           for row in report]
                rows = production_bor_contract.produce(supplier_dispatch_rows=rows,
                    dispatch_colours=colours, policy=self.output_policy['normal_bor'])
            except (KeyError, ValueError) as error:
                raise PublicationUnavailable('bpr_bor_projection_invalid') from error
            return _values(rows, {name: ('bigint' if kind=='int' else 'text')
                                 for name, kind in FIELDS['SupplierDispatchReq'].items()})
        if name in ('SOBData', 'MOQData'):
            return self._image(('state','supplier_'+('sob' if name=='SOBData' else 'moq')),
                               'BPR/'+name, FIELDS[name])[1]
        if name == 'BORWithOrderAllocation':
            core = [field for field in PREPARED_FIELDS['A'] if field not in production_output_policy.ATTRIBUTES]
            rows, _ = self._image(('consumers','production_reports',name), 'production/'+name, core)
            try:
                rows = production_output_policy.bor_oa(rows, self.output_policy)
            except ValueError as error:
                raise PublicationUnavailable('bpr_boroa_projection_invalid') from error
            return _values(rows, PREPARED_FIELDS['A'])
        if name == 'BOROARequirement':
            rows, relation = self._image(('consumers','production_reports',name), 'production/'+name,
                                        ('SKUCode','WhCode','AdvAllocDone'))
            from mta.presentation.scoped_sources import _image
            manifest = self.phase.snapshot.manifest
            logical = _image(manifest, ('consumers','production_reports',name))
            fields = {field for field, _, _ in manifest['images'][logical]['fields']}
            if not fields and not rows:
                # A genuinely empty older bag still needs the declared typed
                # relation. Its producer-parent projection below verifies the
                # same empty population; no row/cell is invented.
                fields = set()
            if 'ParentWhCode' in fields:
                return relation
            rows = self._requirement_parents(rows)
            return _values(rows, dict(SKUCode='text',WhCode='text',**PREPARED_FIELDS['F']))
        raise PublicationUnavailable('bpr_bor_source_unknown:'+str(name))

    def _requirement_parents(self, rows):
        """Project an omitted field from its identical structural producer.

        production_reports.current loops operational_capture's requirement
        bands unchanged. Their parent is copied by planning.projections from
        the generated foundation hierarchy. r1_master_state generates both
        that hierarchy and r1_bpr_master.parent_location_code from the same
        importer field; r1_rationed_report copies the latter to ParentWhCode.
        Require the complete identical grain and both accepted parent
        owners, rather than joining on a loose alias or filling missing cells.
        """
        sources = self.view.bpr.sources
        report = sources.rows('reports/bpr/vf_RationedReqReport')
        masters = sources.rows('closing/bpr/BPRMaster')
        def fail():
            raise PublicationUnavailable('bpr_boroa_requirement_parent_producer_differs')
        def index(population, location):
            result = {}
            for row in population:
                if not {'SKUCode',location,'ParentWhCode'} <= set(row):fail()
                pair = (row['SKUCode'],row[location])
                if any(type(value) is not str for value in pair) or pair in result:fail()
                parent = row['ParentWhCode']
                if parent is not None and (type(parent) is not str or len(parent.encode('utf-16-le'))>100):fail()
                result[pair] = parent
            return result
        parents = index(report,'WhCode')
        master_parents = index(masters,'WHCode')
        keys = [(row['SKUCode'],row['WhCode']) for row in rows]
        if (len(set(keys)) != len(keys) or set(keys) != set(parents)
                or any(pair not in master_parents or master_parents[pair] != parent
                       for pair,parent in parents.items())):
            fail()
        return [dict(row,ParentWhCode=parents[pair]) for row,pair in zip(rows,keys,strict=True)]

    def image_query(self, path):
        if path == 'metadata/bpr/ColorSequence':
            from mta.presentation.native_report_colours import query
            return query()
        sources = self.view.bpr.sources
        from mta.presentation.bor_prepared_fields import SOURCES, FIELDS
        from mta.presentation.boroa_contract import SOURCES as OA_SOURCES, PREPARED_FIELDS
        required = set()
        for paths, roster in ((SOURCES, FIELDS), (OA_SOURCES, PREPARED_FIELDS)):
            for owner, source_path in paths.items():
                if source_path == path:
                    required.update(roster[owner])
        # Verify the entire bag and the fields consumed by both stable joins.
        rows = sources.rows(path)
        item = sources.metadata(path)
        fields = {field for field, _, _ in item['fields']}
        if not fields and item['count'] == 0:
            fields = {field for field, _ in phase_state.REGISTRY[item['table']]}
        if not required <= fields or any(not required <= set(row) for row in rows):
            raise PublicationUnavailable('bpr_bor_source_fields_missing:'+path)
        return sources.query(path)

    def attributes(self):
        return {name: self.view.bpr.sources.rows('closing/importer/'+name)
                for name in ('SkuAttributeData','LocationAttributeData')}

    def remarks(self, family):
        from mta.presentation import ancillary_live
        path = ancillary_live.PATHS[family]
        # Only this run's original capture is admitted. Missing is unavailable;
        # a verified zero-row capture is an owned empty population.
        ancillary_live.image_rows(self.run, path, include_live=False)
        return ancillary_live.image_query(self.run, path, include_live=False)

    def configuration(self):
        from mta.presentation.boroa_configuration import CONFIG
        from mta.presentation.boroa_contract import CONFIG_SHA256
        raw = CONFIG.read_bytes()
        if hashlib.sha256(raw).hexdigest() != CONFIG_SHA256:
            raise PublicationUnavailable('BOR_configuration_changed')
        return json.loads(raw)
