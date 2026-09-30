import {  render} from "@testing-library/react";
import { ReactNode } from "react";
import { useGetAvailabilityTrend} from "../../../../../Services/MTA/InsightsAndTrends";
import { GuidedInsights } from "../../../../../../mock-data/GuidedInsights";
import AvailabilityTrend from ".";
import {UserDataContext} from '../../../../../../context'

jest.mock("../../../../../Services/MTA/InsightsAndTrends");
const useGetAvailabilityTrendMock = useGetAvailabilityTrend as jest.MockedFunction<
    typeof useGetAvailabilityTrend
>;
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


//const useGetAvailabilityTrendData: any =  { data: {data: GuidedInsights.AvailabilityTrendData }}; 
const useGetAvailabilityTrendData: any = {
  mutateAsync: () => {
    return { data: {data: GuidedInsights.AvailabilityTrendData }};
  },
};
describe("Availability Trend", () => {
     beforeEach(()=>{
      useGetAvailabilityTrendMock.mockImplementation(()=>{
            return useGetAvailabilityTrendData;
        })
    });
     it("Renders Availability Trend", () => {
        
        render(contextWrapperWithCustomTheme(<AvailabilityTrend themeUi="REGALBLAZE" filter={"Product Filter"} horizon={10} setHorizon={jest.fn()}/>,"REGALBLAZE"))
       
    })
})
