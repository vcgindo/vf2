import { createRef } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import axios from 'axios';
import ModalAdvanedPermissions from './index';
import { UserDataContext } from '../../../context';
import { useRegisterUser, usePutEditUser } from '../../../services/profile';
import { notifyError } from '../../../helpers/notify';

jest.mock('axios');
jest.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
jest.mock('../../../services/profile');
jest.mock('../../../helpers/notify', () => ({ notifyError: jest.fn(), notifySuccess: jest.fn(), notifyWarning: jest.fn() }));
jest.mock('../../../VectorFlow/Services/MTO/Common/DBRSettings', () => ({ useGetDBRsettingsData: () => ({ mutateAsync: async () => ({ data: { data: [] } }) }) }));
jest.mock('../../../components/layouts/ProductPermission/common-mulselect', () => {
  const React = require('react');
  return React.forwardRef((_props: unknown, ref: any) => {
    React.useImperativeHandle(ref, () => ({ getPrdPermissionValue: () => ({ brand: [], subBrand: [], category: [] }) }));
    return <p>Product scope selector</p>;
  });
});
jest.mock('../../../components/layouts/LocationPermission/common-mulselect', () => {
  const React = require('react');
  return React.forwardRef((_props: unknown, ref: any) => {
    React.useImperativeHandle(ref, () => ({ getLcPermissionValue: () => ({ lcRegion: [], lcType: [], lcCluster: [] }) }));
    return <p>Location scope selector</p>;
  });
});
const register = jest.fn();
const get = axios.get as jest.Mock;
const originalResizeObserver = global.ResizeObserver;
let client: QueryClient;
beforeEach(() => {
  jest.clearAllMocks();
  global.ResizeObserver = class { observe = jest.fn(); unobserve = jest.fn(); disconnect = jest.fn(); };
  (useRegisterUser as jest.Mock).mockReturnValue({ mutateAsync: register });
  (usePutEditUser as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
});
afterEach(() => { client.clear(); global.ResizeObserver = originalResizeObserver; });
const open = (populated = false) => {
  client = new QueryClient({ defaultOptions: { queries: { retry: false, cacheTime: 0 } } });
  const role = { application_id: 1, application_name: 'Distribution' };
  return render(<QueryClientProvider client={client}>
    <UserDataContext.Provider value={{ user: { user: { theme_ui: 'NOIRFUSION' } } } as any}>
      <ModalAdvanedPermissions openModal activeApplication={1} infoUser={{ name: 'ordinary', roles: [2] }}
        allPermissions={{ product_permission: populated ? [{ id: 1 }] : [], location_permission: [] }}
        storePermission={[role]} setStorePermission={jest.fn()} stepperDetails={[]} headers={{}}
        prdPermissionRef={createRef()} lcPermissionRef={createRef()} contentModal={{ callApi: 1, buttonSubmit: 'Add User' }}
        closeModal={jest.fn()} setIsOpenUser={jest.fn()} setIsOpenAdvanced={jest.fn()} setStepperDetails={jest.fn()}
        setActiveApplication={jest.fn()} updateAllPermissions={jest.fn()} refetch={jest.fn()} isCheckBoxRef={createRef()} />
    </UserDataContext.Provider>
  </QueryClientProvider>);
};
const installed = { status: 503, data: { application: { available: true, installed: true,
  initialized: false, publication_selected: false, state: 'installed' } } };

test('validated empty install submits the normal account contract with no population access', async () => {
  get.mockResolvedValue(installed);
  open();
  expect(await screen.findByRole('status')).toHaveTextContent('no population access');
  fireEvent.click(screen.getByRole('button', { name: 'Add User' }));
  await waitFor(() => expect(register).toHaveBeenCalledTimes(1));
  expect(register.mock.calls[0][0]).toEqual({ name: 'ordinary', roles: [2], tc: true,
    product_permissions: [{ application_id: 1, permissions: [] }],
    location_permissions: [{ application_id: 1, permissions: [] }] });
});

test.each(['published', 'invalid', 'populated'])('%s cannot use empty setup to omit scope selection', async mode => {
  get.mockResolvedValue(mode === 'invalid' ? { status: 503, data: {} }
    : mode === 'published' ? { status: 200, data: { status: 'ready' } } : installed);
  open(mode === 'populated');
  await waitFor(() => expect(get).toHaveBeenCalled());
  await waitFor(() => expect(screen.queryByRole('status')).not.toBeInTheDocument());
  fireEvent.click(screen.getByRole('button', { name: 'Add User' }));
  expect(register).not.toHaveBeenCalled();
  expect(notifyError).toHaveBeenCalledWith('Please select permission for the selected application!');
});
