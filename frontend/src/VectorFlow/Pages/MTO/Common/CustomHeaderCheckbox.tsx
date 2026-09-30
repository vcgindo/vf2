import React, { useState, useEffect, useRef, useCallback } from 'react';
import { IHeaderParams } from 'ag-grid-community';

const CustomHeaderCheckbox = (params: IHeaderParams) => {
  const [isChecked, setIsChecked] = useState(false);
  const checkboxRef = useRef<HTMLInputElement>(null);

  const updateCheckboxState = useCallback(() => {
    const api = params.api;
    if (!api || !checkboxRef.current) return;

    let displayedAndSelectedCount = 0;
    let displayedDataRowCount = 0;

    api.forEachNodeAfterFilterAndSort((node) => {
      if (!node.group) {
        displayedDataRowCount++;
        if (node.isSelected()) {
          displayedAndSelectedCount++;
        }
      }
    });
    
    if (displayedDataRowCount > 0 && displayedAndSelectedCount === displayedDataRowCount) {
      setIsChecked(true);
      checkboxRef.current.indeterminate = false;
    } else if (displayedAndSelectedCount > 0) {
      setIsChecked(false);
      checkboxRef.current.indeterminate = true;
    } else {
      setIsChecked(false);
      checkboxRef.current.indeterminate = false;
    }
  }, [params.api]);

  useEffect(() => {
    params.api.addEventListener('selectionChanged', updateCheckboxState);
    params.api.addEventListener('filterChanged', updateCheckboxState);
    params.api.addEventListener('modelUpdated', updateCheckboxState);

    updateCheckboxState();

    return () => {
      params.api.removeEventListener('selectionChanged', updateCheckboxState);
      params.api.removeEventListener('filterChanged', updateCheckboxState);
      params.api.removeEventListener('modelUpdated', updateCheckboxState);
    };
  }, [params.api, updateCheckboxState]);
  
  const handleCheckboxClick = (e: React.MouseEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (isChecked) {
      params.api.deselectAll();
    } else {
      params.api.selectAllFiltered();
    }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
      <input
        ref={checkboxRef}
        type="checkbox"
        checked={isChecked}
        onClick={handleCheckboxClick}
        readOnly 
        style={{ cursor: 'pointer' }}
      />
    </div>
  );
};

export default CustomHeaderCheckbox;