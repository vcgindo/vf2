import { render} from "@testing-library/react"
// import MonitorGITChildLocationWiseCharts from "./Charts/LocationWise";
// import { MonitorGITChildLocationWiseMockData, MonitorGITChildTransporterWiseMockData, MonitorGITChildCustomMockData } from "../../../../../../../mock-data/Planning";
import { MonitorGITChildCustomMockData } from "../../../../../../../mock-data/Planning";
import MonitorGITChildCustomCharts from "./Grid/Custom";
import { UserDataContext } from "../../../../../../../context/UserDataContext";
import { QueryClientProvider } from "@tanstack/react-query";
import { setupReactQuery } from "../../../../../../../config/react-query-config";
import { ReactNode } from "react";
import { BrowserRouter as Router } from "react-router-dom";
import { Provider } from "react-redux";
import { store } from "../../../../../../../redux/store/store";
import { useGetPlanningDataCustom } from "../../../../../../Services/MTA/SupplyChainIntelligenceHub/Planning";
jest.mock("../../../../../../Services/MTA/SupplyChainIntelligenceHub/Planning");
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

// const mockFn = jest.fn()

// const contextWrapper = (children:any)=>{
//     return (
//         <UserDataContext.Provider
//             value={{
//               user: { user: { theme_ui: "NOIRFUSION" } },
//               changeColorTheme: (color) => {
//                 return color;
//               },
//               isSideBarOpen:true,toggleSideBar:jest.fn
//             }}
//           >
//             {children}
//           </UserDataContext.Provider>
//     )
// }

const useGetPlanningDataCustomMock = useGetPlanningDataCustom as jest.MockedFunction<
    typeof useGetPlanningDataCustom
  >;

  const useGetPlanningDataCustomMockData: any = {
    mutateAsync: () => {
      return { data: {data:MonitorGITChildCustomMockData} };
    },
  };

describe("Monitor GIT Child",()=>{
  global.ResizeObserver = class MockedResizeObserver {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };

  // it("Renders Location Wise View",() => {
  //   render(contextWrapper(<MonitorGITChildLocationWiseCharts data={MonitorGITChildLocationWiseMockData}/>,store))
  // })

  // it("Renders Location Wise View",() => {
  //   render(contextWrapper(<MonitorGITChildLocationWiseCharts data={MonitorGITChildTransporterWiseMockData}/>,store))
  // })

  it("Renders Custom View",() => {
    useGetPlanningDataCustomMock.mockImplementation(()=>{
      return useGetPlanningDataCustomMockData
    })
    render(contextWrapper(<MonitorGITChildCustomCharts recordCount={1000}/>,store))
  })

})