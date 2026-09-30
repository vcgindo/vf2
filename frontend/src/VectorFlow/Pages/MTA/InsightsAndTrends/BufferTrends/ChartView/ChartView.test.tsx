import { render } from "@testing-library/react";
import { graphsMock } from "../../../../../../mock-data/BufferTrends";
import { setupReactQuery } from "../../../../../../config/react-query-config";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter as Router } from "react-router-dom";
import { UserDataContext } from "../../../../../../context/UserDataContext";
import ChartView from ".";




const queryClient = setupReactQuery();
const mockContextValue = {
    user: { user: { theme_ui: "NOIRFUSION" } },
    changeColorTheme: jest.fn(),
    isSideBarOpen: true,
    toggleSideBar: jest.fn()
  };

  const contextWrapper = (children:any) => {
    return (
      <QueryClientProvider client={queryClient}>
        <Router>
            <UserDataContext.Provider value={mockContextValue}>
              {children}
            </UserDataContext.Provider>
        </Router>
      </QueryClientProvider>
    );
  }



jest.mock("../../../../../Services/MTA/InsightsAndTrends/BufferTrends")
jest.mock("ag-charts-react", () => ({
    AgCharts: jest.fn(() => null)
  }));

describe ("Buffer trends charts",()=>{
  global.ResizeObserver = class MockedResizeObserver {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };

  it("should render chart view",()=>{
      render(contextWrapper(<ChartView currentTab="technicalView" currentGraphData={[]} currentPageTab="Absolute" isLoading={false}  graphs={graphsMock}  updateGraphState={()=>console.log("a") }  setHorizondays={()=>console.log("b")} handleSubmitClick={()=>console.log("b")} horizonDays={30}/>))
      render(contextWrapper(<ChartView currentTab="economicalView" currentGraphData={[]} currentPageTab="Absolute" isLoading={false}  graphs={graphsMock}  updateGraphState={()=>console.log("a")} setHorizondays={()=>console.log("b")} handleSubmitClick={()=>console.log("b")} horizonDays={30}/>))
  })

})
