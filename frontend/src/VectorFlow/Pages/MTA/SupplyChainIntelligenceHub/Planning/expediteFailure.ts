/** P3 approved containment, not replacement results or repaired legacy logic. */
export function expediteFailureMessage(error: any): string {
    let body = error?.response?.data ?? error?.response;
    if (typeof body?.message === 'string') {
        try { body = JSON.parse(body.message); } catch { body = null; }
    }
    if (body?.error === 'legacy_source_flaw' && body?.packet === 'P3 E1/E2' && body?.status === 'FAILED_INCOMPARABLE') {
        return 'This filter is unavailable in the legacy Expedite implementation for this view. Remove the unsupported filter or reset filters. No successful result has been produced for this selection.';
    }
    return 'Expedite could not be loaded. Retry or change the filters. The previous grid is not a result for this request.';
}

export function expediteChartFailureMessage(error: any): string {
    let body = error?.response?.data ?? error?.response;
    if (typeof body?.message === 'string') {
        try { body = JSON.parse(body.message); } catch { body = null; }
    }
    if (typeof body?.error === 'string' && body.error.includes('LEG-EXPEDITE-UNORDERED-LABEL:')) {
        return 'Child Expedite charts are unavailable because the legacy response has ambiguous location labels. Use Grid View to inspect the available rows.';
    }
    return 'Child Expedite charts could not be loaded. Use Grid View, or go back and retry.';
}
