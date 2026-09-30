import { render } from '@testing-library/react';
import {ReactNode} from 'react'
import VFLoader from '.';
import { UserDataContext } from "../../../../context";



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

  describe("VFLoader",()=>{
    it("Renders with RegalBlaze",()=>{
        render(contextWrapperWithCustomTheme(<VFLoader/>,'REGALBLAZE'))
    })

    it("Renders with NoirFusion",()=>{
        render(contextWrapperWithCustomTheme(<VFLoader/>,'NOIRFUSION'))
    })
  })
  
