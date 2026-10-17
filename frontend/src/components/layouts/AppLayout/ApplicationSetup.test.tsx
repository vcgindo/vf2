import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import axios from 'axios';
import { ApplicationSetup, useApplicationSetup } from './ApplicationSetup';

jest.mock('axios');
const get = axios.get as jest.Mock;

const Page = () => {
  const setup = useApplicationSetup();
  return <p>{setup ? `Configuration: ${setup.state}` : 'Operational page'}</p>;
};
const open = (path = '/mta/supply-chain-intelligence-hub/bpr') => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, cacheTime: 0 } } })}>
    <MemoryRouter initialEntries={[path]}><ApplicationSetup><Page /></ApplicationSetup></MemoryRouter>
  </QueryClientProvider>,
);

beforeEach(() => get.mockReset());

test('valid empty setup is explained without changing data readiness to ready', async () => {
  get.mockResolvedValue({ status: 503, data: { status: 'unavailable', application: {
    available: true, installed: true, initialized: false, publication_selected: false, state: 'installed',
  } } });
  open();
  expect(await screen.findByText('Configuration: installed')).toBeInTheDocument();
  expect(screen.getByText(/Initial data has not been loaded/)).toBeInTheDocument();
  expect(screen.queryByText('Operational page')).not.toBeInTheDocument();
});

test('an initialized source without a day is still explained as awaiting publication', async () => {
  get.mockResolvedValue({ status: 503, data: { application: {
    available: true, installed: true, initialized: true, publication_selected: false, state: 'initialized',
  } } });
  open();
  expect(await screen.findByText('Configuration: initialized')).toBeInTheDocument();
  expect(screen.getByText(/after a calculated day is published/)).toBeInTheDocument();
});

test('a broken configured installation cannot render as a successful empty application', async () => {
  get.mockResolvedValue({ status: 503, data: { ready: false } });
  open();
  expect(await screen.findByRole('alert')).toHaveTextContent('Application configuration is unavailable');
  expect(screen.queryByText('Operational page')).not.toBeInTheDocument();
  expect(screen.queryByText(/Initial data has not/)).not.toBeInTheDocument();
});

test('published mode retains its page and profile does not depend on MTA readiness', async () => {
  get.mockResolvedValue({ status: 200, data: { status: 'ready' } });
  open();
  expect(await screen.findByText('Operational page')).toBeInTheDocument();
  expect(screen.queryByText(/Initial data/)).not.toBeInTheDocument();
});

test('profile and account setup remain independent of MTA data readiness', () => {
  open('/profile');
  expect(screen.getByText('Operational page')).toBeInTheDocument();
  expect(get).not.toHaveBeenCalled();
});
