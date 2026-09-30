/** P4a approved presentation: preserve B1-SOURCE-03, never replace its query. */
export function gitFailureMessage(error: any): string {
    let body = error?.response?.data ?? error?.response;
    if (body?.error === 'Failed to forward request' && typeof body.message === 'string') {
        try { body = JSON.parse(body.message); } catch { body = null; }
    }
    if (body?.error === 'legacy_source_flaw' && body?.source_id === 'B1-SOURCE-03') {
        return 'The legacy child GIT grid is unavailable because its transporter query fails. This request includes both location-wise and transporter-wise results, so neither grid is shown. Return to Chart View or Go Back to select From Parent. No replacement results have been generated.';
    }
    if (body?.error === 'legacy_source_flaw' && body?.packet === 'P4a G1/G2') {
        return 'GIT results are unavailable for the selected filters because the legacy query fails. Reset the filters to return to the working view. No replacement results have been generated.';
    }
    return 'GIT could not be loaded. Retry or change the filters. The previous grid is not a result for this request.';
}
