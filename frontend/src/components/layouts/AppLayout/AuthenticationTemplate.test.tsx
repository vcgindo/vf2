import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { UserDataContext } from '../../../context'
import { MainService } from '../../../module-main/services/api'
import { ROUTES } from '../../../helpers/constants'
import { clearRedirecting, completeLocalLogin, getRedirecting, loginRedirect, setRedirecting } from '../../../helpers/utils'
import { AuthenticationTemplate } from './AuthenticationTemplate'
import { MDMService } from '../../../VectorFlow/Services/MTA/MDM/api'
import { UPDATE_ENV_CONFIG } from '../../../redux/actions/MTA'

const mockDispatch = jest.fn()
jest.mock('react-redux', () => ({ useDispatch: () => mockDispatch }))
jest.mock('../../../VectorFlow/Services/MTA/MDM/api', () => ({
  MDMService: { getAllEnvironmentConfiguration: jest.fn() }
}))

jest.mock('../../../module-main/services/api', () => ({
  MainService: { getProfile: jest.fn() }
}))

const getProfile = MainService.getProfile as jest.MockedFunction<typeof MainService.getProfile>
const getEnvironment = MDMService.getAllEnvironmentConfiguration as jest.MockedFunction<typeof MDMService.getAllEnvironmentConfiguration>

const ProtectedRoute = ({ initialUser = null }: { initialUser?: any }) => {
  const [user, setUser] = useState<any>(initialUser)

  return (
    <UserDataContext.Provider value={{
      user,
      setUser,
      changeColorTheme: color => color,
      isSideBarOpen: false,
      toggleSideBar: jest.fn()
    }}>
      <AuthenticationTemplate
        isAnonymous={false}
        loadingComponent={<div>Loading...</div>}
        setMenuItem={jest.fn()}
      >
        <div>Protected profile</div>
        <button onClick={() => setUser((current: any) => ({ ...current }))}>Update context</button>
      </AuthenticationTemplate>
    </UserDataContext.Provider>
  )
}

const renderProtected = (initialUser?: any) => render(
  <MemoryRouter initialEntries={['/profile']}>
    <Routes>
      <Route path={ROUTES.landing} element={<div>Login page</div>} />
      <Route path="/profile" element={<ProtectedRoute initialUser={initialUser} />} />
    </Routes>
  </MemoryRouter>
)

