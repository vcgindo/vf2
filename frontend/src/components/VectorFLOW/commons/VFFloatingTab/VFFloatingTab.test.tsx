import { ReactNode } from "react";
import {screen, render, fireEvent } from "@testing-library/react";
import VFFloatingTab, { VFFloatingTabProps } from ".";
import { UserDataContext } from "../../../../context";

const dummyId = '1'

const mockFn = jest.fn()

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

const dummyProps:VFFloatingTabProps = {
    tabs:[
        {
            id:dummyId,
            label:"One",
            value:"one"
        },
        {
            id:'2',
            label:"Two",
            value:"two"
        },
        {
            id:'3',
            label:"Three",
            value:"three"
        }
    ],
    defaultTab:1,
    handleClick:mockFn
}


describe('Filter Component', () => {
    it("Renders the component with all the props",()=>{
        render(contextWrapperWithCustomTheme(<VFFloatingTab {...dummyProps}/>,"REGALBLAZE"))
        const element = screen.getByText('One')
        fireEvent.click(element)
    })
    it("Renders the component with required props",()=>{
        render(contextWrapperWithCustomTheme(<VFFloatingTab tabs={dummyProps.tabs}/>,"NOIRFUSION"))
        const element = screen.getByText('Two')
        fireEvent.click(element)
    })
});



