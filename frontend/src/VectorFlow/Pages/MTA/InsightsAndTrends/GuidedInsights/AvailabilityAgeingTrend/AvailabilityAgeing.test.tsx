import { render } from "@testing-library/react";
import { ReactNode } from "react";
import { useGetAvailabilityAgeing} from "../../../../../Services/MTA/InsightsAndTrends";
import { GuidedInsights } from "../../../../../../mock-data/GuidedInsights";
import AvailabilityAgeingTrend from './';

import {UserDataContext} from '../../../../../../context'

jest.mock("../../../../../Services/MTA/InsightsAndTrends");
jest.mock("ag-charts-react", () => ({
  AgCharts: jest.fn(() => null) 
}));
const useGetAvailabilityAgeingMock = useGetAvailabilityAgeing as jest.MockedFunction<
    typeof useGetAvailabilityAgeing
>;
//const useGetAvailabilityAgeingData: any = { data: {data: GuidedInsights.AvailabilityAgeingTrendData }};

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


const useGetAvailabilityAgeingData: any = {
  mutateAsync: () => {
    return { data: {data: GuidedInsights.AvailabilityAgeingTrendData }};
  },
};
describe("Availability Ageing ", () => {
global.ResizeObserver = class MockedResizeObserver {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };
    beforeEach(()=>{
        useGetAvailabilityAgeingMock.mockImplementation(()=>{
            return useGetAvailabilityAgeingData;
        })

    })


     it("Availability Ageing", () => {
       
        render(contextWrapperWithCustomTheme(<AvailabilityAgeingTrend themeUi="REGALBLAZE" filter={"Product Filter"} horizon={10} setHorizon={jest.fn()} setAgeing={jest.fn()} ageing={1}/>,"REGALBLAZE", ))

    })
})