describe('AuthenticationTemplate redirect lifecycle', () => {
  beforeEach(() => {
    clearRedirecting()
    getProfile.mockReset()
    getEnvironment.mockReset()
    getEnvironment.mockResolvedValue({ data: { data: [] } } as any)
    mockDispatch.mockClear()
  })

  it('fetches and installs a successful profile even when a redirect flag is stale', async () => {
    const profile = { user: { id: 7, name: 'Reader' }, roles: { permission: [] } }
    setRedirecting()
    getProfile.mockResolvedValue({ data: { data: profile } } as any)

    renderProtected()

    expect(await screen.findByText('Protected profile')).toBeInTheDocument()
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
    expect(getProfile).toHaveBeenCalledTimes(1)
    expect(getRedirecting()).toBe(false)
  })

  it('redirects a rejected profile request after clearing a stale transition', async () => {
    setRedirecting()
    getProfile.mockRejectedValue(new Error('profile unavailable'))

    renderProtected()

    expect(await screen.findByText('Login page')).toBeInTheDocument()
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
    expect(getRedirecting()).toBe(true)
    expect(getEnvironment).not.toHaveBeenCalled()
  })

  it('redirects a profile response without user data instead of remaining Loading', async () => {
    getProfile.mockResolvedValue({ data: {} } as any)

    renderProtected()

    expect(await screen.findByText('Login page')).toBeInTheDocument()
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
    expect(getRedirecting()).toBe(true)
    expect(getEnvironment).not.toHaveBeenCalled()
  })

  it('waits for the profile, renders children while configuration is pending, and dispatches configuration once', async () => {
    let finishProfile!: (value: any) => void
    let finishConfiguration!: (value: any) => void
    getProfile.mockReturnValue(new Promise(resolve => { finishProfile = resolve }))
    getEnvironment.mockImplementation(() => {
      expect(screen.getByText('Protected profile')).toBeInTheDocument()
      return new Promise(resolve => { finishConfiguration = resolve })
    })
    renderProtected()
    expect(screen.getByText('Loading...')).toBeInTheDocument()
    expect(getEnvironment).not.toHaveBeenCalled()

    const profile = { user: { id: 7, name: 'Reader' }, roles: { permission: [] } }
    await act(async () => { finishProfile({ data: { data: profile } }) })
    expect(screen.getByText('Protected profile')).toBeInTheDocument()
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
    expect(getEnvironment).toHaveBeenCalledTimes(1)
    expect(mockDispatch).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText('Update context'))
    expect(getEnvironment).toHaveBeenCalledTimes(1)

    await act(async () => { finishConfiguration({ data: { data: [
      { ConfigKey: 'VIEWRECORD_PAGE', ConfigValue: '50' },
      { ConfigKey: 'PRODUCT_PERMISSION_L1', ConfigValue: 'Brand' },
    ] } }) })
    expect(mockDispatch).toHaveBeenCalledTimes(1)
    expect(mockDispatch).toHaveBeenCalledWith(UPDATE_ENV_CONFIG({
      VIEWRECORD_PAGE: '50', PRODUCT_PERMISSION_L1: 'Brand',
    } as any))
    expect(getEnvironment).toHaveBeenCalledTimes(1)
  })

  it('preserves children for an existing context user while the mandatory profile check is pending', () => {
    getProfile.mockReturnValue(new Promise(() => undefined))
    renderProtected({ user: { id: 7, name: 'Reader' } })
    expect(screen.getByText('Protected profile')).toBeInTheDocument()
    expect(getProfile).toHaveBeenCalledTimes(1)
    expect(getEnvironment).not.toHaveBeenCalled()
  })

  it('ignores a profile response after the authenticated template unmounts', async () => {
    let finishProfile!: (value: any) => void
    getProfile.mockReturnValue(new Promise(resolve => { finishProfile = resolve }))
    const view = renderProtected()
    view.unmount()
    await act(async () => { finishProfile({ data: { data: { user: { id: 7 } } } }) })
    expect(getEnvironment).not.toHaveBeenCalled()
    expect(mockDispatch).not.toHaveBeenCalled()
  })

  it('ignores a configuration response after the authenticated template unmounts', async () => {
    let finishConfiguration!: (value: any) => void
    getProfile.mockResolvedValue({ data: { data: { user: { id: 7 } } } } as any)
    getEnvironment.mockReturnValue(new Promise(resolve => { finishConfiguration = resolve }))
    const view = renderProtected()
    await screen.findByText('Protected profile')
    await waitFor(() => expect(getEnvironment).toHaveBeenCalledTimes(1))
    view.unmount()
    await act(async () => { finishConfiguration({ data: { data: [
      { ConfigKey: 'VIEWRECORD_PAGE', ConfigValue: '50' },
    ] } }) })
    expect(mockDispatch).not.toHaveBeenCalled()
  })

  it('retains rendered children and the existing console error when ancillary configuration fails', async () => {
    const error = new Error('configuration unavailable')
    const log = jest.spyOn(console, 'error').mockImplementation(() => undefined)
    try {
      getProfile.mockResolvedValue({ data: { data: { user: { id: 7 } } } } as any)
      getEnvironment.mockRejectedValue(error)
      renderProtected()
      expect(await screen.findByText('Protected profile')).toBeInTheDocument()
      await waitFor(() => expect(log).toHaveBeenCalledWith('Unexpected error in get Environment configuration:', error))
      expect(getEnvironment).toHaveBeenCalledTimes(1)
      expect(mockDispatch).not.toHaveBeenCalled()
      expect(getRedirecting()).toBe(false)
    } finally {
      log.mockRestore()
    }
  })

  it('allows successful SPA login to clear the prior redirect transition', () => {
    const navigate = jest.fn()
    setRedirecting()
    expect(getRedirecting()).toBe(true)

    completeLocalLogin(navigate)

    expect(getRedirecting()).toBe(false)
    expect(navigate).toHaveBeenCalledWith('/landing-page', { replace: true })
  })

  it('deduplicates repeated login redirects within one verification transition', () => {
    const navigate = jest.fn()

    loginRedirect(navigate)
    loginRedirect(navigate)

    expect(navigate).toHaveBeenCalledTimes(1)
    expect(navigate).toHaveBeenCalledWith(ROUTES.landing, { replace: true })
  })
})
