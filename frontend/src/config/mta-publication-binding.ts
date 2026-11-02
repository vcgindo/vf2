/** Transport only: one publication/revision per coordinated report refresh. */
import axios from 'axios';
export const PUBLICATION_HEADER = 'X-VectorFLOW-Publication';
export const PUBLICATION_DATE_HEADER = 'X-VectorFLOW-Publication-Date';
export const PUBLICATION_BOOTSTRAP = '/api/mta/PublicationBinding';

const reportNames = new Set(`GetOrderAllocationReportData GetOrderAllocationReportDataCount
GetLastRunDate
GetElephantOrderData GetElephantOrderDataCount GetBPRData GetBPRDataCount
GetAnalyticsData GetExportDataAsync GetRemarkDetails GetPlanningDataGrid
GetPlanningDataCount GetPlanningDataGraph GetPlanningDataGridCount GetPlanningDataCustom
GetInTransitWhereAboutsData GetInTransitWhereAboutsDataCount GetTransporterDetails
GetRemarkDetailsForInTransit GetOpenExpediteRequest GetRemarkDetailsForExpedite
GetResearchInsightData GetHistroricalAvailabilityBPRData GetBTRData GetBTRDataCount
DBMData DBMDataCount RRRData RRRDataCount GetRRROrderAllocationReportData
GetRRRAllocationReportDataCount BORData BORDataCount BORAnalytics
GetBOROrderAllocationReportData GetBOROrderAllocationReportDataCount
getSupplierWiseAllocationReportData getSupplierWiseAllocationReportDataCount
GetBOROARemarkDetails GetBORRemarkDetails DailyDataGraph GetBufferTrendGraphData
DBMNormSuggestionLoc DBMNormSuggestionSKUs DBMNormSuggestionPie DBMNormSuggestionAgeing
ChronicUnavailabilityLoc ChronicUnavailabilitySku ChronicUnavailabilityGridViewData
AvailabilityTrend AvailabilityAgeing ExcessInventorySku ExcessInventoryValue`.split(/\s+/));
const mutationNames = new Set(['DBMApplySelectedNorms', 'DBMUpdateSleepTbl', 'AddRemark',
  'AddBORRemark', 'AddBOROARemark', 'SubmitRemarksForInTransit', 'AddRemarkForExpedite', 'SubmitOpenExpediteRequest']);

const transportUrl = (config: any): URL => new URL(config.url || '',
  new URL(config.baseURL || '/', window.location.origin || 'http://localhost'));
const reportUrl = (config: any): URL | undefined => {
  const url = transportUrl(config);
  const parts = url.pathname.replace(/\/$/, '').split('/');
  if (parts[1] !== 'api' || parts[2] !== 'mta') return undefined;
  return ((parts.length === 4 && reportNames.has(parts[3])) ||
    (parts.length === 5 && parts[3] === 'DownloadReports')) ? url : undefined;
};

const copyDate = (value: any) => JSON.parse(JSON.stringify(value));
const validateDate = (date: any) => {
  if (date?.status !== 200 || !Array.isArray(date.data) || date.data.length !== 1 ||
      typeof date.data[0]?.formatted !== 'string' || typeof date.data[0]?.rawDate !== 'string' ||
      !/^\d{4}-\d{2}-\d{2}$/.test(date.data[0].rawDate)) {
    throw new Error('Publication date is unavailable. Refresh the report.');
  }
  return date;
};
const dateIdentity = (value: any): string => {
  const canonical = (item: any): any => Array.isArray(item) ? item.map(canonical) :
    item && typeof item === 'object' ? Object.fromEntries(Object.keys(item).sort().map(key => [key, canonical(item[key])])) : item;
  return JSON.stringify(canonical(value));
};

