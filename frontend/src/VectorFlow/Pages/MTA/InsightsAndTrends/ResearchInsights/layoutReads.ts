type SavedLayoutResult = { ok: true; response: any } | { ok: false; error: unknown };

// Research's reads are independent; applying saved state still waits for base columns.
export function startResearchLayoutReads(readConfig: () => Promise<any>, readSaved: () => Promise<any>) {
    const configuration = readConfig();
    const saved: Promise<SavedLayoutResult> = readSaved().then(
        response => ({ ok: true, response }),
        error => ({ ok: false, error })
    );
    return { configuration, saved };
}

export async function applyResearchSavedLayout(saved: Promise<SavedLayoutResult>, apply: (state: any) => void) {
    const result = await saved;
    if (result.ok === false) throw result.error;
    const stateData = result.response;
    if (stateData.data.data.length !== 0) {
        const parsedContent = JSON.parse(stateData.data.data);
        apply({ charts: parsedContent.charts, columns: parsedContent.columns, pivot: parsedContent.pivot });
    } else {
        console.log('Data not available');
    }
}
