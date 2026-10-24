"""Finite native consumers captured while the live BPR calculation is owned.

These are canonical consumer populations, not a reconstruction of every R1
diagnostic capability. The full calculation digest retains that provenance.
Persistence and stage acceptance belong to the scoped transaction owner.
"""
from dataclasses import dataclass

from mta.serialization import digest


@dataclass(frozen=True)
class CalculationSources:
    calculation_digest: str
    pick_bands: list
    routes: list
    operational: dict | None
    production_reports: dict | None


def capture_bpr(phase, opening):
    """Capture the real BPR phase without running DBM/BTR or fabricating a day.

    The narrow mapping supplies only the existing report producers' arguments;
    it is never passed to a full-day writer, validator or publication reader.
    """
    if not phase.context.native_daily:
        raise ValueError('Scoped calculation sources require a native BPR phase')
    output = dict(
        _ReportBoundary='fresh-operational-report-boundary-v3',
        CalculationOutputs=[dict(capability=name, rows=rows)
                            for name, rows in phase.calculated.items()],
        ClosingState=[dict(bpr=dict(BPRMaster=phase.bpr_master),
                           orders=phase.order_state, complete=phase.complete)],
        BPRFinal=[phase.late])
    return capture(output, phase.context.profile, opening)


def capture(output, profile, opening):
    """Transfer only the values consumed after the native BPR boundary.

    Keep the original producers and their errors, NULLs, duplicates and order.
    Missing opt-ins remain absent; an enabled consumer must have its actual
    complete capability, including an explicitly produced empty population.
    """
    if output.get('_ReportBoundary') != 'fresh-operational-report-boundary-v3':
        raise ValueError('Scoped calculation sources require the native report boundary')
    from mta.presentation.pick_storage import selected_bands
    from mta.presentation.fulfillment import routes_for_orders
    from mta.application.operational_capture import CAPTURE_POLICY, capture_rows

    calculated = output['CalculationOutputs']
    calculation_digest = digest(calculated)
    bands = selected_bands(calculated)
    routes = routes_for_orders(calculated, output['ClosingState'][0]['orders']['SpikeOrderData'])
    policy = profile.get('operational_sources')
    if policy is not None and policy != CAPTURE_POLICY:
        raise ValueError('Unsupported operational source capture policy')
    operational = capture_rows(calculated) if policy is not None else None
    reports = None
    if 'production_report_policy' in opening:
        from mta.presentation.production_reports import current
        reports = current(output, opening)
    return CalculationSources(calculation_digest, bands, routes, operational, reports)
