import { render} from '@testing-library/react';
import { UserDataContext } from "../../../../../context";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter as Router } from "react-router-dom";
import { setupReactQuery } from "../../../../../config/react-query-config";
import {GetInTransitWhereAboutsDataCountMockResponse, GetInTransitWhereAboutsMockResponse, GetRemarkDetailsForInTransitMockResponse, GetStateMockResponse,GetTransporterDetailsMockResponse,ResetStateMockResponse,SaveStateMockResponse, SubmitRemarksForInTransitMockResponse} from '../../../../../mock-data/BPR';

import {useGetLocationTypes, useGetState,useResetState,useSaveState} from '../../../../Services/MTA/SupplyChainIntelligenceHub/BPR'
import { ReactNode } from "react";
import { Provider } from "react-redux";
import {store} from "../../../../../redux/store/store";
import InTransitWhereAbouts from './index'
import { useGetInTransitWhereAboutsData, useGetInTransitWhereAboutsDataCount,useGetRemarkDetailsForInTransit,useSubmitRemarksForInTransit,useGetTransporterDetails } from '../../../../Services/MTA/Logistics/InTransitWhereAbouts';

// Mock context data

jest.mock('../../../../Services/MTA/Logistics/InTransitWhereAbouts')
jest.mock('../../../../Services/MTA/SupplyChainIntelligenceHub/BPR')

// const mockContextValue = {
//   user: { user: { theme_ui: "NOIRFUSION" } },
//   changeColorTheme: jest.fn(),
//   isSideBarOpen: true,
//   toggleSideBar: jest.fn()
// };

// Mock the query client
const queryClient = setupReactQuery();

const useGetStateMock = useGetState as jest.MockedFunction<
typeof useGetState
>

const useSaveStateMock = useSaveState as jest.MockedFunction<
typeof useSaveState
>

const useResetStateMock = useResetState as jest.MockedFunction<
typeof useResetState
>

const useGetInTransitWhereAboutsDataCountMock = useGetInTransitWhereAboutsDataCount as jest.MockedFunction<
    typeof useGetInTransitWhereAboutsDataCount
>

const useGetInTransitWhereAboutsDataMock = useGetInTransitWhereAboutsData as jest.MockedFunction<
    typeof useGetInTransitWhereAboutsData
>

const useGetRemarkDetailsForInTransitMock = useGetRemarkDetailsForInTransit as jest.MockedFunction<
  typeof useGetRemarkDetailsForInTransit
>

const useSubmitRemarksForInTransitMock = useSubmitRemarksForInTransit as jest.MockedFunction<
  typeof useSubmitRemarksForInTransit
>

const useGetTransporterDetailsMock = useGetTransporterDetails as jest.MockedFunction<
  typeof useGetTransporterDetails
>

const useGetLocationTypesMock = useGetLocationTypes as jest.MockedFunction<
  typeof useGetLocationTypes
>


// const contextWrapper = (children:any) => {
//   return (
//     <QueryClientProvider client={queryClient}>
//       <Router>
//           <UserDataContext.Provider value={mockContextValue}>
//             {children}
//           </UserDataContext.Provider>
//       </Router>
//     </QueryClientProvider>
//   );
// }


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



describe("It handles all interactions",()=>{
  global.ResizeObserver = class MockedResizeObserver {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };


  beforeEach(() => {
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

    useGetInTransitWhereAboutsDataCountMock.mockImplementation(():any=>{
        return{
          mutateAsync:()=>{
            return {
              data:{data: GetInTransitWhereAboutsDataCountMockResponse}
            }
          }
        }
        
      })

      useGetInTransitWhereAboutsDataMock.mockImplementation(():any=>{
        return{
          mutateAsync:()=>{
            return {
              data:{data: GetInTransitWhereAboutsMockResponse}
            }
          }
        }
        
      })

      useGetRemarkDetailsForInTransitMock.mockImplementation(():any=>{
        return{
          mutateAsync:()=>{
            return {
              data:{data: GetRemarkDetailsForInTransitMockResponse}
            }
          }
        }
        
      })

      useSubmitRemarksForInTransitMock.mockImplementation(():any=>{
        return{
          mutateAsync:()=>{
            return {
              data:{data: SubmitRemarksForInTransitMockResponse}
            }
          }
        }
        
      })

      useGetTransporterDetailsMock.mockImplementation(():any=>{
        return{
          mutateAsync:()=>{
            return {
              data:{data: GetTransporterDetailsMockResponse}
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

    render(contextWrapper(<InTransitWhereAbouts/>,store))
  });

  it("renders",async()=>{
   
    render(contextWrapper(<InTransitWhereAbouts/>,store))
  })

  // it('clicks on remarkhistory',async()=>{
  //   await waitFor(async()=>{
      
  //     const imgElement = screen.getAllByRole('img', { name: /history icon/i })[0]
  //     fireEvent.click(imgElement)
  //   })
  // })
  
})
