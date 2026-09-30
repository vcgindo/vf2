import React from 'react';
import { render } from '@testing-library/react';
import CategoryToolTip from './CategoryToolTip';

// Mock ITooltipParams
const mockTooltipParams:any = {
  value: '1|2|3|5|9', // Mocked value
};

// Mock BTRCategoryMapper
jest.mock('../../../../../helpers/BPRConstants', () => ({
  BTRCategoryMapper: {
    1: { bgColor: 'red', color: 'white', toolTipHeader: 'Header 1', toolTipDescription: 'Description 1' },
    2: { bgColor: 'blue', color: 'white', toolTipHeader: 'Header 2', toolTipDescription: 'Description 2' },
    3: { bgColor: 'green', color: 'white', toolTipHeader: 'Header 3', toolTipDescription: 'Description 3' },
    5: { bgColor: 'yellow', color: 'white', toolTipHeader: 'Header 4', toolTipDescription: 'Description 4' },
  },
}));

describe('CategoryToolTip', () => {
  it('renders with the correct categories', () => {
    const { getByText } = render(<CategoryToolTip {...mockTooltipParams} />);
    
    // Check if each category section is rendered with correct styles and content
    const category1Header = getByText('Header 1');
    expect(category1Header).toBeInTheDocument();
    const category1Description = getByText('Description 1');
    expect(category1Description).toBeInTheDocument();

    const category2Header = getByText('Header 2');
    expect(category2Header).toBeInTheDocument();
    const category2Description = getByText('Description 2');
    expect(category2Description).toBeInTheDocument();

    const category3Header = getByText('Header 3');
    expect(category3Header).toBeInTheDocument();
    const category3Description = getByText('Description 3');
    expect(category3Description).toBeInTheDocument();
  });

  // Add more test cases as needed
});
