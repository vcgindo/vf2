import { render, fireEvent, screen } from "@testing-library/react";
import { act } from "react-dom/test-utils";
import {ReactNode} from 'react'
import {useGetDBMNormSuggestionSKUs, useGetDBMNormSuggestionAgeing, useGetDBMNormSuggestionLoc, useGetDBMNormSuggestionPie} from "../../../../../Services/MTA/InsightsAndTrends";
import { GuidedInsights } from "../../../../../../mock-data/GuidedInsights";
import DBMNormSuggestions from './';

import {UserDataContext} from '../../../../../../context'

jest.mock("../../../../../Services/MTA/InsightsAndTrends");

const useGetDBMNormSuggestionSKUsMock = useGetDBMNormSuggestionSKUs as jest.MockedFunction<
    typeof useGetDBMNormSuggestionSKUs
>;
const useGetDBMNormSuggestionSKUsData: any = { 
  mutateAsync: () => {
    return { data:{data: GuidedInsights.DBMSuggestionsSKUs }};
  },
};  
  

const useGetDBMNormSuggestionAgeingMock = useGetDBMNormSuggestionAgeing as jest.MockedFunction<
    typeof useGetDBMNormSuggestionAgeing
>;
const useGetDBMNormSuggestionAgeingData: any =  { 
  mutateAsync: () => {
    return { data:{data: GuidedInsights.DBMSuggestionAgeing }};
  },
};

const useGetDBMNormSuggestionLocMock = useGetDBMNormSuggestionLoc as jest.MockedFunction<
    typeof useGetDBMNormSuggestionLoc
>;
const useGetDBMNormSuggestionLocData: any =  {
  mutateAsync: () => {
    return { data:{data: GuidedInsights.DBMSuggestionsLoc }};
  },
};

const useGetDBMNormSuggestionPieMock = useGetDBMNormSuggestionPie as jest.MockedFunction<
    typeof useGetDBMNormSuggestionPie
>;
const useGetDBMNormSuggestionPieData: any =  { 
  mutateAsync: () => {
    return { data:{data: GuidedInsights.DBMSuggestionsPie }};
  },
};

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



describe("DBM Suggestions ", () => {
global.ResizeObserver = class MockedResizeObserver {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };
    beforeEach(()=>{
        useGetDBMNormSuggestionSKUsMock.mockImplementation(()=>{
            return useGetDBMNormSuggestionSKUsData;
        })
        useGetDBMNormSuggestionAgeingMock.mockImplementation(()=>{
            return useGetDBMNormSuggestionAgeingData;
        })
          useGetDBMNormSuggestionLocMock.mockImplementation(()=>{
            return useGetDBMNormSuggestionLocData;
        })
          useGetDBMNormSuggestionPieMock.mockImplementation(()=>{
            return useGetDBMNormSuggestionPieData;
        })
    })
    
      
     it("Renders DBM Suggestions", () => {
      
        render(contextWrapperWithCustomTheme(<DBMNormSuggestions filter={"Product Filter"}/>,'NOIRFUSION'))
       
    })
     it("On minimize chart click for graph 2", async() => {        
        render(contextWrapperWithCustomTheme(<DBMNormSuggestions filter={"Product Filter"}/>,'NOIRFUSION'))
         await act(async () => {
            
            fireEvent.click(screen.getAllByTestId('minimizechart1')[0])
        })
       
    })
    //   it("On minimize chart click for graph 2", async() => {
    //    render(contextWrapperWithCustomTheme(<DBMNormSuggestions/>,'NOIRFUSION'))
    //      await act(async () => {
            
    //         fireEvent.click(screen.getAllByTestId('minimizechart2')[0])
    //     })
       
    // })
      it("On minimize chart click for graph 2", async() => {
   
        render(contextWrapperWithCustomTheme(<DBMNormSuggestions filter={"Product Filter"}/>,'NOIRFUSION'))
         await act(async () => {
            
            fireEvent.click(screen.getAllByTestId('minimizechart3')[0])
        })
       
    })
      it("On minimize chart click for graph 2", async() => {
      
        render(contextWrapperWithCustomTheme(<DBMNormSuggestions filter={"Product Filter"}/>,'NOIRFUSION'))
         await act(async () => {
            
            fireEvent.click(screen.getAllByTestId('minimizechart4')[0])
        })
       
    })
})