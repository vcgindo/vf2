import { screen, render, fireEvent, waitFor} from "@testing-library/react"
import { useGetPlanningDataCount, useGetPlanningDataGraph, useGetPlanningDataGrid,useGetPlanningDataGridCount } from "../../../../Services/MTA/SupplyChainIntelligenceHub/Planning";
// import { UserDataContext } from "../../../../../context";
import { getPlanningDataCountMockData,getPlanningDataGridMockData,ExcessInventoryMockData,getPlanningDataGraphMockData,getPlanningDataGridCountMockResponse } from "../../../../../mock-data/Planning";
import Planning from ".";
import { act } from "react-dom/test-utils";
import { UserDataContext } from "../../../../../context/UserDataContext";
import { QueryClientProvider } from "@tanstack/react-query";
import { setupReactQuery } from "../../../../../config/react-query-config";
import { ReactNode } from "react";
import { BrowserRouter as Router } from "react-router-dom";
import { Provider } from "react-redux";
import { store } from "../../../../../redux/store/store";

const queryClient = setupReactQuery();

jest.mock('redux-persist/es/persistReducer', () => require('redux-persist/lib/persistReducer'));
jest.mock('redux-persist/es/persistStore', () => require('redux-persist/lib/persistStore'));

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

jest.mock("ag-charts-react", () => ({
    AgCharts: jest.fn(() => null)
}));

jest.mock("../../../../Services/MTA/SupplyChainIntelligenceHub/Planning");
jest.mock("../../../../Services/MTA/Common/UIConfig", () => ({
    useGetUIConfigData: () => ({ mutateAsync: async () => ({ data: { data: [] } }) }),
}));
jest.mock("../../../../Services/MTA/SupplyChainIntelligenceHub/BPR", () => ({
    ...jest.requireActual("../../../../Services/MTA/SupplyChainIntelligenceHub/BPR"),
    useGetLocationTypes: () => ({ data: { data: [] }, isLoading: false }),
}));

const useGetPlanningDataGridCountMock = useGetPlanningDataGridCount as jest.MockedFunction<
    typeof useGetPlanningDataGridCount
>

const useGetPlanningDataCountMock = useGetPlanningDataCount as jest.MockedFunction<
    typeof useGetPlanningDataCount
>;

const useGetPlanningDataGraphMock = useGetPlanningDataGraph as jest.MockedFunction<
    typeof useGetPlanningDataGraph
>;

const useGetPlanningDataGridMock = useGetPlanningDataGrid as jest.MockedFunction<
    typeof useGetPlanningDataGrid
>;

const useuseGetPlanningDataGridCountMockData:any = {
    mutateAsync: () => {
        return { data: getPlanningDataGridCountMockResponse };
    },
};

const useGetPlanningDataCountMockData: any = {
    mutateAsync: () => {
        return { data: { ...getPlanningDataCountMockData, businessDate: '2026-04-07' } };
    },
};

const useGetPlanningDataGraphMockData: any = (mockData:any) => ({
    mutateAsync: () => {
        return { data: {recordCount:345,data:mockData} };
    },
    isLoading:false
});

const useGetPlanningDataGridMockData: any = (mockData:any) => ({
    mutateAsync: () => {
        return { data: {recordCount:345,data:mockData} };
    },
});