export const createMtaPublicationBinding = (send: (config: any) => Promise<any>) => {
  type Binding = { token: string | null; dateResponse?: any };
  let bootstrap: Promise<Binding> | undefined;
  let pinned: Binding | undefined;
  let capable = false;
  let reportDates = false;
  let epoch = 0;
  const refreshListeners = new Set<() => void>();
  const dateListeners = new Set<(date: any) => void>();
  const refresh = (notify = true, reportReadWillFollow = false) => {
    epoch++; bootstrap = undefined; pinned = undefined;
    if (!notify) capable = false;
    reportDates = notify && reportReadWillFollow && capable;
    if (notify) refreshListeners.forEach(listener => listener());
  };
  const isCurrent = (response: any) => response.config?._mtaPublicationEpoch === undefined ||
    response.config._mtaPublicationEpoch === epoch;
  const pin = (value: Binding) => {
    if (pinned && (pinned.token !== value.token || (pinned.dateResponse !== undefined &&
        value.dateResponse !== undefined && dateIdentity(pinned.dateResponse) !== dateIdentity(value.dateResponse)))) {
      throw new Error('Publication binding changed. Refresh the report.');
    }
    const publishDate = value.dateResponse !== undefined && pinned?.dateResponse === undefined;
    pinned = {token: value.token, dateResponse: pinned?.dateResponse ?? value.dateResponse};
    if (publishDate) dateListeners.forEach(listener => listener(copyDate(pinned!.dateResponse)));
    return pinned;
  };
  const acquire = (url: URL) => {
    if (!bootstrap) {
      const requestedEpoch = epoch;
      bootstrap = send({ method: 'get', url: new URL(PUBLICATION_BOOTSTRAP, url.origin).href })
        .then(response => {
          if (requestedEpoch !== epoch) throw new Error('Report refresh was superseded.');
          const value = response.data;
          if (response.status !== undefined && response.status !== 200) throw new Error('Publication binding is unavailable. Refresh the report.');
          if (value?.mode === 'native' && typeof value.binding === 'string' && /^[a-f0-9]{64}$/.test(value.binding)) {
            const date = value.date_response === undefined ? undefined : validateDate(value.date_response);
            const result = pin({token: value.binding, dateResponse: date});
            capable = value.report_acquisition === true;
            return result;
          }
          if (value?.mode === 'legacy' && value.binding === null) {
            const result = pin({token: null}); capable = false; return result;
          }
          throw new Error('Publication binding is unavailable. Refresh the report.');
        });
      // Failed bootstrap remains failed until an explicit coordinated refresh.
    }
    return bootstrap;
  };
  return {
    async request(config: any) {
      const url = reportUrl(config);
      if (!url) return config;
      if (!isCurrent({ config })) throw new Error('Report refresh was superseded.');
      const requestedEpoch = epoch;
      config._mtaPublicationEpoch = requestedEpoch;
      const previous = config._mtaPublicationBinding || config.headers?.[PUBLICATION_HEADER];
      const ordinaryRead = !url.pathname.includes('/DownloadReports/') &&
        !['GetLastRunDate', 'GetExportDataAsync'].includes(url.pathname.split('/').pop() || '') &&
        ['get', 'post'].includes((config.method || 'get').toLowerCase());
      if (reportDates && ordinaryRead && !pinned && (!previous || previous === 'acquire')) {
        config.headers = {...config.headers, [PUBLICATION_HEADER]: 'acquire'};
        config._mtaPublicationAcquire = true;
        return config;
      }
      const { token, dateResponse } = pinned ?? await acquire(url);
      if (requestedEpoch !== epoch) throw new Error('Report refresh was superseded.');
      if (token) {
        if (previous && previous !== 'acquire' && previous !== token) throw new Error('Publication binding changed. Refresh the report.');
        config.headers = { ...config.headers, [PUBLICATION_HEADER]: token };
        config._mtaPublicationBinding = token;
        config._mtaPublicationAcquire = false;
        if (url.pathname === '/api/mta/GetLastRunDate' &&
            (config.method || 'get').toLowerCase() === 'get' && dateResponse !== undefined) {
          config.adapter = async (actualConfig: any) => ({
            config: actualConfig, status: 200, statusText: 'OK',
            headers: { [PUBLICATION_HEADER.toLowerCase()]: token }, data: copyDate(dateResponse),
          });
        }
      }
      return config;
    },
    response(response: any) {
      if (!isCurrent(response)) throw new Error('Report refresh was superseded.');
      const expected = response.config?._mtaPublicationBinding;
      const actual = response.headers?.[PUBLICATION_HEADER.toLowerCase()];
      if (response.config?._mtaPublicationAcquire) {
        if (response.status !== 200 || (response.data?.status || 200) >= 400 || typeof actual !== 'string' || !/^[a-f0-9]{64}$/.test(actual)) {
          throw new Error('Publication response is missing or stale. Refresh the report.');
        }
        let date;
        try { date = validateDate(JSON.parse(response.headers?.[PUBLICATION_DATE_HEADER.toLowerCase()])); }
        catch { throw new Error('Publication date is unavailable. Refresh the report.'); }
        pin({token: actual, dateResponse: date});
        response.config._mtaPublicationBinding = actual;
        response.config.headers = {...response.config.headers, [PUBLICATION_HEADER]: actual};
        response.config._mtaPublicationAcquire = false;
      } else if (expected && actual !== expected) {
        throw new Error('Publication response is missing or stale. Refresh the report.');
      }
      const parts = transportUrl(response.config || {}).pathname.split('/');
      if (parts[1] === 'api' && parts[2] === 'mta' && mutationNames.has(parts[3]) &&
          response.status >= 200 && response.status < 300 && (response.data?.status || 200) < 400) refresh();
      return response;
    },
    refresh,
    dateFromReports: () => reportDates,
    subscribeDate(listener: (date: any) => void) {
      dateListeners.add(listener);
      return () => { dateListeners.delete(listener); };
    },
    subscribeRefresh(listener: () => void) {
      refreshListeners.add(listener);
      return () => { refreshListeners.delete(listener); };
    },
    isCurrent,
  };
};

export const mtaPublicationBinding = createMtaPublicationBinding(config => axios(config));
export const refreshMtaReportBinding = () => mtaPublicationBinding.refresh(true, true);
export const resetMtaReportBinding = () => mtaPublicationBinding.refresh(false);
export const subscribeMtaReportRefresh = (listener: () => void) => mtaPublicationBinding.subscribeRefresh(listener);
export const subscribeMtaPublicationDate = (listener: (date: any) => void) => mtaPublicationBinding.subscribeDate(listener);
export const mtaDateFromReports = () => mtaPublicationBinding.dateFromReports();
export const isMtaReportCurrent = (response: any) => mtaPublicationBinding.isCurrent(response);
