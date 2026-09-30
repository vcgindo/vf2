// Assuming GridFilterWrapper and TextBtn are styled components, not types
import React from 'react';
import { GridFilterWrapper, TextBtn } from '../Common/VFPagination/styles';

interface ClearAllFiltersProps {
  isDisabled: boolean;
  clearGridFilter: () => void;
  themeUi: any;
}

export const CustomStatusPanel: React.FC<ClearAllFiltersProps> = ({
  isDisabled,
  clearGridFilter,
  themeUi,
}) => {
    
  return (
    <GridFilterWrapper style={{ marginTop: '15px', paddingTop: '3px' }}>
      <TextBtn onClick={clearGridFilter} disabled={isDisabled} themeUi={themeUi}>
        Clear All Grid Filters
      </TextBtn>
    </GridFilterWrapper>
  );
};
