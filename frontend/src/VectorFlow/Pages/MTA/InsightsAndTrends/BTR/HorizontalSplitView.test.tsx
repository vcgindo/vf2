import {ReactNode} from 'react'
import { render } from '@testing-library/react';
import HorizontalSplitView, { SplitViewProps } from './HorizontalSplitView';

import { UserDataContext } from '../../../../../context';


const contextWrapperWithCustomTheme = (children: ReactNode,theme:string) => {
  return (

          <UserDataContext.Provider
            value={{
              user: { user: { theme_ui: theme } },
              changeColorTheme: (color) => {
                return color;
              },
              isSideBarOpen:true,toggleSideBar:jest.fn
            }}
          >
            {children}
          </UserDataContext.Provider>

  );
};

// Mocked props
const mockTechTableProps = {
  header: 'Tech Table',
  columnDefs: [], // Mocked column definitions
  rowData: [], // Mocked row data
  paginationProps:{
    selectedRows:0,
    totalRows:0,
    rowsPerPage:100,
    currentPage:1,
    handleChangePage:() => {
       return 
    }
    
}
};

const mockEcoTableProps = {
  header: 'Eco Table',
  columnDefs: [], // Mocked column definitions
  rowData: [], // Mocked row data
  paginationProps:{
    selectedRows:0,
    totalRows:0,
    rowsPerPage:100,
    currentPage:1,
    handleChangePage:() => {
       return 
    }
    
}
};

const mockSplitViewProps: SplitViewProps = {
  techTable: mockTechTableProps,
  ecoTable: mockEcoTableProps,
  isLocked:true,
  toggleLockMode:jest.fn(),
  themeUi:'REGALBLAZE'
  
};

describe('VerticalSplitView', () => {
    global.ResizeObserver = class MockedResizeObserver {
        observe = jest.fn();
        unobserve = jest.fn();
        disconnect = jest.fn();
      };
  it('renders with the correct headers', () => {
    const { getByText } = render(contextWrapperWithCustomTheme(<HorizontalSplitView {...mockSplitViewProps} />,"NOIRFUSION"));
    const techTableHeader = getByText('Tech Table');
    const ecoTableHeader = getByText('Eco Table');

    expect(techTableHeader).toBeInTheDocument();
    expect(ecoTableHeader).toBeInTheDocument();
  });

//   it('renders VFTable components with correct props', () => {
//     const { container } = render(<VerticalSplitView {...mockSplitViewProps} />);
//     const vfTables = container.querySelectorAll('VFTable');

//     expect(vfTables.length).toBe(2); // Assuming there are two VFTable components rendered

//     vfTables.forEach((vfTable, index) => {
//       const tableProps = index === 0 ? mockTechTableProps : mockEcoTableProps;

//       expect(vfTable).toHaveAttribute('disableZoomScaling');
//       expect(vfTable).toHaveAttribute('tooltipMouseTrack', 'true');
//       expect(vfTable).toHaveAttribute('pagination');
//       expect(vfTable).toHaveAttribute('paginationPageSize', '50');
//       expect(vfTable).toHaveAttribute('tooltipShowDelay', '0');
//       expect(vfTable).toHaveAttribute('tooltipHideDelay', '0');

//       // Assuming VFTable receives props columnDefs and rowData
//       expect(vfTable).toHaveAttribute('columnDefs', JSON.stringify(tableProps.columnDefs));
//       expect(vfTable).toHaveAttribute('rowData', JSON.stringify(tableProps.rowData));
//     });
//   });
});
