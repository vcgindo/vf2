import axios from 'axios';
import { createContext, PropsWithChildren, useContext } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useLocation } from 'react-router-dom';

export interface ApplicationState {
  installed: true;
  initialized: boolean;
  publication_selected: false;
  state: 'installed' | 'initialized';
}

const ApplicationSetupContext = createContext<ApplicationState | null>(null);
export const useApplicationSetup = () => useContext(ApplicationSetupContext);

const loadState = async (): Promise<ApplicationState | null> => {
  const response = await axios.get('readyz', {
    timeout: 15000,
    validateStatus: status => status === 200 || status === 503,
  });
  if (response.status === 200 && response.data?.status === 'ready') return null;
  const value = response.data?.application;
  if (value?.available === true && value.installed === true && value.publication_selected === false
      && typeof value.initialized === 'boolean'
      && ((value.state === 'installed' && !value.initialized)
          || (value.state === 'initialized' && value.initialized))) return value;
  throw new Error('Application configuration is unavailable. Ask the deployment operator to check readiness.');
};

export const ApplicationSetup = ({ children }: PropsWithChildren<{}>) => {
  const { pathname } = useLocation();
  const enabled = pathname.startsWith('/mta/') || pathname === '/supply-chain-intelligence-hub/merchandising-grid';
  const state = useQuery(['installed-application-state'], loadState, {
    enabled, retry: false, staleTime: 15000, refetchOnWindowFocus: false,
  });
  if (!enabled) return <>{children}</>;
  if (state.isLoading) return <p role="status">Checking application setup…</p>;
  if (state.isError) return (
    <div role="alert">
      <p>Application configuration is unavailable. Ask the deployment operator to check readiness.</p>
      <button type="button" onClick={() => state.refetch()}>Check again</button>
    </div>
  );
  return (
    <ApplicationSetupContext.Provider value={state.data || null}>
      {state.data && (
        <div role="status" style={{ padding: '12px 16px', marginBottom: 12, borderBottom: '1px solid #ddd' }}>
          {state.data.initialized
            ? 'Initial data is installed. Operational reports will be available after a calculated day is published.'
            : 'The application is installed. Initial data has not been loaded. You can browse configuration; business operations require initialization.'}
        </div>
      )}
      {children}
    </ApplicationSetupContext.Provider>
  );
};
