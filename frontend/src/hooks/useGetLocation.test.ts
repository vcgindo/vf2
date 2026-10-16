import { MultiFilterSupplyChainCheckboxList } from '../helpers/BPRConstants'
import { parseLocationTypes } from './useGetLocation'

describe('parseLocationTypes', () => {
  it('uses the local defaults when the reconstructed database has no location rows', () => {
    expect(parseLocationTypes({ data: { data: null } })).toEqual(
      MultiFilterSupplyChainCheckboxList
    )
  })

  it('maps the JSON-string payload returned by the MTA API', () => {
    expect(
      parseLocationTypes({ data: { data: JSON.stringify([{ lt: 'Plant' }, { lt: 'Depot' }]) } })
    ).toEqual([
      { label: 'Plant', id: 'Plant' },
      { label: 'Depot', id: 'Depot' },
    ])
  })
})
