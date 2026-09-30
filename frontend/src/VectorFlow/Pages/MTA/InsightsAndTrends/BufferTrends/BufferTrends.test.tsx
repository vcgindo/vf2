import { render} from "@testing-library/react";
import { mockBTGTechData } from "../../../../../mock-data/BufferTrends";
import { useGetBufferTrendsGraph } from '../../../../Services/MTA/InsightsAndTrends/BufferTrends/index'
import { setupReactQuery } from "../../../../../config/react-query-config";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter as Router } from "react-router-dom";
import { UserDataContext } from "../../../../../context/UserDataContext";
import BufferTrends from ".";
import { Provider } from "react-redux";
import {ReactNode} from 'react'
import { store } from "../../../../../redux/store/store";


const queryClient = setupReactQuery();
const mockContextValue = {
    user: { user: { theme_ui: "NOIRFUSION" } },
    changeColorTheme: jest.fn(),
    isSideBarOpen: true,
    toggleSideBar: jest.fn()
  };

  const contextWrapper = (children: ReactNode,store:any) => {
    return (
      <QueryClientProvider client={queryClient}>
        <Router>
          <Provider store={store}>
            <UserDataContext.Provider
              value={mockContextValue}
            >
              {children}
            </UserDataContext.Provider>
          </Provider>
        </Router>
      </QueryClientProvider>
    );
  };
  
//     return (
//       <QueryClientProvider client={queryClient}>
//         <Router>
//           <Provider store={store}>
//             <UserDataContext.Provider
//               value={{
//                 user: { user: { theme_ui: "NOIRFUSION" } },
//                 changeColorTheme: (color) => {
//                   return color;
//                 },
//                 isSideBarOpen:true,toggleSideBar:jest.fn
//               }}
//             >
//               {children}
//             </UserDataContext.Provider>
//           </Provider>
//         </Router>
//       </QueryClientProvider>
//     );
//   };

jest.mock("../../../../Services/MTA/InsightsAndTrends/BufferTrends")
jest.mock("ag-charts-react", () => ({
    AgCharts: jest.fn(() => null)
  }));

const useGetBufferTrendsGraphMocked = useGetBufferTrendsGraph as jest.MockedFunction <
        typeof useGetBufferTrendsGraph
>;

const useGetBufferTrendsGraphMockData:any = (mockData:any)=>({
    mutateAsync : () => {
        return { data: {data:mockData} };
    },
    isLoading:false
});

describe ("Buffer trends",()=>{
    global.ResizeObserver = class MockedResizeObserver {
        observe = jest.fn();
        unobserve = jest.fn();
        disconnect = jest.fn();
      };

    beforeEach(()=>{
        useGetBufferTrendsGraphMocked.mockImplementation(()=>{

            return useGetBufferTrendsGraphMockData(mockBTGTechData);
        }) 
    })

    it("should render the buffer trends components",async ()=>{
        render(contextWrapper(<BufferTrends/>,store))
    
        // const button=screen.getByText("On-Hand Inv. Availability Trend")
        // expect(button).toBeInTheDocument();
    })

    // it("should render the buffer trends components",async ()=>{
    //     await act (async ()=>  render(contextWrapper(<BufferTrends/>,store)))
    //     const button=screen.getByText("On-Hand Inv. Availability Trend")
    //     expect(button).toBeInTheDocument();
    // })

    // it("should render the floating tab",async()=>{
    //     await act (async ()=>  render(contextWrapper(<BufferTrends/>,store)))

    //     const button=screen.getAllByTestId('floatingTabButton')[0]
    //     expect(button).toBeInTheDocument();
    // })
    // it("should render the capsule tab",async()=>{
    //     await act (async ()=>  render(contextWrapper(<BufferTrends/>,store)))
    //     const button1=screen.getByTestId('vf-capsule')
    //     expect(button1).toBeInTheDocument();
    // })


    // it("Switches Floating Tab", async () => {
    //     // useGetBufferTrendsGraphMocked.mockImplementation(()=>{
    //     //     return useGetBufferTrendsGraphMockData(mockBTGTechData);
    //     // }) 
    //     render(contextWrapper(<BufferTrends/>,store));
    //     expect(screen.getAllByTestId('floatingTabButton').length).toEqual(2);
    //     await act(async () => {
    //         fireEvent.click(screen.getAllByTestId('floatingTabButton')[1]);
    //     })
    //     expect(screen.getAllByTestId('floatingTabButton')[1]).toHaveStyle('color:white')
    // },10000)



})
