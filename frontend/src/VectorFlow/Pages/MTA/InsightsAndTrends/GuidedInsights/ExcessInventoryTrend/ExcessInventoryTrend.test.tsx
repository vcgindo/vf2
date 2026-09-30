import { render} from "@testing-library/react";
import {ReactNode} from 'react'
import {useGetExcessInventorySku, useGetExcessInventoryValue} from "../../../../../Services/MTA/InsightsAndTrends";
import { GuidedInsights } from "../../../../../../mock-data/GuidedInsights";
import ExcessInventoryTrend from './';
import {UserDataContext} from '../../../../../../context'

jest.mock("../../../../../Services/MTA/InsightsAndTrends");
jest.mock("ag-charts-react", () => ({
  AgCharts: jest.fn(() => null) // Replace null with a mock component if needed
}));


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
  

const useGetExcessInventorySkuMock = useGetExcessInventorySku as jest.MockedFunction<
    typeof useGetExcessInventorySku
>;
const useGetExcessInventorySkuData: any = {
     mutateAsync: () => {
    return {data: {data: GuidedInsights.ExcessInventorySkuData }};
  }
    
};


const useGetExcessInventoryValueMock = useGetExcessInventoryValue as jest.MockedFunction<
    typeof useGetExcessInventoryValue
>;
const useGetExcessInventoryValueData: any =  { 
    mutateAsync: () => {
    return {data:{data: GuidedInsights.ExcessInventoryValueData }}
}
};
describe("Excess  Inventory ", () => {
global.ResizeObserver = class MockedResizeObserver {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };
    beforeEach(()=>{
        useGetExcessInventorySkuMock.mockImplementation(()=>{
            return useGetExcessInventorySkuData;
        })
        useGetExcessInventoryValueMock.mockImplementation(()=>{
            return useGetExcessInventoryValueData;
        })
    })
    
      
     it("Renders Excess  Inventory", () => {
 
        render(contextWrapperWithCustomTheme(<ExcessInventoryTrend themeUi="REGALBLAZE" filter={"Product Filter"} horizon={10} setHorizon={jest.fn()}/>,"REGALBLAZE"))
       
    })
})