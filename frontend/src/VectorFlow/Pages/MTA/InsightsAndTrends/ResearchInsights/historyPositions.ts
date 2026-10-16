import { addDays, format, isValid, parse, parseISO } from 'date-fns';

// D90 is the selected publication day; earlier columns are consecutive days.
export function researchHistoryPositions(runDate: string, horizon: number) {
    if (!Number.isInteger(horizon) || horizon < 1 || horizon > 90) return [];
    const end = /^\d{4}-\d{2}-\d{2}/.test(runDate)
        ? parseISO(runDate.slice(0, 10))
        : parse(runDate, 'dd MMM yyyy', new Date(2000, 0, 1));
    if (!isValid(end)) return [];
    return Array.from({ length: horizon }, (_, index) => ({
        field: `D${91 - horizon + index}`,
        date: format(addDays(end, index - horizon + 1), 'do MMM'),
    }));
}
