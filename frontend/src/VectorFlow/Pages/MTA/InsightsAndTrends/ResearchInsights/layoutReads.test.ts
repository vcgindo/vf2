import { startResearchLayoutReads, applyResearchSavedLayout } from './layoutReads';

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (error: unknown) => void;
    const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
}

const saved = { charts: [{ type: 'bar' }], columns: [{ colId: 'Norm', hide: false }, { colId: 'SKUCode', hide: true }], pivot: true };
const response = (data: any) => ({ data: { data } });

test('starts each read once before either resolves; saved state applies only after base construction', async () => {
    const config = deferred<any>(), layout = deferred<any>();
    const readConfig = jest.fn(() => config.promise), readSaved = jest.fn(() => layout.promise);
    const reads = startResearchLayoutReads(readConfig, readSaved);
    expect(readConfig).toHaveBeenCalledTimes(1);
    expect(readSaved).toHaveBeenCalledTimes(1);
    const applied: any[] = [];
    layout.resolve(response(JSON.stringify(saved)));
    await reads.saved;
    expect(applied).toEqual([]);
    const base = { charts: [], columns: [{ colId: 'SKUCode' }, { colId: 'Norm' }], pivot: false };
    config.resolve(response(base.columns));
    expect((await reads.configuration).data.data).toEqual(base.columns);
    applied.push(base);
    await applyResearchSavedLayout(reads.saved, state => applied.push(state));
    expect(applied).toEqual([base, saved]);
});

test.each(['', []])('empty layout %p leaves base columns untouched', async empty => {
    const reads = startResearchLayoutReads(() => Promise.resolve(response([])), () => Promise.resolve(response(empty)));
    const apply = jest.fn();
    const log = jest.spyOn(console, 'log').mockImplementation(() => {});
    await applyResearchSavedLayout(reads.saved, apply);
    expect(apply).not.toHaveBeenCalled();
    log.mockRestore();
});

test('invalid saved JSON remains an error without applying a partial layout', async () => {
    const reads = startResearchLayoutReads(() => Promise.resolve(response([])), () => Promise.resolve(response('{invalid')));
    const apply = jest.fn();
    await expect(applyResearchSavedLayout(reads.saved, apply)).rejects.toBeInstanceOf(SyntaxError);
    expect(apply).not.toHaveBeenCalled();
});

test('early saved read rejection is retained safely and surfaces when application is attempted', async () => {
    const config = deferred<any>();
    const error = new Error('layout denied');
    const reads = startResearchLayoutReads(() => config.promise, () => Promise.reject(error));
    expect(await reads.saved).toEqual({ ok: false, error });
    config.resolve(response([]));
    await reads.configuration;
    const apply = jest.fn();
    await expect(applyResearchSavedLayout(reads.saved, apply)).rejects.toBe(error);
    expect(apply).not.toHaveBeenCalled();
});

test('configuration failure remains a failure even when saved state succeeds', async () => {
    const error = new Error('configuration denied');
    const reads = startResearchLayoutReads(() => Promise.reject(error), () => Promise.resolve(response(JSON.stringify(saved))));
    await expect(reads.configuration).rejects.toBe(error);
    expect((await reads.saved).ok).toBe(true);
});
