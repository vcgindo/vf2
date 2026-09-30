import {ReactNode} from 'react'
import { render, screen } from '@testing-library/react';
import BPRViewTable from './BPRViewTable';

import { UserDataContext } from '../../../../../context';

const contextWrapper = (children: ReactNode) => {
  return (

          <UserDataContext.Provider
            value={{
              user: { user: { theme_ui: "NOIRFUSION" } },
              changeColorTheme: (color:any) => {
                return color;
              },
              isSideBarOpen:true,toggleSideBar:jest.fn
            }}
          >
            {children}
          </UserDataContext.Provider>

  );
};

describe('BPRViewTable Component', () => {
  const colDefs = [
    { headerName: 'ID',colId: 'id'  },
    { headerName: 'Name', colId: 'name' },
    { headerName: 'Remarks', colId: 'remarks' },
  ];

  const rowData = [
    { id: 1, name: 'John Doe', remarks: 'Some remarks for testing' },
    { id: 2, name: 'Jane Smith', remarks: 'Some other remarks for testing' },
  ];

  it('renders table header and row data correctly', () => {
    render(contextWrapper(<BPRViewTable colDefs={colDefs} rowData={rowData} tablePrefixSrc="/assets/img/VectorFLOW/BPR/stock.svg" tableHeader=''/>));


  });

  it('renders NULL for missing data', () => {
    const rowDataWithNull = [
      { id: 1, name: 'John Doe', remarks: 'Some remarks for testing' },
      { id: 2, name: 'Jane Smith' }, // Missing remarks data
    ];

    render(contextWrapper(<BPRViewTable colDefs={colDefs} rowData={rowDataWithNull} tablePrefixSrc="/assets/img/VectorFLOW/BPR/stock.svg"  tableHeader=''/>));

    const remarksRow2 = screen.getByText('NULL');

    expect(remarksRow2).toBeInTheDocument();
  });
});
