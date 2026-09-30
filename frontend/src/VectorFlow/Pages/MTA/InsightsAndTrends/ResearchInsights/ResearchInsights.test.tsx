import { render} from '@testing-library/react';
import { UserDataContext } from "../../../../../context";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter as Router } from "react-router-dom";
import { setupReactQuery } from "../../../../../config/react-query-config";
import { useGetBPRData,useGetBPRUIConfiguration ,useGetBPRDataCount,useSaveState,useResetState,useGetDailyData,useGetLocationTypes} from '../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR';
import { useGetState } from '../../../../../VectorFlow/Services/MTA/Common/UserUIConfig';
import {useGetHistroricalAvailabilityData, useGetUpdatedGraphData} from '../../../../../VectorFlow/Services/MTA/InsightsAndTrends/ResearchInsights'
import { GetBPRDataMockResponse,GetBPRUIConfigurationMockResponse, GetUpdatedGraphDataMockResponse,GetStateMockResponse,ResetStateMockResponse,SaveStateMockResponse,GetDailyDataMockResponse, GetHistoricalAvailabilityMockResponse} from '../../../../../mock-data/BPR';
import ResearchInsights from './index';

import { ReactNode } from "react";
import { Provider } from "react-redux";
import {store} from "../../../../../redux/store/store";



// Mock context data
jest.mock('../../../../Services/MTA/InsightsAndTrends/ResearchInsights')
jest.mock('../../../../Services/MTA/SupplyChainIntelligenceHub/BPR')

// const mockContextValue = {
//   user: { user: { theme_ui: "NOIRFUSION" } },
//   changeColorTheme: jest.fn(),
//   isSideBarOpen: true,
//   toggleSideBar: jest.fn()
// };

// Mock the query client
const queryClient = setupReactQuery();


const useGetBPRDataMock = useGetBPRData as jest.MockedFunction<
  typeof useGetBPRData
>

const useGetBPRDataCountMock = useGetBPRDataCount as jest.MockedFunction<
  typeof useGetBPRDataCount
>

const useGetBPRUIConfigurationMock = useGetBPRUIConfiguration as jest.MockedFunction<
    typeof useGetBPRUIConfiguration
  >;

  const useGetUpdatedGraphDataMock = useGetUpdatedGraphData as jest.MockedFunction<
    typeof useGetUpdatedGraphData
  >;

  const useGetStateMock = useGetState as jest.MockedFunction<
  typeof useGetState
>

const useSaveStateMock = useSaveState as jest.MockedFunction<
  typeof useSaveState
>

const useResetStateMock = useResetState as jest.MockedFunction<
  typeof useResetState
>

const useGetDailyDataMock = useGetDailyData as jest.MockedFunction<
typeof useGetDailyData
> 

const useGetHistroricalAvailabilityDataMock = useGetHistroricalAvailabilityData as jest.MockedFunction<
  typeof useGetHistroricalAvailabilityData
>

const useGetLocationTypesMock = useGetLocationTypes as jest.MockedFunction<
  typeof useGetLocationTypes
>

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

describe('Research and insights Component', () => {
  global.ResizeObserver = class MockedResizeObserver {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };

  beforeEach(() => {

    useGetBPRUIConfigurationMock.mockImplementation(():any=>{
        return {data: {data:GetBPRUIConfigurationMockResponse},isLoading:false};
      })
  
      useGetHistroricalAvailabilityDataMock.mockImplementation(():any=>{
        return{data:{data:GetHistoricalAvailabilityMockResponse},isLoading:false}
      })

    useGetBPRDataMock.mockImplementation(():any=>{
      return {
        mutateAsync:()=>{
          return {data:GetBPRDataMockResponse}
        },
        isLoading:false
      }
    })

    useGetUpdatedGraphDataMock.mockImplementation(():any=>{
      return {
        mutateAsync:()=>{
          return {data:GetUpdatedGraphDataMockResponse}
        },
        isLoading:true
      }
    })

    useGetBPRDataCountMock.mockImplementation(():any=>{
      return {
        mutateAsync:()=>{
          return{
            data:{
              "recordCount": "148129",
              "data": null,
              "status": 200,
              "msg": null,
              "errorCount": null,
              "error": null,
              "conflictErrorCount": null,
              "conflictError": null
            }
          }
        }
      }
    })
    useGetStateMock.mockImplementation(():any=>{
      return{
        mutateAsync:()=>{
          return {
            data:{data: GetStateMockResponse}
          }
        }
      }
      
    })

    useSaveStateMock.mockImplementation(():any=>{
      return{
        mutateAsync:()=>{
          return {
            data:{data: SaveStateMockResponse}
          }
        }
      }
      
    })

    useResetStateMock.mockImplementation(():any=>{
      return{
        mutateAsync:()=>{
          return {
            data:{data: ResetStateMockResponse}
          }
        }
      }
      
    })

    useGetDailyDataMock.mockImplementation(():any=>{
      return{
        mutateAsync:()=>{
          return {
            data:{data: GetDailyDataMockResponse}
          }
        }
      }
      
    })

    useGetLocationTypesMock.mockImplementation(():any=>{
      return {data: {data:{
        "recordCount": null,
        "data": "[{\"lt\":\"2013\"},{\"lt\":\"CWH\"},{\"lt\":\"Depot\"},{\"lt\":\"Inhouse\"},{\"lt\":\"plant\"},{\"lt\":\"Supplier\"},{\"lt\":\"WS01\"}]",
        "status": 200,
        "msg": null,
        "errorCount": null,
        "error": null,
        "conflictErrorCount": null,
        "conflictError": null
      }},isLoading:false};
    })

  });
  // it('renders loader when isLoading is true', () => {
  //   useGetBPRUIConfigurationMock.mockImplementation(():any=>{
  //       return {data: {data:GetBPRUIConfigurationMockResponse},isLoading:true};
  //     })
  //     render(contextWrapper(<ResearchInsights />,store));
  //   expect(screen.getByTestId('loader')).toBeInTheDocument();
  // });

  it('renders BPR layout properly', () => {
    render(contextWrapper(<ResearchInsights />,store));
    // const inputRange = screen.getByRole('slider');

    // fireEvent.change(inputRange, { target: { value: '75' } });
    // Add your assertions here to ensure the layout renders correctly
  });

});


