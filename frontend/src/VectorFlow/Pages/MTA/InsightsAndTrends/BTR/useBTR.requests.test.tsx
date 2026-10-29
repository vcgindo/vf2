import React from 'react';
import { act, renderHook } from '@testing-library/react';
import useBTR from './useBTR';
import { notifyError } from '../../../../../helpers/notify';

const mockGrid = jest.fn();
const mockCount = jest.fn();
const mockConfig = jest.fn();
const mockState = jest.fn();
const mockDaily = jest.fn();
const mockDispatch = jest.fn();
let mockDate: string | undefined = '2026-04-07';
let mockActor = 1;
jest.mock('../../../../Services/MTA/InsightsAndTrends/BTR', () => ({
    useGetBTRData: () => ({ mutateAsync: mockGrid }),
    useGetBTRDataCount: () => ({ mutateAsync: mockCount })
}));
jest.mock('../../../../Services/MTA/Common/UIConfig', () => ({ useGetUIConfigData: () => ({ mutateAsync: mockConfig, isLoading: false }) }));
jest.mock('../../../../Services/MTA/Common/UserUIConfig', () => ({ useGetState: () => ({ mutateAsync: mockState, isLoading: false }) }));
jest.mock('../../../../Services/MTA/SupplyChainIntelligenceHub/BPR', () => ({ useGetDailyData: () => ({ mutateAsync: mockDaily }) }));
jest.mock('../../../../../context', () => ({ useUserData: () => ({ user: { user: { id: mockActor, email: 'test@local', theme_ui: 'NOIRFUSION' } } }) }));
jest.mock('react-redux', () => ({ useDispatch: () => mockDispatch, useSelector: (select: any) => select({ mta: { EnvConfig: { BTR_ROWS_PER_PAGE: '5000' } } }) }));
jest.mock('../../../../../hooks/useGetLastRunData', () => () => ({ date: mockDate }));
jest.mock('../../../../../hooks/useBPRFilter', () => () => ({ state: { availabilityFilter: { filters: [] } }, setState: jest.fn(), onDelete: jest.fn() }));
jest.mock('../../../../../helpers/utils', () => ({
    mapBTRRowData: (rows: any) => rows,
    getColumnDefinationsMTA: () => [{ field: 'SKUCode', colId: 'SKUCode' }],
    MainMenuItemsCustomization: jest.fn()
}));
jest.mock('../../../../../helpers/notify', () => ({ notifyError: jest.fn(), notifyLoader: jest.fn(), notifySuccess: jest.fn() }));
jest.mock('react-toastify', () => ({ toast: { dismiss: jest.fn() } }));
jest.mock('./CustomVFTable', () => () => null);
jest.mock('./HorizontalSplitView', () => () => null);
jest.mock('./VerticalSplitView', () => () => null);
jest.mock('../../../../../VectorFlow/Pages/MTO/Common/VFPagination', () => () => null);

