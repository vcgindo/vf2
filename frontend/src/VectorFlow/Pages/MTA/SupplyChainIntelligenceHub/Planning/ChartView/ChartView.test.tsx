import { render } from "@testing-library/react"
import ChartView from '.';
import { MonitorGITChildMockData,ExpediteParentMockData,MonitorGITChildCustomMockData, getPlanningDataGridMockData } from "../../../../../../mock-data/Planning";
import { UserDataContext } from "../../../../../../context/UserDataContext";
import { QueryClientProvider } from "@tanstack/react-query";
import { setupReactQuery } from "../../../../../../config/react-query-config";
import { ReactNode } from "react";
import { BrowserRouter as Router } from "react-router-dom";
import { Provider } from "react-redux";
import { store } from "../../../../../../redux/store/store";
import { useGetPlanningDataCustom } from "../../../../../Services/MTA/SupplyChainIntelligenceHub/Planning";
import { VFPaginationProps } from "../../../../../../components/VectorFLOW/commons/VFPagination";

// const mockFn = jest.fn()
const queryClient = setupReactQuery();

jest.mock("ag-charts-react", () => ({
  AgCharts: jest.fn(() => null)
}));

jest.mock("../../../../../Services/MTA/SupplyChainIntelligenceHub/Planning");

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

const useGetPlanningDataCustomMock = useGetPlanningDataCustom as jest.MockedFunction<
    typeof useGetPlanningDataCustom
  >;

  const useGetPlanningDataCustomMockData: any = {
    mutateAsync: () => {
      return { data: {data:MonitorGITChildCustomMockData} };
    },
  };

  const initialPlanningCounts = {
    childMonitorCount:0,
    parentMonitorCount:0,
    childMonitorCustomCount:0,
    parentExpediteCount:0,
    parentExpediteCustomCount:0,
    childExpediteCount:0,
    childExpediteCustomCount:0,
    reviewExcessInventoryCount:0,
    reviewExcessInventoryCustomCount:0,
    reviewOrderFulfillmentCount:0,
    reviewOrderFulfillmentCustomCount:0
    
}
const paginationProps:VFPaginationProps = {
  totalRows:100,
  currentPage:1,
  selectedRows:0,
  handleChangePage:jest.fn(),
  rowsPerPage:50,
}

describe("Monitor GIT Child",()=>{
  global.ResizeObserver = class MockedResizeObserver {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };

  const commonProps = {
    paginationProps:paginationProps, 
    planningCounts:initialPlanningCounts,
    onOpenDailyDataGraph:jest.fn()
  }

  it("Renders Chart View",() => {
   
    useGetPlanningDataCustomMock.mockImplementation(()=>{
      return useGetPlanningDataCustomMockData
    })
    render(contextWrapper(<ChartView category="" currentTab="" currentGraphData={[]} {...commonProps}/>,store))
    // render(contextWrapper(<ChartView category="GITToChild" currentTab="locationWise" currentGraphData={MonitorGITChildMockData} {...commonProps}/>,store))
    // render(contextWrapper(<ChartView category="GITToChild" currentTab="transporterWise" currentGraphData={MonitorGITChildMockData} {...commonProps}/>,store))
    render(contextWrapper(<ChartView category="GITToChild" currentTab="custom" currentGraphData={MonitorGITChildCustomMockData} {...commonProps}/>,store))
    render(contextWrapper(<ChartView category="GITToChild" currentTab="" currentGraphData={MonitorGITChildMockData} {...commonProps}/>,store))
    render(contextWrapper(<ChartView category="GITFromParent" currentTab="" currentGraphData={getPlanningDataGridMockData['data']} {...commonProps}/>,store))
    render(contextWrapper(<ChartView category="ExpediteFromParent" currentTab="expediteDispatches" currentGraphData={ExpediteParentMockData} {...commonProps}/>,store))
    render(contextWrapper(<ChartView category="ExpediteFromParent" currentTab="createAvailabilityAtParent" currentGraphData={ExpediteParentMockData} {...commonProps}/>,store))
    render(contextWrapper(<ChartView category="ExpediteFromParent" currentTab="custom" currentGraphData={[]} {...commonProps}/>,store))
    render(contextWrapper(<ChartView category="ExcessInventory" currentTab="CustomScreens" currentGraphData={[]} {...commonProps}/>,store))
    render(contextWrapper(<ChartView category="OrderFulfillment" currentTab="CustomScreens" currentGraphData={[]} {...commonProps}/>,store))

  })

})