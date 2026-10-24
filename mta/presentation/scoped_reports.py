"""Finite pre-BTR report rows from accepted BPR sources, before preparation.

No Full output object, terminal receipt or current BTR population is synthesized.
The caller must persist/seal these bags in its own phase generation before use
by native report readers. This module grants no serving/readiness admission.
"""
import inspect

from mta.presentation import excess,fulfillment,expedite,pick_post,rrr,scoped_sources
from mta.serialization import digest,storage

SCHEMA='fresh-bpr-report-rows-v1'


def recipe_digest():
    return digest(dict(schema=SCHEMA,builder=inspect.getsource(produce),
        sources=inspect.getsource(scoped_sources),
        producers={module.__name__:inspect.getsource(module)
                   for module in (excess,fulfillment,expedite,pick_post,rrr)}))


def produce(phase_id,*,expected_digest,action_revision):
    sources=scoped_sources.bind(phase_id,expected_digest=expected_digest,action_revision=action_revision)
    rationed=sources.rows('reports/bpr/vf_RationedReqReport')
    standards=sources.rows('closing/dbm/SKULocStandardAttributes')
    masters=sources.rows('closing/importer/MasterData')
    orders=sources.rows('closing/orders/SpikeOrderData')
    routes=sources.rows('sources/calculation/OrderRoutes')
    bands=sources.rows('sources/calculation/PickBands')
    pick=storage(rrr.pick_rows(rationed,bands))
    today=sources.display_date.isoformat()
    rows=dict(
        ExcessInventoryDetails=excess.produce(rationed,standards,today),
        OrderFulfillmentSummary=fulfillment.produce_summary(rationed,standards),
        OrderFulfillmentDetails=fulfillment.produce_details(orders,routes,standards,today),
        ExpediteDispatches=expedite.produce_before_btr(pick,masters,standards,rationed),
        PickPost=pick_post.produce(pick))
    metadata=dict(schema=SCHEMA,source_digest=sources.source_digest,recipe_digest=recipe_digest(),
        phase_id=str(sources.acceptance_id),phase_digest=sources.acceptance_digest,
        action_revision=action_revision,display_date=today,
        producers=dict(excess=excess.PRODUCER_SHA,fulfillment=fulfillment.PRODUCER_SHA,
                       expedite=expedite.PRODUCER_SHA,pick_post=pick_post.SOURCE_HASHES),
        images={name:dict(count=len(bag),digest=digest(bag)) for name,bag in rows.items()})
    return metadata,rows
