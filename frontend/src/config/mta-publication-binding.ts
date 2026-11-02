/** Transport only: one publication/revision per coordinated report refresh. */
import axios from 'axios';
export const PUBLICATION_HEADER = 'X-VectorFLOW-Publication';
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

export const createMtaPublicationBinding = (send: (config: any) => Promise<any>) => {
  let bootstrap: Promise<{ token: string | null; dateResponse?: any }> | undefined;
  let epoch = 0;
  const refreshListeners = new Set<() => void>();
  const refresh = (notify = true) => {
    epoch++; bootstrap = undefined;
    if (notify) refreshListeners.forEach(listener => listener());
  };
  const isCurrent = (response: any) => response.config?._mtaPublicationEpoch === undefined ||
    response.config._mtaPublicationEpoch === epoch;
  const acquire = (url: URL) => {
    if (!bootstrap) {
      bootstrap = send({ method: 'get', url: new URL(PUBLICATION_BOOTSTRAP, url.origin).href })
        .then(response => {
          const value = response.data;
          if (value?.mode === 'native' && /^[a-f0-9]{64}$/.test(value.binding)) {
            const date = value.date_response;
            // Older matched servers can still use their ordinary date endpoint.
            // A supplied malformed date is unavailable, never a fallback value.
            if (date !== undefined && (date?.status !== 200 || !Array.isArray(date.data) ||
                date.data.length !== 1 || typeof date.data[0]?.formatted !== 'string' ||
                !/^\d{4}-\d{2}-\d{2}$/.test(date.data[0]?.rawDate || ''))) {
              throw new Error('Publication date is unavailable. Refresh the report.');
            }
            return { token: value.binding, dateResponse: date };
          }
          if (value?.mode === 'legacy' && value.binding === null) return { token: null };
          throw new Error('Publication binding is unavailable. Refresh the report.');
        });
      // Retry only at an explicit coordinated refresh; never silently adopt a
      // later publication after companion reads have already started.
    }
    return bootstrap;
  };
  return {
    async request(config: any) {
      const url = reportUrl(config);
      if (!url) return config;
      if (!isCurrent({ config })) throw new Error('Report refresh was superseded.');
      const requestedEpoch = epoch;
      const { token, dateResponse } = await acquire(url);
      if (requestedEpoch !== epoch) throw new Error('Report refresh was superseded.');
      if (token) {
        const previous = config.headers?.[PUBLICATION_HEADER];
        if (previous && previous !== token) throw new Error('Publication binding changed. Refresh the report.');
        config.headers = { ...config.headers, [PUBLICATION_HEADER]: token };
        config._mtaPublicationBinding = token;
        config._mtaPublicationEpoch = epoch;
        if (url.pathname === '/api/mta/GetLastRunDate' &&
            (config.method || 'get').toLowerCase() === 'get' && dateResponse !== undefined) {
          // This is the owner's actual date envelope from the binding snapshot,
          // not a date inferred from the browser or a separately cached release.
          // The normal response interceptor still rejects a superseded epoch.
          config.adapter = async (actualConfig: any) => ({
            config: actualConfig, status: 200, statusText: 'OK',
            headers: { [PUBLICATION_HEADER.toLowerCase()]: token },
            data: JSON.parse(JSON.stringify(dateResponse)),
          });
        }
      }
      return config;
    },
    response(response: any) {
      if (!isCurrent(response)) throw new Error('Report refresh was superseded.');
      const expected = response.config?._mtaPublicationBinding;
      if (expected && response.headers?.[PUBLICATION_HEADER.toLowerCase()] !== expected) {
        throw new Error('Publication response is missing or stale. Refresh the report.');
      }
      const parts = transportUrl(response.config || {}).pathname.split('/');
      if (parts[1] === 'api' && parts[2] === 'mta' && mutationNames.has(parts[3]) &&
          response.status >= 200 && response.status < 300 && (response.data?.status || 200) < 400) refresh();
      return response;
    },
    refresh,
    subscribeRefresh(listener: () => void) {
      refreshListeners.add(listener);
      return () => { refreshListeners.delete(listener); };
    },
    isCurrent,
  };
};

export const mtaPublicationBinding = createMtaPublicationBinding(config => axios(config));
export const refreshMtaReportBinding = () => mtaPublicationBinding.refresh();
export const resetMtaReportBinding = () => mtaPublicationBinding.refresh(false);
export const subscribeMtaReportRefresh = (listener: () => void) => mtaPublicationBinding.subscribeRefresh(listener);
export const isMtaReportCurrent = (response: any) => mtaPublicationBinding.isCurrent(response);
