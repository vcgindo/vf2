import { researchHistoryPositions } from './historyPositions';
import retained from './historyPositions.fixture.json';

describe('Research selected-publication history positions', () => {
    it('maps exactly D84-D90 to July 1-7 independently of the wall clock', () => {
        jest.useFakeTimers().setSystemTime(new Date('2026-10-15T12:00:00Z'));
        expect(researchHistoryPositions('07 Jul 2026', 7)).toEqual([
            { field: 'D84', date: '1st Jul' },
            { field: 'D85', date: '2nd Jul' },
            { field: 'D86', date: '3rd Jul' },
            { field: 'D87', date: '4th Jul' },
            { field: 'D88', date: '5th Jul' },
            { field: 'D89', date: '6th Jul' },
            { field: 'D90', date: '7th Jul' },
        ]);
        jest.useRealTimers();
    });

    it('retains the terminal point and both ends of the 90-day history', () => {
        expect(researchHistoryPositions('2026-07-07', 1)).toEqual([
            { field: 'D90', date: '7th Jul' },
        ]);
        const full = researchHistoryPositions('2026-07-07', 90);
        expect(full).toHaveLength(90);
        expect(full[0]).toEqual({ field: 'D1', date: '9th Apr' });
        expect(full[89]).toEqual({ field: 'D90', date: '7th Jul' });
    });

    it('keeps calendar dates aligned over a leap-day boundary', () => {
        expect(researchHistoryPositions('02 Mar 2024', 4)).toEqual([
            { field: 'D87', date: '28th Feb' },
            { field: 'D88', date: '29th Feb' },
            { field: 'D89', date: '1st Mar' },
            { field: 'D90', date: '2nd Mar' },
        ]);
    });

    it('does not substitute today when the selected date is unavailable', () => {
        expect(researchHistoryPositions('Loading', 7)).toEqual([]);
        for (const horizon of [0, 91, 1.5]) {
            expect(researchHistoryPositions('07 Jul 2026', horizon)).toEqual([]);
        }
    });

    it('keeps all seven retained Self/Parent Tech/Eco observations on their source dates', () => {
        const positions = researchHistoryPositions(retained.business_date, 7);
        for (const type of ['Self', 'Parent']) {
            for (const pen of ['Tech', 'Eco']) {
                const rows = retained.rows.filter(row => row.Type === type && row.Pen === pen);
                expect(rows).toHaveLength(2);
                for (let index = 0; index < positions.length; index++) {
                    const position = positions[index];
                    expect((retained.dates as Record<string, string>)[position.field])
                        .toBe(`2026-07-0${index + 1}`);
                    const colors = rows.map(row => (row as Record<string, string>)[position.field]);
                    expect(colors.filter(color => color === 'White')).toHaveLength(type === 'Self' ? 1 : 2);
                    expect(colors.filter(color => color === 'Yellow')).toHaveLength(type === 'Self' ? 1 : 0);
                }
            }
        }
    });
});
