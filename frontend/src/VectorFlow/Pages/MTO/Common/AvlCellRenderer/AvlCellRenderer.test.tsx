import { render, screen } from '@testing-library/react';
import AvlCellRenderer from './AvlCellRenderer';

// Mock ICellRendererParams
const mockCellRendererParams: any = {
    data: {
        fkapr: 20,
    },
};

describe('AvlCellRenderer', () => {
    it('renders with the correct availability value', () => {
        render(<AvlCellRenderer {...mockCellRendererParams} />);
        const availabilityElement = screen.getByTestId("avl-cell-renderer");
        expect(availabilityElement).toBeInTheDocument();
    });
    // Add more test cases as needed
});
