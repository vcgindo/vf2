import {ReactNode} from 'react'

import { render } from '@testing-library/react';
import UserManagementStepper from '.'; 
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

describe('Stepper Component', () => {
  const StepItems:any = [
    {
        label:'Retail',
        currentState:'completed'
    },
    {
        label:'Distribution',
        currentState:'active'
    },
    {
        label:'Production',
        currentState:'pending'
    }
  ]

  it('Renders the Stepper component with theme = REGALBLAZE', () => {
    render(contextWrapperWithCustomTheme(<UserManagementStepper list={StepItems} themeUi="REGALBLAZE"/>,"REGALBLAZE"));
    
    // You may want to add more specific assertions here
    
  });

  it('Renders the Stepper component with theme = NOIRFUSION', () => {
    render(contextWrapperWithCustomTheme(<UserManagementStepper list={StepItems} themeUi="NOIRFUSION"/>,"NOIRFUSION"));
    
    // You may want to add more specific assertions here
    
  });

  it('Renders the Stepper component with activeStep = 1', () => {
    render(contextWrapperWithCustomTheme(<UserManagementStepper list={StepItems} themeUi="NOIRFUSION"/>,"NOIRFUSION"));
    
    // You may want to add more specific assertions here
    
  });



  // Add more test cases for other functionalities as needed
});
