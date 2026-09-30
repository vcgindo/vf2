import {ReactNode} from 'react'
import { render,screen,fireEvent } from '@testing-library/react';
import ErrorCell from '.';

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


const props:any = {
    value:'dummy',
    data:{error:"SKU Code has pipe and commatesttesttest"}

}

describe("Renders Error Cell",() => {

    it("Render the component when message is more than 30 char",()=>{
        render(contextWrapperWithCustomTheme(<ErrorCell {...props}/>,'NOIRFUSION'));
        expect(screen.getByText('SKU Code has pipe and commates...')).toBeInTheDocument();
        
    })

    it("Renders the component with message is less than 30 char",()=>{
        const message = "dummydumm"
        props.data.error = message;
        render(contextWrapperWithCustomTheme(<ErrorCell {...props}/>,'REGALBLAZE'));
        expect(screen.getByText('dummydumm')).toBeInTheDocument();
        
    })

    it("Renders the Tooltip",()=>{
        const message = "dummydumm"
        props.data.error = message;
        render(contextWrapperWithCustomTheme(<ErrorCell {...props}/>,'NOIRFUSION'));
        fireEvent.mouseEnter(screen.getByTestId('errorImage'))
        fireEvent.mouseEnter(screen.getByTestId('tooltip-wrapper'))
        fireEvent.mouseLeave(screen.getByTestId('errorImage'))
        
    })
    
    it("Renders an Empty fragment when message is undefined",()=>{
        props.data.error = undefined;
        render(contextWrapperWithCustomTheme(<ErrorCell {...props}/>,'REGALBLAZE'));
        
    })
})

describe('ErrorCell component', () => {
    test('tooltip repositioning when overflow occurs', () => {
      // Mock window.innerHeight
      const originalInnerHeight:any = Object.getOwnPropertyDescriptor(window, 'innerHeight');
      Object.defineProperty(window, 'innerHeight', { value: 10 });
  
      const props:any = {
        data: {
          error: 'This is a test error message.'
        }
      };
  
      const { getByTestId } = render(contextWrapperWithCustomTheme(<ErrorCell {...props}/>,'NOIRFUSION'));
  
      const errorImage = getByTestId('errorImage');
  
      fireEvent.mouseEnter(errorImage);
  
      // You can assert the repositioned tooltip position here
    //   expect(tooltipWrapper.style.top).toBe('approximately expected value');
  
      // Restore the original window.innerHeight
      Object.defineProperty(window, 'innerHeight', originalInnerHeight);
    });
  });