const deferred = () => {
    let resolve: (value: any) => void = () => {};
    let reject: (value: any) => void = () => {};
    const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
};
const response = (id: string) => ({ data: { data: { displayPrepared: true, tech: [{ SKUCode: id }], eco: [{ SKUCode: id }], labels: [{}] } } });
const rowData = (node: any): any => {
    if (!node) return undefined;
    if (node.props?.rowData) return node.props.rowData;
    for (const child of React.Children.toArray(node.props?.children)) {
        const value = rowData(child);
        if (value) return value;
    }
};
beforeEach(() => {
    jest.clearAllMocks();
    mockDate = '2026-04-07';
    mockActor = 1;
    mockConfig.mockResolvedValue({ data: { data: [] } });
    mockState.mockResolvedValue({ data: { data: '' } });
    mockCount.mockResolvedValue({ data: { data: { TechCount: '97299', EcoCount: '97299' } } });
});
test('late responses cannot replace newer rows/counts or clear their loading state; config is reused', async () => {
    const old = deferred(), recent = deferred(), oldCount = deferred(), recentCount = deferred();
    mockGrid.mockReturnValueOnce(old.promise).mockReturnValueOnce(recent.promise);
    mockCount.mockReturnValueOnce(oldCount.promise).mockReturnValueOnce(recentCount.promise);
    const { result } = renderHook(useBTR);
    await act(async () => { result.current.onApplyFilter({ availabilityFilter: { filters: [] } } as any); });
    await act(async () => { result.current.onApplyFilter({ availabilityFilter: { filters: [] } } as any); });
    expect(mockConfig).toHaveBeenCalledTimes(1);
    await act(async () => { old.resolve(response('old')); oldCount.resolve({ data: { data: { TechCount: '1' } } }); });
    expect(result.current.isLoading).toBe(true);
    expect(rowData(result.current.renderView())).toEqual([]);
    await act(async () => { recent.resolve(response('new')); recentCount.resolve({ data: { data: { TechCount: '97299' } } }); });
    expect(result.current.isLoading).toBe(false);
    expect(rowData(result.current.renderView())).toEqual([{ SKUCode: 'new' }]);
    expect(result.current.techTotalRows).toBe('97299');
    expect(mockGrid.mock.calls[1][0]).toMatchObject({ displayPrepared: true, displayHorizon: 90, paginationParameter: { recordsPerPage: 5000 } });
});
test('a current failed request clears visible rows and releases loading', async () => {
    mockGrid.mockResolvedValueOnce(response('initial')).mockRejectedValueOnce(new Error('failed'));
    const { result } = renderHook(useBTR);
    await act(async () => { result.current.onApplyFilter({ availabilityFilter: { filters: [] } } as any); });
    expect(rowData(result.current.renderView())).toHaveLength(1);
    await act(async () => { result.current.onApplyFilter({ availabilityFilter: { filters: [] } } as any); });
    expect(rowData(result.current.renderView())).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(notifyError).toHaveBeenCalledWith('failed');
});

test('filter replacement aborts obsolete row/count HTTP work without a displayed error', async () => {
    const requests: Array<{ signal: AbortSignal; reject: (error: Error) => void }> = [];
    const network = (payload: any) => new Promise((_resolve, reject) => {
        requests.push({ signal: payload.signal, reject });
        payload.signal.addEventListener('abort', () => reject(new Error('aborted transport')));
    });
    mockGrid.mockImplementation(network);
    mockCount.mockImplementation(network);
    const { result, unmount } = renderHook(useBTR);
    const filter = { availabilityFilter: { filters: [] } } as any;
    await act(async () => { result.current.onApplyFilter(filter); });
    expect(requests).toHaveLength(2);
    await act(async () => { result.current.onApplyFilter(filter); });
    expect(requests.slice(0, 2).every(request => request.signal.aborted)).toBe(true);
    expect(requests.slice(2).every(request => !request.signal.aborted)).toBe(true);
    expect(result.current.isLoading).toBe(true);
    expect(notifyError).not.toHaveBeenCalled();
    await act(async () => { unmount(); });
    expect(requests.every(request => request.signal.aborted)).toBe(true);
    expect(notifyError).not.toHaveBeenCalled();
});

test.each(['actor', 'publication'] as const)('%s replacement cancels active rows and counts', async kind => {
    mockGrid.mockImplementation(() => new Promise(() => {}));
    mockCount.mockImplementation(() => new Promise(() => {}));
    const { result, rerender, unmount } = renderHook(useBTR);
    await act(async () => { result.current.onApplyFilter({ availabilityFilter: { filters: [] } } as any); });
    const oldRows = mockGrid.mock.calls[0][0].signal;
    const oldCount = mockCount.mock.calls[0][0].signal;
    await act(async () => {
        if (kind === 'actor') mockActor = 2;
        else mockDate = '2026-04-08';
        rerender();
    });
    expect(oldRows.aborted).toBe(true);
    expect(oldCount.aborted).toBe(true);
    expect(mockGrid.mock.calls[1][0].signal.aborted).toBe(false);
    expect(mockCount.mock.calls[1][0].signal.aborted).toBe(false);
    unmount();
});

