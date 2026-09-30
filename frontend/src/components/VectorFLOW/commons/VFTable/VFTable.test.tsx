import { render, screen } from '@testing-library/react';
import {ReactNode} from 'react';
import VFTable from './';
import { UserDataContext } from '../../../../context';

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

describe('should render the VFTable component', () => {
    window.URL.createObjectURL = jest.fn();
    
  const rowData = [
    { id: 1, name: 'John Doe', age: 30 },
    { id: 2, name: 'Jane Doe', age: 25 },
  ];

  const columnDefs = [
    { header: 'ID', field: 'id' },
    { header: 'Name', field: 'name' },
    { header: 'Age', field: 'age' },
  ];

  const agGridProps = {
    rowData:rowData,
    columnDefs:columnDefs,
    columnVisible:jest.fn()
  }
  
  it("Should render with different themes",()=>{
    render(contextWrapperWithCustomTheme(<VFTable {...agGridProps}/>,"NOIRFUSION"));

    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();
  })

  it("Should render with different themes",()=>{
    render(contextWrapperWithCustomTheme(<VFTable {...agGridProps}/>,"REGALBLAZE"));

    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();
  })

  it("Should render with different themes",()=>{
    render(contextWrapperWithCustomTheme(<VFTable {...agGridProps}/>,"PUREELEGANCE"));

    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();
  })

  it("Should render with different themes",()=>{
    render(contextWrapperWithCustomTheme(<VFTable {...agGridProps}/>,"CHARCOALCHIC"));

    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();
  })

  it("Should render with different themes",()=>{
    render(contextWrapperWithCustomTheme(<VFTable {...agGridProps}/>,"CHARCOALgfagaCHIC"));

    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();
  })
});
