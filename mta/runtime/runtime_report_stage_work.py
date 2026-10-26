"""Private placement files and typed-image plans for the existing publishers.

Nothing here makes a report visible or accepts a phase. The Full/scoped owner
must authenticate its cut and atomically register the returned work. Canonical
candidate, catalogue and encoding primitives are shared with the first release.
"""
from copy import deepcopy
from dataclasses import dataclass
from uuid import uuid4

from mta.application.runtime_report_configuration import configuration,plan
from mta.application.runtime_report_projection import describe
from mta.runtime import runtime_report_candidates as candidates
from mta.runtime import runtime_report_catalogue as catalogue
from mta.runtime import runtime_report_stage_storage as images
from mta.runtime.runtime_report_publication import _archive,_content
from mta.serialization import digest

SCHEMA='fresh-runtime-report-stage-work-v1'


@dataclass(frozen=True)
class StageWork:
    placement: str
    candidate: dict
    source_manifest: dict
    sources: dict
    descriptors: dict
    owner: dict
    catalogue: dict
    previous_digest: str | None
    definitions: tuple
    inputs: dict
    _execution_authority: object = None

    @property
    def candidate_id(self):return self.candidate['candidate_id']


def _definitions(config,placement,names):
    effective=deepcopy(config)
    indexed={row['Id']:row['LastGeneratedFileName'] for row in names}
    if len(indexed)!=len(names) or set(indexed)!={row['Id'] for row in effective['RuntimeReports']}:
        raise ValueError('Explicit complete generated filename state required')
    for row in effective['RuntimeReports']:row['LastGeneratedFileName']=indexed[row['Id']]
    selected=next((row for row in plan(effective,'Full') if row['placement']==placement),None)
    if selected is None or selected['DownloadableUIReportSettings']:
        raise ValueError('Qualified RuntimeReports-only stage required')
    return tuple(selected['RuntimeReports'])


def _source_manifest(candidate_id,placement,sources):
    return images.capture(None,candidate_id=candidate_id,placement=placement,sources=sources,
        row_writer=lambda name,rows:images.describe(candidate_id,name,rows)[0])


def _inputs(definitions,source_manifest,sources,descriptors,owner):
    result={}
    required=set()
    for definition in definitions:
        spec=describe(definition);names=set(spec['sources'].values());required.update(names)
        if not names<=sources.keys() or not names<=descriptors.keys():
            raise ValueError('Required exact stage source absent')
        provenance=dict(schema=SCHEMA,owner=deepcopy(owner),
            query_sha256=spec['query_sha256'],definition_digest=digest(definition),
            images={name:deepcopy(source_manifest['images'][name]) for name in sorted(names)},
            sources={name:deepcopy(descriptors[name]) for name in sorted(names)})
        provenance['digest']=digest(provenance)
        result[definition['Id']]=dict(sources={name:sources[name] for name in sorted(names)},provenance=provenance)
    if required!=set(sources) or required!=set(descriptors):
        raise ValueError('Exact consumed stage source roster required')
    return result


def prepare(*,root,report_configuration,placement,variables,last_generated,
            previous_catalogue,previous_digest,sources,descriptors,owner,
            candidate_id=None,expected_candidate_digest=None):
    """Prepare before final processing; owner is authenticated by the caller.

    A supplied candidate is revalidated against reconstructed sources, complete
    bytes and the catalogue. It never supplies its own authority or row values.
    """
    config=configuration(report_configuration)
    if (placement not in images.PLACEMENTS or type(sources) is not dict
            or type(descriptors) is not dict or type(owner) is not dict or not owner):
        raise ValueError('Explicit authenticated stage arguments required')
    definitions=_definitions(config,placement,last_generated)
    if candidate_id is None:
        if expected_candidate_digest is not None:raise ValueError('Candidate digest without identity')
        candidate_id=str(uuid4());recover=False
    else:
        if expected_candidate_digest is None:raise ValueError('Recovery requires the exact candidate digest')
        recover=True
    source_manifest=_source_manifest(candidate_id,placement,sources)
    inputs=_inputs(definitions,source_manifest,sources,descriptors,owner)
    if recover:
        candidate=candidates.verify(root=root,candidate_id=candidate_id,expected_digest=expected_candidate_digest)
    else:
        candidate=candidates.materialize(root=root,candidate_id=candidate_id,
            report_configuration=config,placement=placement,variables=variables,
            last_generated=last_generated,inputs=inputs,archive_writer=_archive)
    folded=catalogue.validate_candidate(candidate=candidate,report_configuration=config,
        placement=placement,variables=variables,last_generated=last_generated,
        provenance={key:value['provenance'] for key,value in inputs.items()},previous_catalogue=previous_catalogue)
    _content(definitions,inputs,candidate)
    return StageWork(placement,candidate,source_manifest,sources,deepcopy(descriptors),
        deepcopy(owner),folded['catalogue'],previous_digest,definitions,inputs)


def persist_sources(run,work):
    """Atomic registrar only; detects mutation between preparation and commit."""
    if type(work) is not StageWork:raise ValueError('Exact prepared report work required')
    if _source_manifest(work.candidate_id,work.placement,work.sources)!=work.source_manifest:
        raise ValueError('Report stage sources changed after preparation')
    # Recheck every value before the first write. The DB row guards separately
    # require the registrar's actual authenticated run/worker/final transaction.
    actual=images.capture(run,candidate_id=work.candidate_id,placement=work.placement,sources=work.sources)
    if actual!=work.source_manifest:raise ValueError('Persisted report stage differs')
    return actual


def verify(work,*,root,report_configuration,variables,last_generated,previous_catalogue,
           previous_digest,owner):
    """Reconstruct work using caller-authenticated owner and prior catalogue."""
    if type(work) is not StageWork or work.previous_digest!=previous_digest or work.owner!=owner:
        raise ValueError('Report work owner or catalogue parent changed')
    checked=prepare(root=root,report_configuration=report_configuration,placement=work.placement,
        variables=variables,last_generated=last_generated,previous_catalogue=previous_catalogue,
        previous_digest=previous_digest,sources=work.sources,descriptors=work.descriptors,owner=owner,
        candidate_id=work.candidate_id,expected_candidate_digest=work.candidate['digest'])
    if (checked.source_manifest!=work.source_manifest or checked.catalogue!=work.catalogue
            or checked.candidate!=work.candidate):
        raise ValueError('Prepared report source/candidate/catalogue changed')
    return checked