describe("Planning Quadrant", () => {

    global.ResizeObserver = class MockedResizeObserver {
        observe = jest.fn();
        unobserve = jest.fn();
        disconnect = jest.fn();
      };

    beforeEach(() => {

        useGetPlanningDataGridCountMock.mockImplementation(()=>{
            return useuseGetPlanningDataGridCountMockData
        })
        
        useGetPlanningDataCountMock.mockImplementation(()=>{
            return useGetPlanningDataCountMockData
        }) 
        useGetPlanningDataGraphMock.mockImplementation(()=>{
            return useGetPlanningDataGraphMockData(getPlanningDataGraphMockData)
        })
        useGetPlanningDataGridMock.mockImplementation(()=>{
            return useGetPlanningDataGridMockData(getPlanningDataGridMockData)
        })
    });

    it("renders the date from the same count response", async () => {
        render(contextWrapper(<Planning/>,store));
        expect(await screen.findByText('07 Apr 2026')).toBeInTheDocument();
    })

    it("requests one fresh summary on each consecutive quadrant return", async () => {
        const fetchCount = jest.fn().mockResolvedValue({
            data: { ...getPlanningDataCountMockData, businessDate: '2026-04-07' },
        });
        useGetPlanningDataCountMock.mockImplementation(() => ({ mutateAsync: fetchCount } as any));
        useGetPlanningDataGraphMock.mockImplementation(() => useGetPlanningDataGraphMockData(ExcessInventoryMockData));
        render(contextWrapper(<Planning/>, store));
        await screen.findByText('07 Apr 2026');
        expect(fetchCount).toHaveBeenCalledTimes(1);
        for (let count = 2; count <= 3; count += 1) {
            await act(async () => { fireEvent.click(screen.getAllByText('Review')[0]); });
            await act(async () => { fireEvent.click(await screen.findByText('Go Back')); });
            await screen.findByText('07 Apr 2026');
            expect(fetchCount).toHaveBeenCalledTimes(count);
        }
    });

    it("releases the blocking loader when planning counts are unavailable", async () => {
        let rejectCount: (error: Error) => void = () => {};
        const pendingCount = new Promise((_, reject) => {
            rejectCount = reject;
        });
        const fetchCount = jest.fn().mockReturnValue(pendingCount);
        useGetPlanningDataCountMock.mockImplementation(() => ({
            mutateAsync: fetchCount,
        } as any));

        render(contextWrapper(<Planning/>, store));
        expect(screen.getByTestId('loader')).not.toBeNull();

        await act(async () => {
            rejectCount(new Error('Planning counts endpoint unavailable'));
        });

        await waitFor(() => expect(screen.queryByTestId('loader')).toBeNull());
        expect(fetchCount).toHaveBeenCalledTimes(1);
    });

    // it("Switches Floating Tab", async () => {
    //     useGetPlanningDataGraphMock.mockImplementation(()=>{
    //         return useGetPlanningDataGraphMockData(MonitorGITChildMockData)
    //     })
    //     render(contextWrapper(<Planning/>,store));
    //     await act(async () => {
    //         fireEvent.click(screen.getAllByText('To Child')[0])
    //     })
    //     expect(screen.getAllByTestId('floatingTabButton').length).toEqual(3);
    //     await act(async () => {
    //         fireEvent.click(screen.getAllByTestId('floatingTabButton')[1]);
    //     })
    //     expect(screen.getAllByTestId('floatingTabButton')[1]).toHaveStyle('color:white')

    // })

    // it("Renders MonitorGIT Graphs", async () => {
    //     useGetPlanningDataGraphMock.mockImplementation(()=>{
    //         return useGetPlanningDataGraphMockData(MonitorGITChildMockData)
    //     })
    //     render(contextWrapper(<Planning/>,store));
    //     // fireEvent.click(screen.getAllByText('To Child')[0])
    //     await act(async () => {
    //         fireEvent.click(screen.getAllByText('To Child')[0])
    //     })
    //     expect(screen.getAllByTestId('floatingTabButton').length).toEqual(3);
    //     cleanup();
    //     useGetPlanningDataGridMock.mockImplementation(()=>{
    //         return useGetPlanningDataGridMockData(getPlanningDataGridMockData['data'])
    //     })
    //     render(contextWrapper(<Planning/>,store));
    //     await act(async () => {
    //         fireEvent.click(screen.getAllByText('From Parent')[0])
    //     })

    // })

    // it("Renders Expedite Graphs", async () => {
    //     useGetPlanningDataGraphMock.mockImplementation(()=>{
    //         return useGetPlanningDataGraphMockData(ExpediteChildMockData)
    //     })
    //     render(contextWrapper(<Planning/>,store));
    //     await act(async () => {
    //         fireEvent.click(screen.getAllByText('To Child')[1])
    //     })
    //     cleanup();
    //     useGetPlanningDataGraphMock.mockImplementation(()=>{
    //         return useGetPlanningDataGraphMockData(ExpediteParentMockData)
    //     })
    //     render(contextWrapper(<Planning/>,store));
    //     await act(async () => {
    //         fireEvent.click(screen.getAllByText('From Parent')[1])
    //     })

    // })

    it("Renders Excess Inventory Graphs", async () => {
        useGetPlanningDataGraphMock.mockImplementation(()=>{
            return useGetPlanningDataGraphMockData(ExcessInventoryMockData)
        })

        render(contextWrapper(<Planning/>,store));
        
        await act(async () => {
            fireEvent.click(screen.getAllByText('Review')[0])
        })
    })

    // it("Renders Order Fulfillment Graphs", async () => {
    //     useGetPlanningDataGraphMock.mockImplementation(()=>{
    //         return useGetPlanningDataGraphMockData(OrderFulfillmentMockData)
    //     })
    //     render(contextWrapper(<Planning/>,store));
    //     await act(async () => {
    //         fireEvent.click(screen.getAllByText('Review')[1])
    //     })
    // })

    it("Switches Floating Tab on Click", () => {
        render(contextWrapper(<Planning/>,store));
        fireEvent.click(screen.getAllByText('To Child')[0])
        // fireEvent.click(screen.getByTestId('floatingTabButton'));
    })
    
  
})
