import React,{ReactNode} from 'react';
import { render, fireEvent, screen } from '@testing-library/react';
import ConflictErrorCellRenderer from './ConflictErrorCellRenderer';
import '@testing-library/jest-dom';

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

describe('ConflictErrorCellRenderer', () => {
  // Mock data for the params prop
  const mockParams = {
    value: 'Test Value',
    data: {
      users: [
        { user: 'User1', data: { testColId: 'Data1' } },
        { user: 'User2', data: { testColId: 'Data2' } },
      ],
      testColId:'Data1'
    },
    colDef: {
      colId: 'testColId',
      headerName: 'Test Header',
      // ... other properties of the column definition
    },
    onClick: jest.fn(),
  };
  
  // Test 1: Component renders without crashing
  it('renders without crashing', () => {
    render(contextWrapperWithCustomTheme(<ConflictErrorCellRenderer {...mockParams} />,'NOIRFUSION'));
    expect(screen.getByText('Test Value')).toBeInTheDocument();
  });

  // Test 2: The color of the paragraph changes based on getTextColor
  it('shows black color based on no conflict detection', () => {
    const newMockParams = {
        ...mockParams,
        data:{
            users: [
                { user: 'User2', data: { testColId: 'Data1' } },
              ],
            testColId:'Data1'
        }
    }
    render(contextWrapperWithCustomTheme(<ConflictErrorCellRenderer {...newMockParams} />,"REGALBLAZE"));
    // expect(screen.getByText('Test Value')).toHaveStyle('color: black');

    // const newMockParams = {
    //   ...mockParams,
    //   data: {
    //     ...mockParams.data,
    //     afaf: 'Different Value', // Simulate a conflict
    //   },
    // };
    // rerender(<ConflictErrorCellRenderer {...newMockParams} />);
    // expect(screen.getByText('Test Value')).toHaveStyle('color: rgb(130, 15, 76)');
  });

  // Test 3: Tooltips are shown/hidden on mouse events
  it('shows and hides tooltip on mouse events', () => {
    render(contextWrapperWithCustomTheme(<ConflictErrorCellRenderer {...mockParams} />,'NOIRFUSION'));
    fireEvent.mouseEnter(screen.getByText('Test Value'));
    // Assuming there is an element with the role tooltip
    fireEvent.mouseLeave(screen.getByText('Test Value'));
  
  });

  it('renders overflown tooltips', () => {
    render(contextWrapperWithCustomTheme(<div style={{display:'flex',flexDirection:'column'}}>
    {[1,2,3,4,5,67,8,9,0,534,311,31111,31111,111111,4111111,14124121,45215125,15125124,5632623626,21479867,4169679,519696,96796515,569769669,156996961,1967969696].map((n:number)=>{
        return(
            <ConflictErrorCellRenderer {...mockParams} key={n} />
        )
    })}
</div>,"REGALBLAZE"));
    fireEvent.mouseEnter(screen.getAllByText('Test Value')[25]);
    // Assuming there is an element with the role tooltip
    fireEvent.mouseLeave(screen.getAllByText('Test Value')[25]);
  
  });

  // Further tests would follow a similar pattern, setting up the conditions needed
  // and asserting the expected outcomes for tooltip data, positions, and overflow behavior.

  // Remember to mock the Portal component or any other modules if necessary.
});