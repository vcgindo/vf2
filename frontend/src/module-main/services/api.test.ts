import { expandBrowserRoutePermissions, MainService } from './api'
import axios from 'axios'
import { mtaPublicationBinding, PUBLICATION_HEADER } from '../../config/mta-publication-binding'

jest.mock('axios')

describe('expandBrowserRoutePermissions', () => {
  it('retains gateway permissions and adds browser aliases for MTA and MTO routes', () => {
    expect(
      expandBrowserRoutePermissions([
        '/mta/supply-chain-intelligence-hub/planning',
        '/mto/procurement/material-coverage-open-sales',
        '/landing-page'
      ])
    ).toEqual([
      '/mta/supply-chain-intelligence-hub/planning',
      '/supply-chain-intelligence-hub/planning',
      '/mto/procurement/material-coverage-open-sales',
      '/procurement/material-coverage-open-sales',
      '/landing-page'
    ])
  })

  it('deduplicates browser routes already present in the permission payload', () => {
    expect(
      expandBrowserRoutePermissions([
        '/mta/insights-and-trends/guided-insights',
        '/insights-and-trends/guided-insights'
      ])
    ).toEqual([
      '/mta/insights-and-trends/guided-insights',
      '/insights-and-trends/guided-insights'
    ])
  })
})

describe('MTA binding across existing local session transitions', () => {
  const loginReply = { status: 200, data: { data: { user: { id: 8, name: 'Fixture' }, url_permission: [] } } }
  const bind = async (token: string) => {
    (axios as unknown as jest.Mock).mockResolvedValue({ data: { mode: 'native', binding: token } })
    return mtaPublicationBinding.request({ url: '/api/mta/RRRData' })
  }
  beforeEach(() => { jest.clearAllMocks(); mtaPublicationBinding.refresh(); localStorage.clear() })

  it('successful login invalidates the old actor binding and acquires the new one', async () => {
    const old = await bind('a'.repeat(64))
    ;(axios.post as jest.Mock).mockResolvedValueOnce(loginReply)
    await MainService.login({ email: 'fixture@example.invalid', password: 'encrypted-fixture' } as any)
    expect(mtaPublicationBinding.isCurrent({ config: old })).toBe(false)
    expect((await bind('b'.repeat(64))).headers[PUBLICATION_HEADER]).toBe('b'.repeat(64))
    expect(axios.post).toHaveBeenCalledTimes(1)
  })

  it('failed login does not replace an existing binding', async () => {
    const old = await bind('a'.repeat(64))
    ;(axios.post as jest.Mock).mockRejectedValueOnce(new Error('denied'))
    await expect(MainService.login({} as any)).rejects.toThrow('denied')
    expect(mtaPublicationBinding.isCurrent({ config: old })).toBe(true)
  })

  it.each([false, true])('logout cleanup invalidates report work when logout failure=%s', async failed => {
    const old = await bind('a'.repeat(64))
    const queryClient = { clear: jest.fn() }
    if (failed) (axios.post as jest.Mock).mockRejectedValueOnce(new Error('logout unavailable'))
    else (axios.post as jest.Mock).mockResolvedValueOnce({ status: 204 })
    const result = MainService.logout(queryClient as any)
    if (failed) await expect(result).rejects.toThrow('logout unavailable')
    else await expect(result).resolves.toMatchObject({ status: 204 })
    expect(mtaPublicationBinding.isCurrent({ config: old })).toBe(false)
    expect(queryClient.clear).toHaveBeenCalledTimes(1)
    expect(axios.post).toHaveBeenCalledTimes(1)
  })
})
