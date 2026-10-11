import React, { PropsWithChildren } from 'react'
import { act, renderHook } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MainService } from '../../../../../module-main/services/api'
import { PlanningService } from './api'
import { useGetPlanningDataCount } from '.'

jest.mock('../../../../../module-main/services/api', () => ({
  MainService: { acquireToken: jest.fn() }
}))

jest.mock('./api', () => ({
  PlanningService: {
    getSummaryIdentity: jest.fn(),
    getPlanningDataCount: jest.fn()
  }
}))

const acquireToken = MainService.acquireToken as jest.MockedFunction<typeof MainService.acquireToken>
const getSummaryIdentity = PlanningService.getSummaryIdentity as jest.MockedFunction<
  typeof PlanningService.getSummaryIdentity
>
const getPlanningDataCount = PlanningService.getPlanningDataCount as jest.MockedFunction<
  typeof PlanningService.getPlanningDataCount
>

const identityResponse = (identity: string, businessDate = '2026-04-07') => ({ data: { data: { identity, businessDate } } } as any)
const summaryResponse = (value: string) => ({
  status: 200,
  config: {},
  data: { status: 200, data: { TechCount: value, nested: { rows: [value] } } }
} as any)

const setup = () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    logger: { log: console.log, warn: console.warn, error: () => undefined }
  })
  const wrapper = ({ children }: PropsWithChildren) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  return { client, ...renderHook(useGetPlanningDataCount, { wrapper }) }
}

beforeEach(() => {
  jest.clearAllMocks()
  acquireToken.mockResolvedValue('actor-a' as any)
})

test('validates identity on every call, reuses one summary, and clones consumer data', async () => {
  getSummaryIdentity.mockResolvedValue(identityResponse('identity-a'))
  getPlanningDataCount.mockResolvedValue(summaryResponse('11'))
  const { result } = setup()
  const body = { filters: [{ field: 'SKUCode', values: ['6120'] }] }

  let first: any
  await act(async () => { first = await result.current.mutateAsync(body) })
  first.data.data.nested.rows.push('consumer-change')

  let second: any
  await act(async () => { second = await result.current.mutateAsync(body) })

  expect(getSummaryIdentity).toHaveBeenCalledTimes(2)
  expect(getSummaryIdentity).toHaveBeenNthCalledWith(1, body)
  expect(getSummaryIdentity).toHaveBeenNthCalledWith(2, body)
  expect(getPlanningDataCount).toHaveBeenCalledTimes(1)
  expect(getPlanningDataCount).toHaveBeenCalledWith({ ...body, _report_read_identity: 'identity-a' })
  expect(second.data.data.nested.rows).toEqual(['11'])
  expect(second.data).not.toBe(first.data)
  expect(second.headers['x-planning-business-date']).toBe('2026-04-07')
})

test('loads a new summary when the validated identity changes', async () => {
  getSummaryIdentity
    .mockResolvedValueOnce(identityResponse('identity-a'))
    .mockResolvedValueOnce(identityResponse('identity-b', '2026-04-08'))
  getPlanningDataCount
    .mockResolvedValueOnce(summaryResponse('11'))
    .mockResolvedValueOnce(summaryResponse('22'))
  const { result } = setup()

  let first: any
  await act(async () => { first = await result.current.mutateAsync({}) })
  let second: any
  await act(async () => { second = await result.current.mutateAsync({}) })

  expect(first.data.data.TechCount).toBe('11')
  expect(second.data.data.TechCount).toBe('22')
  expect(second.headers['x-planning-business-date']).toBe('2026-04-08')
  expect(getPlanningDataCount).toHaveBeenNthCalledWith(1, { _report_read_identity: 'identity-a' })
  expect(getPlanningDataCount).toHaveBeenNthCalledWith(2, { _report_read_identity: 'identity-b' })
})

test('does not cache a failed summary as a successful result', async () => {
  getSummaryIdentity.mockResolvedValue(identityResponse('identity-a'))
  getPlanningDataCount
    .mockResolvedValueOnce({ status: 503, data: { status: 503 } } as any)
    .mockResolvedValueOnce(summaryResponse('33'))
  const { result } = setup()

  await act(async () => {
    await expect(result.current.mutateAsync({})).rejects.toThrow('Planning summary unavailable')
  })
  let retry: any
  await act(async () => { retry = await result.current.mutateAsync({}) })

  expect(retry.data.data.TechCount).toBe('33')
  expect(getSummaryIdentity).toHaveBeenCalledTimes(2)
  expect(getPlanningDataCount).toHaveBeenCalledTimes(2)
})

test('rejects an authentication change and removes the retained summary', async () => {
  acquireToken
    .mockResolvedValueOnce('actor-a' as any)
    .mockResolvedValueOnce('actor-b' as any)
  getSummaryIdentity.mockResolvedValue(identityResponse('identity-a'))
  getPlanningDataCount.mockResolvedValue(summaryResponse('44'))
  const { client, result } = setup()

  await act(async () => {
    await expect(result.current.mutateAsync({})).rejects.toThrow(
      'Authentication changed during Planning read'
    )
  })

  expect(getSummaryIdentity).toHaveBeenCalledTimes(1)
  expect(getPlanningDataCount).toHaveBeenCalledTimes(1)
  expect(client.getQueryData(['planning-summary', 'identity-a'])).toBeUndefined()
})
