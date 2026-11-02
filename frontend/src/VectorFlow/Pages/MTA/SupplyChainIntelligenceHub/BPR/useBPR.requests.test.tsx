// BPR-only loading-sequence regression checks. MTO and shared controls stay unchanged.
// DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
// The user explicitly authorized this narrow BPR loading-sequence correction.
import { act, renderHook } from '@testing-library/react';
import useBPR from './useBPR';
import { notifyError } from '../../../../../helpers/notify';

const mockConfig = jest.fn();
const mockState = jest.fn();
const mockCount = jest.fn();
const mockRows = jest.fn();
const mockSubmit = jest.fn();
const mockDispatch = jest.fn();
jest.mock('../../../../Services/MTA/Common/UIConfig', () => ({ useGetUIConfigData: () => ({ mutateAsync: mockConfig, isLoading: false }) }));
jest.mock('../../../../Services/MTA/Common/UserUIConfig', () => ({ useGetState: () => ({ mutateAsync: mockState, isLoading: false }) }));
jest.mock('../../../../Services/MTA/SupplyChainIntelligenceHub/BPR', () => ({
    useGetBPRData: () => ({ mutateAsync: mockRows, isLoading: false }),
    useGetBPRDataCount: () => ({ mutateAsync: mockCount, isLoading: false }),
    useSubmitBPRRemark: () => ({ mutateAsync: mockSubmit }),
    useGetBPRRemarkHistory: () => ({ mutateAsync: jest.fn() }),
    useGetDailyData: () => ({ mutateAsync: jest.fn() })
}));
jest.mock('../../../../../context', () => ({ useUserData: () => ({ user: { user: { theme_ui: 'NOIRFUSION' } } }) }));
jest.mock('react-redux', () => ({ useDispatch: () => mockDispatch, useSelector: (select: any) => select({ mta: { EnvConfig: { BPR_ROWS_PER_PAGE: '50' }, dailyData: {} } }) }));
jest.mock('../../../../../hooks/useViewPort', () => () => ({ getGridZoom: jest.fn(), getScreenZoomValue: jest.fn() }));
jest.mock('../../../../../hooks/useGetLastRunData', () => () => ({ date: '2026-10-19' }));
jest.mock('../../../../../hooks/useBPRFilter', () => () => ({ state: {}, setState: jest.fn(), onDelete: jest.fn() }));
jest.mock('../../../../../helpers/utils', () => ({
    mapBPRRowData: (rows: any) => rows,
    convertUiConfigToOptions: () => [],
    getColumnDefinationsMTA: () => [{ colId: 'SKUCode' }]
}));
jest.mock('../../../../../helpers/notify', () => ({ notifyError: jest.fn(), notifyLoader: jest.fn(), notifySuccess: jest.fn() }));
jest.mock('react-toastify', () => ({ toast: { dismiss: jest.fn() } }));
jest.mock('./BPRGraphCellRenderer', () => () => null);
jest.mock('./BPRCellRenderers', () => ({}));

const deferred = () => {
    let resolve: (value: any) => void = () => {};
    let reject: (reason: any) => void = () => {};
    const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
};
beforeEach(() => {
    jest.clearAllMocks();
    mockConfig.mockResolvedValue({ data: { data: [] } });
    mockState.mockResolvedValue({ data: { data: '' } });
    mockCount.mockResolvedValue({ data: { recordCount: 1 } });
    mockRows.mockResolvedValue({ data: { data: [{ SKUCode: '001', WHCode: 'DP01' }] } });
    mockSubmit.mockResolvedValue({ status: 200, data: { msg: 'Saved' } });
});

test('opening BPR leaves the filter unblocked and makes no report/layout requests', () => {
    const { result } = renderHook(useBPR);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isSavedDataLoading).toBe(false);
    for (const request of [mockConfig, mockState, mockCount, mockRows]) expect(request).not.toHaveBeenCalled();
});

test('first confirmation loads once, stays busy through saved layout and preserves it on later filters', async () => {
    const config = deferred(), saved = deferred();
    mockConfig.mockReturnValue(config.promise);
    mockState.mockReturnValue(saved.promise);
    const { result } = renderHook(useBPR);
    const filter = { productFilter: { filters: [{ value: '001' }] } };
    await act(async () => { result.current.onApplyFilter(filter); });
    expect(result.current.isLoading).toBe(true);
    expect(mockConfig).toHaveBeenCalledTimes(1);
    expect(mockState).not.toHaveBeenCalled();
    expect(mockRows).toHaveBeenCalledTimes(1);
    expect(mockCount).toHaveBeenCalledTimes(1);
    expect(mockRows.mock.calls[0][0]).toMatchObject({ filters: filter, paginationParameter: { pageNumber: 1, recordsPerPage: 50 } });
    await act(async () => { config.resolve({ data: { data: [] } }); });
    expect(result.current.isLoading).toBe(true);
    expect(mockState).toHaveBeenCalledTimes(1);
    const layout = { charts: [], columns: [{ colId: 'SKUCode', width: 123 }], pivot: false };
    await act(async () => { saved.resolve({ data: { data: JSON.stringify(layout) } }); });
    expect(result.current.isLoading).toBe(false);
    expect(result.current.gridState).toEqual(layout);
    await act(async () => { result.current.onApplyFilter({}); });
    expect(mockConfig).toHaveBeenCalledTimes(1);
    expect(mockState).toHaveBeenCalledTimes(1);
    expect(mockRows).toHaveBeenCalledTimes(2);
    expect(mockCount).toHaveBeenCalledTimes(2);
    expect(result.current.gridState).toEqual(layout);
});

