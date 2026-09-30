import { render } from '@testing-library/react';
import ProcPlanningAnalytics from './index';

// Mock the useTranslation hook
jest.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key: any) => key,
    }),
}));

// Mock the useProcPlanning hook
jest.mock('../../../../VectorFlow/Pages/MTO/Procurement/Planning/useProcPlanning', () => ({
    __esModule: true,
    default: () => ({
        GetCount: {
            short: 5,
            complete: 10,
            total: 15,
        },
    }),
}));

describe('ProcPlanningAnalytics Component', () => {
    it('renders with correct data', () => {
        render(
            <ProcPlanningAnalytics
                themeUi="NOIRFUSION"
            />
        );

        // Check for the list title
    });
});
