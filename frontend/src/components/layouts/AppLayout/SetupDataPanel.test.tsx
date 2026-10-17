import 'ag-grid-enterprise';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import axios from 'axios';
import { UserDataContext } from '../../../context';
import { ApplicationSetup } from './ApplicationSetup';
import { SetupMaster, SetupReport, SetupWorkflow } from './SetupDataPanel';

jest.mock('axios');
const get = axios.get as jest.Mock;
const post = axios.post as jest.Mock;
const originalResizeObserver = global.ResizeObserver;
let client: QueryClient;
beforeEach(() => {
  jest.clearAllMocks();
  global.ResizeObserver = class { observe = jest.fn(); unobserve = jest.fn(); disconnect = jest.fn(); };
  client = new QueryClient({ defaultOptions: { queries: { retry: false, cacheTime: 0 } } });
});
afterEach(() => { cleanup(); client.clear(); global.ResizeObserver = originalResizeObserver; });
const ready = (initialized = false) => ({ status: 503, data: { application: {
  available: true, installed: true, initialized, publication_selected: false,
  state: initialized ? 'initialized' : 'installed',
} } });
const open = (page: React.ReactNode) => render(
  <UserDataContext.Provider value={{ user: { user: { theme_ui: 'NOIRFUSION' } } } as any}>
    <QueryClientProvider client={client}><MemoryRouter initialEntries={['/mta/supply-chain-intelligence-hub/bpr']}>
      <ApplicationSetup>{page}</ApplicationSetup>
    </MemoryRouter></QueryClientProvider>
  </UserDataContext.Provider>,
);
const OperationalPage = () => { throw new Error('Operational requests must not mount before publication'); };

test('empty installed report loads its real definition and grid without mounting operational requests', async () => {
  get.mockImplementation((url: string) => Promise.resolve(url === 'readyz' ? ready() : {
    status: 200, data: { data: [{ Col_Code: 'sc', Header: 'SKU Code', Visible: true, DataType: 'String', Col_Position: 1 }] },
  }));
  open(<SetupReport title="BPR" reports={['AdminBPR']}><OperationalPage /></SetupReport>);
  expect(await screen.findByRole('columnheader', { name: 'SKU Code' })).toBeInTheDocument();
  expect(screen.getByText('No published data')).toBeInTheDocument();
  expect(get.mock.calls.map(call => call[0])).toHaveLength(2);
  expect(get.mock.calls[1][0]).toContain('GetUIConfig?reportName=AdminBPR');
  expect(post).not.toHaveBeenCalled();
});

test('master family selection displays supplied fields with operations disabled and no data requests', async () => {
  get.mockResolvedValue(ready());
  const field = (key: string, displayName: string) => ({ key, displayName, col_Position: '1', visible: true,
    isAdd: true, isEdit: true, isDelete: true, isDownload: true, isApplicable: true, dataType: 'String' });
  post.mockResolvedValue({ status: 200, data: { data: [
    { id: '1', name: 'SKU', fields: [field('sc', 'SKU Code')] },
    { id: '5', name: 'MOQ', fields: [field('moq', 'Minimum Order Quantity')] },
  ], setupRequirements: [{ masterId: 5, setting: 'NMSMOQInputDataFormat' }] } });
  open(<SetupMaster operation="add"><OperationalPage /></SetupMaster>);
  expect(await screen.findByRole('columnheader', { name: 'SKU Code' })).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Master'), { target: { value: '5' } });
  expect(await screen.findByRole('columnheader', { name: 'Minimum Order Quantity' })).toBeInTheDocument();
  expect(screen.getByText(/initialized NMSMOQInputDataFormat setting/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Upload' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Submit' })).toBeDisabled();
  expect(post).toHaveBeenCalledTimes(1);
  expect(post.mock.calls[0][0]).toContain('GetMasterUIConfiguration');
});

test('a definition failure is shown as an error and never as a configured empty grid', async () => {
  get.mockImplementation((url: string) => url === 'readyz' ? Promise.resolve(ready()) : Promise.reject(new Error('bad definition')));
  open(<SetupReport title="BPR" reports={['AdminBPR']}><OperationalPage /></SetupReport>);
  expect(await screen.findByRole('alert')).toHaveTextContent('Screen definition is unavailable');
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
});

test('initialized masters return to their existing supported page while reports still await publication', async () => {
  get.mockResolvedValue(ready(true));
  open(<SetupMaster operation="modify"><p>Existing master page</p></SetupMaster>);
  await waitFor(() => expect(screen.getByText('Existing master page')).toBeInTheDocument());
  expect(post).not.toHaveBeenCalled();
});

test('the empty reviewer page retains workflow headers and cannot start a task read or action', async () => {
  get.mockResolvedValue(ready());
  open(<SetupWorkflow title="Tasks Pending for Review" kind="review"><OperationalPage /></SetupWorkflow>);
  expect(await screen.findByRole('columnheader', { name: 'Pending Since' })).toBeInTheDocument();
  expect(screen.getByRole('columnheader', { name: 'Task Name' })).toBeInTheDocument();
  expect(get).toHaveBeenCalledTimes(1);
  expect(post).not.toHaveBeenCalled();
});


test('initialized add configuration labels the missing publication truthfully', async () => {
  get.mockResolvedValue(ready(true));
  post.mockResolvedValue({ status: 200, data: { data: [{ id: '1', name: 'SKU', fields: [] }] } });
  open(<SetupMaster operation="add"><OperationalPage /></SetupMaster>);
  expect(await screen.findByText('No published operational day')).toBeInTheDocument();
  expect(screen.queryByText('Initial data not loaded')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Upload' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Submit' })).toBeDisabled();
});