test('two confirmations while setup is pending share the same layout initialization', async () => {
    const config = deferred();
    mockConfig.mockReturnValue(config.promise);
    const { result } = renderHook(useBPR);
    await act(async () => { result.current.onApplyFilter({}); result.current.onApplyFilter({}); });
    expect(mockConfig).toHaveBeenCalledTimes(1);
    await act(async () => { config.resolve({ data: { data: [] } }); });
    expect(mockState).toHaveBeenCalledTimes(1);
    expect(result.current.isLoading).toBe(false);
});

test.each(['columns', 'saved layout'])('failed %s setup releases loading and permits retry on confirmation', async (stage) => {
    if (stage === 'columns') mockConfig.mockRejectedValueOnce(new Error('failed columns'));
    else mockState.mockRejectedValueOnce(new Error('failed layout'));
    const { result } = renderHook(useBPR);
    await act(async () => { result.current.onApplyFilter({}); });
    expect(result.current.isLoading).toBe(false);
    expect(notifyError).toHaveBeenCalledTimes(1);
    await act(async () => { result.current.onApplyFilter({}); });
    expect(mockConfig).toHaveBeenCalledTimes(2);
    expect(result.current.BPRColumns).toEqual([{ colId: 'SKUCode' }]);
    expect(result.current.isLoading).toBe(false);
});

test('leaving while columns load does not start a saved-layout request', async () => {
    const config = deferred();
    mockConfig.mockReturnValue(config.promise);
    const { result, unmount } = renderHook(useBPR);
    await act(async () => { result.current.onApplyFilter({}); });
    unmount();
    await act(async () => { config.resolve({ data: { data: [] } }); });
    expect(mockState).not.toHaveBeenCalled();
});

test('a late old filter pair cannot overwrite a newer report pair', async () => {
    const oldRows = deferred(), oldCount = deferred();
    mockRows.mockReturnValueOnce(oldRows.promise).mockResolvedValue({ data: { data: [{ SKUCode: 'new' }] } });
    mockCount.mockReturnValueOnce(oldCount.promise).mockResolvedValue({ data: { recordCount: 2 } });
    const { result } = renderHook(useBPR);
    await act(async () => { result.current.onApplyFilter({ selected: 'old' }); });
    await act(async () => { result.current.onApplyFilter({ selected: 'new' }); });
    expect(result.current.BPRRowData).toEqual([{ SKUCode: 'new' }]);
    await act(async () => {
        oldRows.resolve({ data: { data: [{ SKUCode: 'old' }] } });
        oldCount.resolve({ data: { recordCount: 99 } });
    });
    expect(result.current.BPRRowData).toEqual([{ SKUCode: 'new' }]);
    expect(result.current.recordCount).toBe(2);
});

test('successful remarks refetch the current count and rows once without replaying the write', async () => {
    const { result } = renderHook(useBPR);
    await act(async () => { result.current.onApplyFilter({}); });
    act(() => { result.current.agGridProps.onCellValueChanged?.({ data: { SKUCode: '001', WHCode: 'DP01', remarks: 'Saved remark' } } as any); });
    mockRows.mockResolvedValueOnce({ data: { data: [{ SKUCode: '001', Remark: 'Saved remark' }] } });
    await act(async () => { await result.current.onSubmitRemarks(); });
    expect(mockSubmit).toHaveBeenCalledTimes(1);
    expect(mockRows).toHaveBeenCalledTimes(2);
    expect(mockCount).toHaveBeenCalledTimes(2);
    expect(mockRows.mock.calls[1][0]).toMatchObject({ filters: {}, paginationParameter: { pageNumber: 1 } });
    expect(result.current.BPRRowData).toEqual([{ SKUCode: '001', Remark: 'Saved remark' }]);
});

test('failed refresh clears the related pair and existing filter confirmation retries reads only', async () => {
    const { result } = renderHook(useBPR);
    mockCount.mockRejectedValueOnce(new Error('publication changed'));
    await act(async () => { result.current.onApplyFilter({}); });
    expect(result.current.BPRRowData).toEqual([]);
    expect(result.current.recordCount).toBeUndefined();
    await act(async () => { result.current.onApplyFilter({}); });
    expect(result.current.BPRRowData).toEqual([{ SKUCode: '001', WHCode: 'DP01' }]);
    expect(mockSubmit).not.toHaveBeenCalled();
});
