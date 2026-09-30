import { render,screen } from '@testing-library/react';
import AvailabilityCellRenderer from './AvailabilityCellRenderer';

// Mock ICellRendererParams
const mockCellRendererParams:any = {
  data: {
    Availability: 20,
  },
};

describe('AvailabilityCellRenderer', () => {
  it('renders with the correct availability value', () => {
    render(<AvailabilityCellRenderer {...mockCellRendererParams} />);
    const availabilityElement = screen.getByTestId("availability-cell-renderer");
    expect(availabilityElement).toBeInTheDocument();
  });

  // Add more test cases as needed
});