// describe('Handles all interactions', () => {
//   global.ResizeObserver = class MockedResizeObserver {
//     observe = jest.fn();
//     unobserve = jest.fn();
//     disconnect = jest.fn();
//   };

//   beforeEach(async() => {
//     cleanup()
//     useGetBPRUIConfigurationMock.mockImplementation(():any=>{
//         return {data: {data:GetBPRUIConfigurationMockResponse},isLoading:false};
//       })
  

//     useGetBPRDataMock.mockImplementation(():any=>{
//       return {
//         mutateAsync:()=>{
//           return {data:GetBPRDataMockResponse}
//         },
//         isLoading:false
//       }
//     })

//     useGetUpdatedGraphDataMock.mockImplementation(():any=>{
//       return {
//         mutateAsync:()=>{
//           return {data:GetUpdatedGraphDataMockResponse}
//         },
//         isLoading:false
//       }
//     })

//     useGetBPRDataCountMock.mockImplementation(():any=>{
//       return {
//         mutateAsync:()=>{
//           return{
//             data:{
//               "recordCount": "148129",
//               "data": null,
//               "status": 200,
//               "msg": null,
//               "errorCount": null,
//               "error": null,
//               "conflictErrorCount": null,
//               "conflictError": null
//             }
//           }
//         }
//       }
//     })

//     useGetStateMock.mockImplementation(():any=>{
//       return{
//         mutateAsync:()=>{
//           return {
//             data:{data: GetStateMockResponse}
//           }
//         }
//       }
      
//     })

//     useSaveStateMock.mockImplementation(():any=>{
//       return{
//         mutateAsync:()=>{
//           return {
//             data:{data: SaveStateMockResponse}
//           }
//         }
//       }
      
//     })

//     useResetStateMock.mockImplementation(():any=>{
//       return{
//         mutateAsync:()=>{
//           return {
//             data:{data: ResetStateMockResponse}
//           }
//         }
//       }
      
//     })

//     useGetDailyDataMock.mockImplementation(():any=>{
//       return{
//         mutateAsync:()=>{
//           return {
//             data:{data: GetDailyDataMockResponse}
//           }
//         }
//       }
      
//     })
    
//     render(contextWrapper(<ResearchInsights />,store));
    

//     // await waitFor(async()=>{
//     //   const skuCodeElement = screen.getAllByRole('gridcell', { name: /ARES0798C004/i })[0];
//     //   expect(skuCodeElement).toBeInTheDocument()
//     // })

//  });

 

//   // it("Clicks on update graph when no row is selected",async()=>{
    
//   //   await waitFor(async()=>{
//   //     fireEvent.click(screen.getByText('Update Graph'))
//   //   })
//   // })

//   // it("Clicks on update graph when one row is selected",async()=>{
    
//   //   await waitFor(async()=>{
//   //     screen.logTestingPlaygroundURL()
//   //     const checkboxInput = screen.getAllByLabelText('Press Space to toggle row selection (unchecked)')[0];
//   //     checkboxInput.click(); // Simulate a click to check the checkbox

//   //     fireEvent.click(screen.getByText('Update Graph'))

//   //     const ecoBtn = screen.getByText("Eco")
//   //     fireEvent.click(ecoBtn)

//   //     const rangeInput = screen.getByRole('slider');
//   //     fireEvent.change(rangeInput, { target: { value: '45' } });
//   //   })
//   // })

//   // it("Clicks on update graph when two rows are selected",async()=>{
    
//   //   await waitFor(async()=>{
//   //     const checkboxInput = screen.getAllByLabelText('Press Space to toggle row selection (unchecked)');
//   //     fireEvent.click(checkboxInput[0])
//   //     fireEvent.click(checkboxInput[1])
      
      
      
     
//   //   })
//   // // //   await waitFor(()=>{
      
//   // // //     const updateGraphBtn = screen.getByText('Update Graph')
//   // // //     updateGraphBtn.click()
//   // // //   })
//   // // //   await waitFor(()=>{
      
//   // // //     const canvasElement = screen.getAllByRole('canvas')[0];
//   // // //     expect(canvasElement).toBeInTheDocument()
//   // // //   })
   
//   // })

  
// });