test('independent paging retains the live half of a Both request until both halves are replaced', async () => {
    const combined = deferred(), tech = deferred(), eco = deferred();
    mockGrid.mockResolvedValueOnce(response('initial')).mockReturnValueOnce(combined.promise)
        .mockReturnValueOnce(tech.promise).mockReturnValueOnce(eco.promise);
    const { result, unmount } = renderHook(useBTR);
    await act(async () => { result.current.onApplyFilter({ availabilityFilter: { filters: [] } } as any); });
    await act(async () => { result.current.toggleCurrentTab({ id: '3', value: 'both', label: 'Both' }); });
    expect(mockGrid.mock.calls[1][0].name).toBe('both');
    const shared = mockGrid.mock.calls[1][0].signal;
    await act(async () => { result.current.renderView().props.techTable.paginationProps.handleChangePage(2); });
    expect(shared.aborted).toBe(false);
    await act(async () => { tech.resolve(response('tech-page-2')); combined.resolve(response('shared-page-1')); });
    const view = result.current.renderView();
    expect(view.props.techTable.rowData).toEqual([{ SKUCode: 'tech-page-2' }]);
    expect(view.props.ecoTable.rowData).toEqual([{ SKUCode: 'shared-page-1' }]);
    await act(async () => { result.current.renderView().props.ecoTable.paginationProps.handleChangePage(2); });
    expect(mockGrid.mock.calls[3][0]).toMatchObject({ name: 'eco', paginationParameter: { pageNumber: 2 } });
    unmount();
});

test('a Both transport is aborted when both branches have newer independent requests', async () => {
    mockGrid.mockResolvedValueOnce(response('initial')).mockImplementation(() => new Promise(() => {}));
    const { result, unmount } = renderHook(useBTR);
    await act(async () => { result.current.onApplyFilter({ availabilityFilter: { filters: [] } } as any); });
    await act(async () => { result.current.toggleCurrentTab({ id: '3', value: 'both', label: 'Both' }); });
    const shared = mockGrid.mock.calls[1][0].signal;
    await act(async () => { result.current.renderView().props.techTable.paginationProps.handleChangePage(2); });
    expect(shared.aborted).toBe(false);
    await act(async () => { result.current.renderView().props.ecoTable.paginationProps.handleChangePage(2); });
    expect(shared.aborted).toBe(true);
    expect(mockGrid.mock.calls[2][0].signal.aborted).toBe(false);
    expect(mockGrid.mock.calls[3][0].signal.aborted).toBe(false);
    unmount();
});

test('initial date arrival waits for Apply; a subsequent publication change refreshes an active report', async () => {
    mockDate = undefined;
    mockGrid.mockResolvedValue(response('current'));
    const { result, rerender } = renderHook(useBTR);
    await act(async () => { mockDate = '2026-04-07'; rerender(); });
    expect(mockGrid).not.toHaveBeenCalled();
    await act(async () => { result.current.onApplyFilter({ availabilityFilter: { filters: [] } } as any); });
    await act(async () => { mockDate = '2026-04-08'; rerender(); });
    expect(mockGrid).toHaveBeenCalledTimes(2);
    expect(mockConfig).toHaveBeenCalledTimes(2);
});

test('Reset refreshes column definitions without reloading the saved layout', async () => {
    mockGrid.mockResolvedValue(response('current'));
    const { result } = renderHook(useBTR);
    await act(async () => { result.current.onApplyFilter({ availabilityFilter: { filters: [] } } as any); });
    expect(mockState).toHaveBeenCalledTimes(1);
    await act(async () => { await result.current.onResetCallback(); });
    expect(mockConfig).toHaveBeenCalledTimes(2);
    expect(mockState).toHaveBeenCalledTimes(1);
});
