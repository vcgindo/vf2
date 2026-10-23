import fs from 'fs';
import path from 'path';
import ts from 'typescript';
import { withLoading } from './withLoading';

// Exercise the production callbacks with controlled closure inputs. This keeps
// request failure/empty-state regressions independent of the full app providers.
function callback(file: string, name: string, scope: Record<string, any>) {
  const filename = path.resolve(__dirname, '..', file);
  const source = ts.createSourceFile(filename, fs.readFileSync(filename, 'utf8'), ts.ScriptTarget.Latest, true);
  let body: ts.Node | undefined;
  const visit = (node: ts.Node) => {
    if (ts.isVariableDeclaration(node) && node.name.getText(source) === name) {
      body = node.initializer;
      if (body && ts.isCallExpression(body)) body = body.arguments[0];
    } else if (ts.isFunctionDeclaration(node) && node.name?.text === name) {
      body = node;
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  if (!body) throw new Error(`Missing callback ${file}:${name}`);
  const code = ts.transpileModule(`const handler = ${body.getText(source)};`, {
    compilerOptions: { target: ts.ScriptTarget.ES2018, module: ts.ModuleKind.CommonJS },
  }).outputText;
  return new Function(...Object.keys(scope), `${code}; return handler;`)(...Object.values(scope));
}

const mta = 'VectorFlow/Pages/MTA/MDM/ViewModify/useViewModify.ts';
const mto = 'VectorFlow/Pages/MTO/MDM/ViewModify/useViewModify.ts';

function masterScope(query: () => Promise<any>) {
  const scope: Record<string, any> = {
    activeMaster: { id: 1, filters: [], fields: [], colDefs: [], rowData: [], isMTO: true },
    areMasterFiltersValid: () => true,
    mapStateFiltersToPayload: () => [],
    getCurrentVisbileColumns: () => [],
    queryAllData: query,
    queryFilteredData: query,
    notifyPromise: (promise: Promise<any>) => promise,
    downloadData: false,
    isShowAll: true,
    tempRecordCount: 9,
    rowsPerPage: 50,
    pageType: 'modify',
    setIsShowAll: jest.fn(),
    setDownloadData: jest.fn(),
    setIsTableDataLoading: jest.fn(),
    setTempRecordCount: jest.fn(),
    setCurrentPage: jest.fn(),
    setSeasonalityActiveQuickFilter: jest.fn(),
    toggleWarningModal: jest.fn(),
    toggleEditOnline: jest.fn(),
    notifyError: jest.fn(),
    dispatch: jest.fn(),
    ref: { current: undefined },
    console: { error: jest.fn() },
  };
  for (const name of ['UPDATE_ROW_DATA', 'SET_RECORD_COUNT', 'UPDATE_PROGRESS_STATE',
    'UPDATE_DATA_AVAILABILITY_STATUS', 'SYNC_ACTIVE_MASTER_TO_MASTER', 'RESET_FILTERS']) {
    scope[name] = (payload: any) => ({ type: name, payload });
  }
  return scope;
}

describe.each([['MTA', mta], ['MTO', mto]])('%s master request settlement', (_label, file) => {
  it.each(['handleApplyFilter', 'onWarningModalSuccess', 'handleChangePage'])(
    '%s releases loading on rejection without reporting a false zero count', async (name) => {
      const scope = masterScope(async () => { throw new Error('timeout'); });
      await callback(file, name, scope)(name === 'handleApplyFilter' ? true : 2);
      expect(scope.setIsTableDataLoading.mock.calls).toEqual([[true], [false]]);
      expect(scope.notifyError).toHaveBeenCalled();
      expect(scope.dispatch).not.toHaveBeenCalledWith({ type: 'SET_RECORD_COUNT', payload: 0 });
      expect(scope.setTempRecordCount).not.toHaveBeenCalledWith(0);
      expect(scope.toggleWarningModal).not.toHaveBeenCalledWith(true);
    }
  );

  it.each([0, '0'])('clears stale rows, count, and progress on successful zero count %p', async (count) => {
    const response = file === mta ? { recordCount: count } : { data: { count } };
    const scope = masterScope(async () => ({ status: 200, data: response }));
    await callback(file, 'handleApplyFilter', scope)(true);
    expect(scope.dispatch).toHaveBeenCalledWith({ type: 'UPDATE_ROW_DATA', payload: [] });
    expect(scope.dispatch).toHaveBeenCalledWith({ type: 'SET_RECORD_COUNT', payload: 0 });
    expect(scope.dispatch).toHaveBeenCalledWith({ type: 'UPDATE_PROGRESS_STATE', payload: 'default' });
    expect(scope.toggleWarningModal).toHaveBeenCalledWith(true);
    expect(scope.setIsTableDataLoading).toHaveBeenLastCalledWith(false);
    expect(scope.notifyError).not.toHaveBeenCalled();
  });

  it.each(['', null, undefined, false, true, 'no data', '1.5', '-1', ' 0', '0 ', -1, 1.5, NaN, Infinity, {}])(
    'rejects malformed count %p without presenting an empty result', async (count) => {
      const response = file === mta ? { recordCount: count } : { data: { count } };
      const scope = masterScope(async () => ({ status: 200, data: response }));
      await callback(file, 'handleApplyFilter', scope)(true);
      expect(scope.notifyError).toHaveBeenCalled();
      expect(scope.setTempRecordCount).not.toHaveBeenCalled();
      expect(scope.dispatch).not.toHaveBeenCalledWith({ type: 'UPDATE_ROW_DATA', payload: [] });
      expect(scope.dispatch).not.toHaveBeenCalledWith({ type: 'SET_RECORD_COUNT', payload: 0 });
      expect(scope.toggleWarningModal).not.toHaveBeenCalledWith(true);
      expect(scope.setIsTableDataLoading).toHaveBeenLastCalledWith(false);
    }
  );

  it.each([12, '12'])('accepts successful positive count %p without clearing rows', async (count) => {
    const response = file === mta ? { recordCount: count } : { data: { count } };
    const scope = masterScope(async () => ({ status: 200, data: response }));
    await callback(file, 'handleApplyFilter', scope)(true);
    expect(scope.setTempRecordCount).toHaveBeenCalledWith(12);
    expect(scope.notifyError).not.toHaveBeenCalled();
    expect(scope.dispatch).not.toHaveBeenCalledWith({ type: 'UPDATE_ROW_DATA', payload: [] });
    expect(scope.toggleWarningModal).toHaveBeenCalledWith(true);
    expect(scope.setIsTableDataLoading).toHaveBeenLastCalledWith(false);
  });

  it('clears a previously positive count when the confirmed data is empty', async () => {
    const scope = masterScope(async () => ({ status: 200, data: { data: [] } }));
    await callback(file, 'onWarningModalSuccess', scope)();
    expect(scope.dispatch).toHaveBeenCalledWith({ type: 'UPDATE_ROW_DATA', payload: [] });
    expect(scope.dispatch).toHaveBeenCalledWith({ type: 'SET_RECORD_COUNT', payload: 0 });
    expect(scope.dispatch).toHaveBeenCalledWith({ type: 'UPDATE_PROGRESS_STATE', payload: 'default' });
    expect(scope.toggleWarningModal).toHaveBeenCalledWith(true);
    expect(scope.setIsTableDataLoading).toHaveBeenLastCalledWith(false);
    expect(scope.notifyError).not.toHaveBeenCalled();
  });

  it('treats a resolved form-error response as an error, preserving the transport contract', async () => {
    const scope = masterScope(async () => ({ status: 400, response: { msg: 'denied' } }));
    await callback(file, 'handleApplyFilter', scope)(true);
    expect(scope.notifyError).toHaveBeenCalled();
    expect(scope.setTempRecordCount).not.toHaveBeenCalledWith(0);
    expect(scope.toggleWarningModal).not.toHaveBeenCalledWith(true);
    expect(scope.setIsTableDataLoading).toHaveBeenLastCalledWith(false);
  });
});

it.each([{ data: [] }, { data: [{ id: 'fixture' }] }])('uses MTO array response length for the retained count contract: %p', async ({ data }) => {
  const scope = masterScope(async () => ({ status: 200, data: { data } }));
  await callback(mto, 'handleApplyFilter', scope)(true);
  expect(scope.setTempRecordCount).toHaveBeenCalledWith(data.length);
  expect(scope.notifyError).not.toHaveBeenCalled();
  expect(scope.setIsTableDataLoading).toHaveBeenLastCalledWith(false);
});

it.each([{ length: 0 }, { count: '', length: 0 }, { error: 'denied', length: 0 }])(
  'does not substitute an object length for a malformed MTO count: %p', async (data) => {
    const scope = masterScope(async () => ({ status: 200, data: { data } }));
    await callback(mto, 'handleApplyFilter', scope)(true);
    expect(scope.notifyError).toHaveBeenCalled();
    expect(scope.setTempRecordCount).not.toHaveBeenCalled();
    expect(scope.toggleWarningModal).not.toHaveBeenCalledWith(true);
    expect(scope.setIsTableDataLoading).toHaveBeenLastCalledWith(false);
  }
);

it.each([
  ['components/layouts/ProductFilter/common-filter.tsx', 'initProductFilter', 'MainService', 'getProductFilter', 'setProductFilterLoading'],
  ['components/layouts/LocationFilter/common-filter.tsx', 'initLocationFilter', 'ISTService', 'getLocationFilterList', 'setLocationFilterLoading'],
  ['module-store-transfer/pages/availability-comparison/product-filter.tsx', 'initProductFilter', 'AvailabilityComparisonService', 'getListProductFilter', 'setProductFilterLoading'],
])('%s releases its filter spinner on failure', async (file, name, service, method, setter) => {
  const setLoading = jest.fn();
  const notifyError = jest.fn();
  const scope = {
    [service]: { [method]: async () => { throw new Error('offline'); } },
    [setter]: setLoading,
    notifyError,
    props: { endpoint: { lcFilterList: 'filter' } },
  };
  await callback(file, name, scope)();
  expect(setLoading.mock.calls).toEqual([[true], [false]]);
  expect(notifyError).toHaveBeenCalled();
});

it.each([
  ['components/layouts/ProductFilter/common-filter.tsx', 'initProductFilter', 'MainService', 'getProductFilter', 'setProductFilterLoading'],
  ['components/layouts/LocationFilter/common-filter.tsx', 'initLocationFilter', 'ISTService', 'getLocationFilterList', 'setLocationFilterLoading'],
  ['module-store-transfer/pages/availability-comparison/product-filter.tsx', 'initProductFilter', 'AvailabilityComparisonService', 'getListProductFilter', 'setProductFilterLoading'],
])('%s treats a resolved denied response as a filter error', async (file, name, service, method, setter) => {
  const setLoading = jest.fn();
  const notifyError = jest.fn();
  await callback(file, name, {
    [service]: { [method]: async () => ({ status: 403 }) }, [setter]: setLoading,
    notifyError, props: { endpoint: { lcFilterList: 'filter' } },
  })();
  expect(setLoading.mock.calls).toEqual([[true], [false]]);
  expect(notifyError).toHaveBeenCalled();
});

it('selecting report rows does not start an unrelated data-loading spinner', () => {
  const setIsGridLoading = jest.fn();
  const selectAllFiltered = jest.fn();
  callback('VectorFlow/Pages/MTO/Production/OverallBMReport/index.tsx', 'onCheckBoxToggle', {
    setIsGridLoading, setIsCheckboxChecked: jest.fn(),
    refGraph2: { current: { api: { selectAllFiltered } } },
  })({ target: { checked: true } });
  expect(selectAllFiltered).toHaveBeenCalledTimes(1);
  expect(setIsGridLoading).not.toHaveBeenCalled();
});

it('releases the quotation spinner when master loading fails', async () => {
  const setLoading = jest.fn();
  const notifyError = jest.fn();
  await callback('VectorFlow/Pages/MTO/Production/DueDateQuotation/index.tsx', 'getMastersData', {
    setLoading, notifyError, console: { error: jest.fn() },
    getBufferMaster: async () => { throw new Error('offline'); },
  })();
  expect(setLoading.mock.calls).toEqual([[true], [false]]);
  expect(notifyError).toHaveBeenCalled();
});

it('releases simulation loading on rejection without retrying the action', async () => {
  const setIsOverlayLoading = jest.fn();
  const request = jest.fn(async () => { throw new Error('timeout'); });
  const notifyError = jest.fn();
  const navigate = jest.fn();
  await callback('VectorFlow/Pages/MTO/Procurement/Planning/useProcPlanning.tsx', 'navigateToSimulateScreen', {
    user: { user: { name: 'fixture' } }, ShortageDatas: [],
    setIsOverlayLoading, UpdateProcurementSimulationData: request,
    notifyError, navigate, console: { error: jest.fn() },
  })();
  expect(setIsOverlayLoading.mock.calls).toEqual([[true], [false]]);
  expect(request).toHaveBeenCalledTimes(1);
  expect(notifyError).toHaveBeenCalled();
  expect(navigate).not.toHaveBeenCalled();
});

it('releases both menu download indicators when the download rejects', async () => {
  const setIsLoading = jest.fn();
  const notifyError = jest.fn();
  let urls: string[] = [];
  await callback('components/commons/MenuToolTip/index.tsx', 'handleTooltipClick', {
    reportUrls: ['report'], withLoading, setIsLoading, notifyError,
    setTempUrls: (update: (value: string[]) => string[]) => { urls = update(urls); },
    handleDownloadMTOVF: async () => { throw new Error('timeout'); },
  })('report', true, 'report.zip');
  expect(setIsLoading.mock.calls).toEqual([[true], [false]]);
  expect(urls).toEqual([]);
  expect(notifyError).toHaveBeenCalled();
});

it('keeps both menu indicators active for overlapping downloads of the same report', async () => {
  const setIsLoading = jest.fn();
  let urls: string[] = [];
  let finishFirst!: () => void;
  let finishSecond!: () => void;
  const first = new Promise<void>((done) => { finishFirst = done; });
  const second = new Promise<void>((done) => { finishSecond = done; });
  const handler = callback('components/commons/MenuToolTip/index.tsx', 'handleTooltipClick', {
    reportUrls: ['report'], withLoading, setIsLoading, notifyError: jest.fn(),
    setTempUrls: (update: (value: string[]) => string[]) => { urls = update(urls); },
    handleDownloadMTOVF: jest.fn().mockReturnValueOnce(first).mockReturnValueOnce(second),
  });
  const firstLoad = handler('report', true, 'report.zip');
  const secondLoad = handler('report', true, 'report.zip');
  finishFirst();
  await firstLoad;
  expect(urls).toEqual(['report']);
  expect(setIsLoading).not.toHaveBeenCalledWith(false);
  finishSecond();
  await secondLoad;
  expect(urls).toEqual([]);
  expect(setIsLoading).toHaveBeenLastCalledWith(false);
});

it.each([
  ['VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/BPR/useBPR.ts', 'getBPRRowData', 'getBPRData'],
  ['VectorFlow/Pages/MTA/InsightsAndTrends/ResearchInsights/useResearchInsights.tsx', 'getRowData', 'readRowData'],
  ['VectorFlow/Pages/MTA/InsightsAndTrends/GuidedInsights/useGuidedInsights.ts', 'fetchAndUpdateGridData', 'getChronicUnavailabilityGrid'],
  ['VectorFlow/Pages/MTA/DBM/DBMNormSuggestions/useDBM.ts', 'getDBMRowData', 'getDBMData'],
  ['VectorFlow/Pages/MTA/DBM/DBMNormSuggestions/useDBM.ts', 'handleGoButton', 'getDBMApplySelectedNorm'],
  ['VectorFlow/Pages/MTA/DBM/DBMNormSuggestions/useDBM.ts', 'handleGoButtonForSleep', 'getDBMUpdateSleepTbl'],
])('%s:%s releases only its own pending toast on rejection', async (file, name, api) => {
  const dismiss = jest.fn();
  const notifyError = jest.fn();
  const notifySuccess = jest.fn();
  const request = jest.fn(async () => { throw new Error('timeout'); });
  const refetchAfter = jest.fn();
  await callback(file, name, {
    [api]: request, notifyLoader: () => 'owned-toast', toast: { dismiss }, notifyError, notifySuccess,
    userPageSize: 50, BPR_ROWS_PER_PAGE: '50', GUIDEDINSIGHT_ROWS_PER_PAGE: 50,
    recordsPerPage: 50, currentFilter: [], refetchAfter,
    gridRef: { current: { api: { getSelectedRows: () => [{ SKUCode: 'fixture', LocCode: 'fixture' }] } } },
  })([], 1);
  expect(dismiss.mock.calls).toEqual([['owned-toast']]);
  expect(notifyError).toHaveBeenCalled();
  expect(notifySuccess).not.toHaveBeenCalled();
  expect(refetchAfter).not.toHaveBeenCalled();
  expect(request).toHaveBeenCalledTimes(1);
});

it.each(['handleGoButton', 'handleGoButtonForSleep'])('%s releases its toast on the no-selection exit', async (name) => {
  const dismiss = jest.fn();
  await callback('VectorFlow/Pages/MTA/DBM/DBMNormSuggestions/useDBM.ts', name, {
    notifyLoader: () => 'owned-toast', toast: { dismiss }, notifyError: jest.fn(),
    gridRef: { current: { api: { getSelectedRows: () => [] } } },
  })(1);
  expect(dismiss.mock.calls).toEqual([['owned-toast']]);
});

it.each([
  ['handleGoButton', 'getDBMApplySelectedNorm'],
  ['handleGoButtonForSleep', 'getDBMUpdateSleepTbl'],
])('%s does not report a resolved denied response as a successful action', async (name, api) => {
  const notifySuccess = jest.fn();
  const notifyError = jest.fn();
  const refetchAfter = jest.fn();
  const dismiss = jest.fn();
  await callback('VectorFlow/Pages/MTA/DBM/DBMNormSuggestions/useDBM.ts', name, {
    [api]: async () => ({ status: 403 }), notifySuccess, notifyError, refetchAfter,
    notifyLoader: () => 'owned-toast', toast: { dismiss }, recordsPerPage: 50,
    gridRef: { current: { api: { getSelectedRows: () => [{ SKUCode: 'fixture', LocCode: 'fixture' }] } } },
  })(1);
  expect(notifyError).toHaveBeenCalled();
  expect(notifySuccess).not.toHaveBeenCalled();
  expect(refetchAfter).not.toHaveBeenCalled();
  expect(dismiss.mock.calls).toEqual([['owned-toast']]);
});

it('releases the discard toast on failure and preserves the draft', async () => {
  const dismiss = jest.fn();
  const dispatch = jest.fn();
  const notifyError = jest.fn();
  await callback(mta, 'onDiscardDraftCallback', {
    draftId: 'draft', draftID: 'draft', notifyLoader: () => 'discard-toast',
    deleteDraft: async () => { throw new Error('timeout'); },
    toast: { dismiss }, dispatch, notifyError,
  })();
  expect(dismiss.mock.calls).toEqual([['discard-toast']]);
  expect(dispatch).not.toHaveBeenCalled();
  expect(notifyError).toHaveBeenCalled();
});

it('releases the reset-layout toast when the grid has already gone away', async () => {
  const dismiss = jest.fn();
  await callback('hooks/useSaveAllState.ts', 'onResetAllState', {
    notifyLoader: () => 'reset-toast', toast: { dismiss },
    ref: { current: undefined }, isLiveGrid: () => false,
  })('BPR');
  expect(dismiss.mock.calls).toEqual([['reset-toast']]);
});

it('releases availability export selection on rejection', async () => {
  const setSelectedItem = jest.fn();
  const notifyError = jest.fn();
  await callback('components/commons/TabAvailabilityComparison/AvailabilityActiveTab.tsx', 'exportItem', {
    selectedItem: { idx: null }, setSelectedItem, notifyError,
    handleExport: async () => { throw new Error('timeout'); },
  })('row', { before: 'red', after: 'green' });
  expect(setSelectedItem).toHaveBeenLastCalledWith({ idx: null, data: null });
  expect(notifyError).toHaveBeenCalled();
});

it('settles the inverse upload spinner on a resolved non-success status', async () => {
  const setIsloading = jest.fn();
  const notifyError = jest.fn();
  await callback('module-store-transfer/pages/manual-upload/index.tsx', 'handleSubmit', {
    setShowPopup: jest.fn(), isShowPopup: false, fileUpload: new Blob(['fixture']),
    setIsloading, notifyError, setFile: jest.fn(), t: (message: string) => message,
    axios: { post: async () => ({ status: 403 }) },
  })({ preventDefault: jest.fn() });
  expect(setIsloading.mock.calls).toEqual([[false], [true]]);
  expect(notifyError).toHaveBeenCalled();
});
