import { render, screen } from '@testing-library/react'
import { useState } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { UserDataContext } from '../../../context'
import { MainService } from '../../../module-main/services/api'
import { ROUTES } from '../../../helpers/constants'
import { clearRedirecting, completeLocalLogin, getRedirecting, loginRedirect, setRedirecting } from '../../../helpers/utils'
import { AuthenticationTemplate } from './AuthenticationTemplate'

jest.mock('../../../module-main/services/api', () => ({
  MainService: { getProfile: jest.fn() }
}))

const getProfile = MainService.getProfile as jest.MockedFunction<typeof MainService.getProfile>

const ProtectedRoute = () => {
  const [user, setUser] = useState<any>(null)

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
      </AuthenticationTemplate>
    </UserDataContext.Provider>
  )
}

const renderProtected = () => render(
  <MemoryRouter initialEntries={['/profile']}>
    <Routes>
      <Route path={ROUTES.landing} element={<div>Login page</div>} />
      <Route path="/profile" element={<ProtectedRoute />} />
    </Routes>
  </MemoryRouter>
)

describe('AuthenticationTemplate redirect lifecycle', () => {
  beforeEach(() => {
    clearRedirecting()
    getProfile.mockReset()
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
  })

  it('redirects a profile response without user data instead of remaining Loading', async () => {
    getProfile.mockResolvedValue({ data: {} } as any)

    renderProtected()

    expect(await screen.findByText('Login page')).toBeInTheDocument()
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
    expect(getRedirecting()).toBe(true)
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
