import React from 'react';
import { act, renderHook } from '@testing-library/react';
import useBTR from './useBTR';

const mockGrid = jest.fn();
const mockCount = jest.fn();
const mockConfig = jest.fn();
const mockState = jest.fn();
const mockDaily = jest.fn();
const mockDispatch = jest.fn();
let mockDate: string | undefined = '2026-04-07';
jest.mock('../../../../Services/MTA/InsightsAndTrends/BTR', () => ({
    useGetBTRData: () => ({ mutateAsync: mockGrid }),
    useGetBTRDataCount: () => ({ mutateAsync: mockCount })
}));
jest.mock('../../../../Services/MTA/Common/UIConfig', () => ({ useGetUIConfigData: () => ({ mutateAsync: mockConfig, isLoading: false }) }));
jest.mock('../../../../Services/MTA/Common/UserUIConfig', () => ({ useGetState: () => ({ mutateAsync: mockState, isLoading: false }) }));
jest.mock('../../../../Services/MTA/SupplyChainIntelligenceHub/BPR', () => ({ useGetDailyData: () => ({ mutateAsync: mockDaily }) }));
jest.mock('../../../../../context', () => ({ useUserData: () => ({ user: { user: { id: 1, email: 'test@local', theme_ui: 'NOIRFUSION' } } }) }));
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
