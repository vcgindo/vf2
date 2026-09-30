
import {screen, render } from '@testing-library/react';
import AvailabilityToolTip from './AvailabilityToolTip';

// Mock ITooltipParams
const mockTooltipParams:any = {
  value: 75, // Mocked value
};

describe('AvailabilityToolTip', () => {
  it('renders with the correct availability value', () => {
    render(<AvailabilityToolTip {...mockTooltipParams} />);
    const availabilityElement = screen.getByText('75% Availability');
    expect(availabilityElement).toBeInTheDocument();
  });

  // Add more test cases as needed
});
