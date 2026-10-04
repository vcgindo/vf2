import { displayRows } from './displayRows';
import { mapBTRRowData } from '../../../../../helpers/utils';
jest.mock('../../../../../helpers/utils', () => ({ mapBTRRowData: jest.fn(() => ['fallback']) }));

test('prepared rows are consumed by reference without calling the legacy mapper', () => {
    const tech = [{ SKUCode: '001', Availability: 66.67, D90: 12 }];
    expect(displayRows({ displayPrepared: true, tech }, 'tech', 90)).toBe(tech);
    expect(mapBTRRowData).not.toHaveBeenCalled();
});
test('non-finite cells are restored only in their own branch', () => {
    const tech = [{ Availability: null }];
    const eco = [{ Availability: null }];
    const data = { displayPrepared: true, tech, eco, displayNonFinite: [['eco', 0, 'Availability', 'NaN']] };
    displayRows(data, 'tech', 1);
    expect(tech[0].Availability).toBeNull();
    expect(Number.isNaN(displayRows(data, 'eco', 1)[0].Availability)).toBe(true);
});
test('an accepted reader without a prepared marker retains the exact mapper fallback', () => {
    (mapBTRRowData as jest.Mock).mockReturnValue(['fallback']);
    const raw = [{ D90: '1' }];
    expect(displayRows({ tech: raw }, 'tech', 1)).toEqual(['fallback']);
    expect(mapBTRRowData).toHaveBeenLastCalledWith(raw, 1);
});
