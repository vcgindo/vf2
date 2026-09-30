import { render } from "@testing-library/react";
import {ReactNode} from 'react'
import { useGetChronicUnavailabilityGridView} from "../../../../../Services/MTA/InsightsAndTrends";
import { GuidedInsights } from "../../../../../../mock-data/GuidedInsights";
import ChronicGridView from './';
import { Provider } from "react-redux";
import { UserDataContext } from "../../../../../../context";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter as Router } from "react-router-dom";
import { setupReactQuery } from "../../../../../../config/react-query-config";
import {store} from "../../../../../../redux/store/store";
jest.mock("../../../../../Services/MTA/InsightsAndTrends");
const useGetChronicUnavailabilityGridViewMock = useGetChronicUnavailabilityGridView as jest.MockedFunction<
    typeof useGetChronicUnavailabilityGridView
>;
const useGetChronicUnavailabilityGridViewData: any = { data: {data: GuidedInsights.ChronicGridViewData }};


const queryClient = setupReactQuery();

const contextWrapper = (children: ReactNode,store:any) => {
    return (
      <QueryClientProvider client={queryClient}>
        <Router>
          <Provider store={store}>
            <UserDataContext.Provider
              value={{
                user: { user: { theme_ui: "NOIRFUSION" } },
                changeColorTheme: (color) => {
                  return color;
                },
                isSideBarOpen:true,toggleSideBar:jest.fn
              }}
            >
              {children}
            </UserDataContext.Provider>
          </Provider>
        </Router>
      </QueryClientProvider>
    );
  };

describe("Chronic Unavailability ", () => {
global.ResizeObserver = class MockedResizeObserver {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };
    beforeEach(()=>{
        useGetChronicUnavailabilityGridViewMock.mockImplementation(()=>{
            return useGetChronicUnavailabilityGridViewData;
        })

    })
        
     it("Renders Chronic Unavailability", () => {
        
      render(contextWrapper(<ChronicGridView currentGridData={useGetChronicUnavailabilityGridViewData?.data?.data}/>,store))
       
    })
})