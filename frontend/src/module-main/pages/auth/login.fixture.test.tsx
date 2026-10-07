import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LoginContainer from './login';
import { fixtureCaptchaExempt } from './fixture-captcha-policy';
import { useLoginAccount } from '../../../module-main/services';
import { hashPassword } from '../../../helpers/utils';
import { validateCaptcha } from 'react-simple-captcha';

jest.mock('./fixture-captcha-policy', () => ({ fixtureCaptchaExempt: jest.fn() }));
jest.mock('../../../module-main/services', () => ({ useLoginAccount: jest.fn() }));
jest.mock('../../../helpers/utils', () => ({ hashPassword: jest.fn(), completeLocalLogin: jest.fn() }));
jest.mock('../../../helpers/notify', () => ({ notifyError: jest.fn(), notifySuccess: jest.fn(), notifyWarningWithoutAutoClose: jest.fn() }));
jest.mock('react-simple-captcha', () => ({ loadCaptchaEnginge: jest.fn(), validateCaptcha: jest.fn(), LoadCanvasTemplateNoReload: () => <canvas data-testid="captcha" /> }));
jest.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
jest.mock('react-redux', () => ({ useDispatch: () => jest.fn() }));
jest.mock('../../../redux/actions/MTA', () => ({ UPDATE_ENV_CONFIG: jest.fn() }));
jest.mock('../../../VectorFlow/Services/MTA/MDM', () => ({ useGetAllEnvironmentConfiguration: () => ({ mutateAsync: jest.fn() }) }));
jest.mock('../../../components', () => ({ Errors: () => null }));
jest.mock('../../../components/VectorFLOW/commons/VFLoader', () => () => null);
jest.mock('./welcome-board', () => () => null);

function form() {
  const view = render(<MemoryRouter><LoginContainer /></MemoryRouter>);
  fireEvent.change(screen.getByPlaceholderText('loginPage.placeholder.email'), { target: { value: 'stage2.broad@vectorflow.local' } });
  fireEvent.change(screen.getByPlaceholderText('loginPage.placeholder.password'), { target: { value: 'original-password' } });
  return view.container.querySelector('form')!;
}

beforeEach(() => {
  jest.clearAllMocks();
  (hashPassword as jest.Mock).mockResolvedValue('hashed-original');
  (validateCaptcha as jest.Mock).mockReturnValue(false);
});

it('keeps the form snapshot and blocks duplicate submits throughout the pending login', async () => {
  let allow!: (value: boolean) => void;
  let finish!: (value: unknown) => void;
  (fixtureCaptchaExempt as jest.Mock).mockReturnValue(new Promise(resolve => { allow = resolve; }));
  const login = jest.fn().mockReturnValue(new Promise(resolve => { finish = resolve; }));
  (useLoginAccount as jest.Mock).mockReturnValue({ mutateAsync: login, isLoading: false });
  const element = form();
  fireEvent.submit(element);
  await waitFor(() => expect(fixtureCaptchaExempt).toHaveBeenCalledTimes(1));
  fireEvent.change(screen.getByPlaceholderText('loginPage.placeholder.email'), { target: { value: 'other@example.test' } });
  fireEvent.change(screen.getByPlaceholderText('loginPage.placeholder.password'), { target: { value: 'changed-password' } });
  await act(async () => { allow(true); });
  expect(hashPassword).toHaveBeenCalledWith('original-password');
  expect(login).toHaveBeenCalledWith({ email: 'stage2.broad@vectorflow.local', password: 'hashed-original' }, expect.any(Object));
  fireEvent.submit(element);
  await act(async () => { await Promise.resolve(); });
  expect(login).toHaveBeenCalledTimes(1);
  expect(fixtureCaptchaExempt).toHaveBeenCalledTimes(1);
  expect(validateCaptcha).not.toHaveBeenCalled();
  expect(screen.getByTestId('captcha')).toBeTruthy();
  await act(async () => { finish({}); });
});

it('retains the CAPTCHA gate for a negative policy response', async () => {
  (fixtureCaptchaExempt as jest.Mock).mockResolvedValue(false);
  const login = jest.fn();
  (useLoginAccount as jest.Mock).mockReturnValue({ mutateAsync: login, isLoading: false });
  fireEvent.submit(form());
  await waitFor(() => expect(fixtureCaptchaExempt).toHaveBeenCalled());
  expect(login).not.toHaveBeenCalled();
  expect(hashPassword).not.toHaveBeenCalled();
});
