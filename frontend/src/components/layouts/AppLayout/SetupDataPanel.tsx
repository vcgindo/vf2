import { PropsWithChildren, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import VFTable from '../../VectorFLOW/commons/VFTable';
import { UIConfigService } from '../../../VectorFlow/Services/MTA/Common/UIConfig/api';
import { MDMService } from '../../../VectorFlow/Services/MTA/MDM/api';
import { getColumnDefinationsMTA, mapMasterToColumnDefs } from '../../../helpers/utils';
import { useApplicationSetup } from './ApplicationSetup';
import { savedDraftFields, taskStatusColumns, pendingTaskColumns, historyColumns } from '../../../VectorFlow/Pages/MTA/MDM/workflowDefinitions';

type ReportProps = PropsWithChildren<{ title: string; reports?: string[]; chart?: boolean }>;

// These are presentation states of the existing pages. They do not admit a route,
// grant permission, synthesize an API result, or mount operational request hooks.
export const SetupReport = (props: ReportProps) => useApplicationSetup()
  ? <ReportDefinition {...props} /> : <>{props.children}</>;

const ReportDefinition = ({ title, reports = [], chart }: ReportProps) => {
  const [selected, setSelected] = useState(reports[0]);
  const configuration = useQuery(['setup-report-definition', selected], async ({ signal }) => {
    const response = await UIConfigService.getUIConfigData(selected, { signal, timeout: 15000 });
    if (response.status !== 200 || !Array.isArray(response.data?.data)) {
      throw new Error('Screen definition is unavailable.');
    }
    return getColumnDefinationsMTA(response.data.data).map((column: any) => ({ ...column, editable: false }));
  }, { enabled: !!selected, retry: false, refetchOnWindowFocus: false });
  return (
    <section aria-label={title} style={{ padding: 16 }}>
      <h2>{title}</h2>
      <p role="status">No operational day has been published. Data, dates and business actions will be available after publication.</p>
      {reports.length > 1 && <label>View <select value={selected} onChange={event => setSelected(event.target.value)}>
        {reports.map(report => <option key={report} value={report}>{report.replace(/_/g, ' ')}</option>)}
      </select></label>}
      {selected && (configuration.isLoading ? <p role="status">Loading screen definition…</p>
        : configuration.isError ? <p role="alert">Screen definition is unavailable. Ask the operator to check the installed release.</p>
          : <VFTable columnDefs={configuration.data} rowData={[]} height="420px"
              overlayNoRowsTemplate="No published data" suppressNoRowsOverlay={false} />)}
      {chart && <div role="img" aria-label={`${title}: no published chart data`}
        style={{ height: 260, borderLeft: '1px solid #aaa', borderBottom: '1px solid #aaa', display: 'grid', placeItems: 'center' }}>
        No published chart data
      </div>}
    </section>
  );
};

type MasterProps = PropsWithChildren<{ operation: 'modify' | 'add' | 'remove'; title?: string; history?: boolean }>;
export const SetupMaster = (props: MasterProps) => {
  const state = useApplicationSetup();
  return state && !state.initialized ? <MasterDefinition {...props} /> : <>{props.children}</>;
};

export const SetupWorkflow = ({ title, kind, children }: PropsWithChildren<{
  title: string; kind: 'drafts' | 'status' | 'review';
}>) => {
  const state = useApplicationSetup();
  if (!state || state.initialized) return <>{children}</>;
  const columns = kind === 'drafts' ? mapMasterToColumnDefs(savedDraftFields)
    : kind === 'status' ? taskStatusColumns : pendingTaskColumns();
  return <section aria-label={title} style={{ padding: 16 }}>
    <h2>{title}</h2>
    <p role="status">Initial data has not been loaded. Workflow records and actions require initialization.</p>
    <VFTable columnDefs={columns.map(column => ({ ...column, editable: false }))} rowData={[]}
      height="420px" overlayNoRowsTemplate="Initial data not loaded" />
  </section>;
};

const MasterDefinition = ({ operation, title, history }: MasterProps) => {
  const [selected, setSelected] = useState('');
  const configuration = useQuery(['setup-master-definition', operation], async ({ signal }) => {
    const response = await MDMService.getMasterUIConfiguration(operation, { signal, timeout: 15000 });
    if (response.status !== 200 || !Array.isArray(response.data?.data)) throw new Error('Master definition is unavailable.');
    return response.data;
  }, { retry: false, refetchOnWindowFocus: false });
  const families = configuration.data?.data || [];
  const family = families.find((item: any) => item.id === selected) || families[0];
  const columns = family ? mapMasterToColumnDefs(family.fields, Number(family.id), undefined, operation)
    .map((column: any) => ({ ...column, editable: false })) : [];
  return <section aria-label={title || 'Master data configuration'} style={{ padding: 16 }}>
    <h2>{title || ({ modify: 'View / Modify', add: 'Add Record', remove: 'Delete Record' }[operation])}</h2>
    <p role="status">Initial data has not been loaded. Master fields can be inspected; reading, uploading, changing and submitting business data require initialization.</p>
    {configuration.isLoading ? <p role="status">Loading master definitions…</p>
      : configuration.isError ? <p role="alert">Master definitions are unavailable. Ask the operator to check the installed release.</p>
        : <>
          <label>Master <select value={family?.id || ''} onChange={event => setSelected(event.target.value)}>
            {families.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select></label>
          {configuration.data?.setupRequirements?.filter((item: any) => String(item.masterId) === family?.id)
            .map((item: any) => <p key={item.setting}>This master also requires the initialized {item.setting} setting.</p>)}
          <VFTable columnDefs={history ? [...historyColumns, ...columns] : columns} rowData={[]} height="420px" overlayNoRowsTemplate="Initial data not loaded" />
          <button type="button" disabled>{operation === 'add' ? 'Upload' : 'Show All'}</button>{' '}
          {!history && <button type="button" disabled>Submit</button>}
        </>}
  </section>;
};
