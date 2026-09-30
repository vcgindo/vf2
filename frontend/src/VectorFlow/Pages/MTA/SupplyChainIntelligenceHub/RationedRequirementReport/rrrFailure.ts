/** P2 approved containment: no SQL details, replacement results or false empties. */
export function rrrFailureMessage(error: any): string {
    let body = error?.response?.data ?? error?.response;
    if (typeof body?.message === 'string') {
        try { body = JSON.parse(body.message); } catch { body = null; }
    }
    if (body?.error === 'legacy_source_flaw' && body?.packet === 'P2 R1/R2' && body?.status === 'FAILED_INCOMPARABLE') {
        return 'This filter is unavailable in the legacy RRR implementation. Remove the unsupported filter or reset filters to return to the normal report. No successful result has been produced for this selection.';
    }
    return 'The RRR report could not be loaded. Retry by applying the filters again or reset filters. No successful result has been produced for this selection.';
}
