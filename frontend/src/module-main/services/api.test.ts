import { expandBrowserRoutePermissions } from './api'

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
