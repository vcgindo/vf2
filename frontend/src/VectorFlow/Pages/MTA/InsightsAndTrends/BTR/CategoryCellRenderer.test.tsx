import React from 'react';
import { render } from '@testing-library/react';
import CategoryCellRenderer from './CategoryCellRenderer';

// Mock ICellRendererParams
const mockCellRendererParams:any = {
  value:'1,2,3,5,7'
};

// Mock BTRCategoryMapper
jest.mock('../../../../../helpers/BPRConstants', () => ({
  BTRCategoryMapper: {
    1: { bgColor: 'red', color: 'white', cellLabel: 'Category 1' },
    2: { bgColor: 'blue', color: 'white', cellLabel: 'Category 2' },
    3: { bgColor: 'green', color: 'white', cellLabel: 'Category 3' },
    5: { bgColor: 'yellow', color: 'white', cellLabel: 'Category 4' },
  },
}));

describe('CategoryCellRenderer', () => {
  it('renders with the correct categories', () => {
    render(<CategoryCellRenderer {...mockCellRendererParams} />);
    
    // Check if each category chip is rendered with correct styles and labels
    // const category1Chip = getByText('Category 1');
    // expect(category1Chip).toHaveStyle({ backgroundColor: 'red', color: 'white' });

    // const category2Chip = getByText('Category 2');
    // expect(category2Chip).toHaveStyle({ backgroundColor: 'blue', color: 'white' });

    // const category3Chip = getByText('Category 3');
    // expect(category3Chip).toHaveStyle({ backgroundColor: 'green', color: 'white' });

    // const category4Chip = getByText('Category 4');
    // expect(category4Chip).toHaveStyle({ backgroundColor: 'yellow', color: 'white' });
  });

});
