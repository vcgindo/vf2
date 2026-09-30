

import { render} from "@testing-library/react";
import {useGetRRRUIConfiguration,useGetRRRData,useGetRRRDataCount} from '../../../../Services/MTA/SupplyChainIntelligenceHub/RRR'

import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter as Router } from "react-router-dom";
import { setupReactQuery } from "../../../../../config/react-query-config";

import { ReactNode } from "react";
import { Provider } from "react-redux";
import {store} from "../../../../../redux/store/store";
import { UserDataContext } from "../../../../../context";


import {mockRRRData,mockRRRUiConfig,mockRRRDataCount} from '../../../../../mock-data/RRR';
import RRR from "./";

jest.mock("../../../../Services/MTA/SupplyChainIntelligenceHub/RRR");

const queryClient = setupReactQuery();

  const contextWrapper = (children: ReactNode,store:any) => {
    return (
      <QueryClientProvider client={queryClient}>
        <Router>
          <Provider store={store}>
            <UserDataContext.Provider
              value={{
                user: { user: { theme_ui: "NOIRFUSION" } },
                changeColorTheme: (color:any) => {
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


const useGetRRRUIConfigurationMock = useGetRRRUIConfiguration as jest.MockedFunction<
typeof useGetRRRUIConfiguration
>;

const useRRRDataMock = useGetRRRData as jest.MockedFunction<
  typeof useGetRRRData
>;

const useRRRDataCountMock = useGetRRRDataCount as jest.MockedFunction<
    typeof useGetRRRDataCount
>;

window.URL.createObjectURL = jest.fn();


const useRRRDataResult: any = {
    mutateAsync: () => {
      return { data: mockRRRData };
    },
  };

const useGetRRRUIConfigurationMockResult:any ={
  mutateAsync:()=>{
    return {
      data:{data: mockRRRUiConfig}  
    }
  }
}

const useGetRRRCountResult: any = {
  mutateAsync: () => {
    return { data: mockRRRDataCount };
  },
};

  describe("Renders RRR Component", ()=>{
    beforeEach(()=>{
        useGetRRRUIConfigurationMock.mockImplementation(()=>{
            return useGetRRRUIConfigurationMockResult;
        });
        useRRRDataMock.mockImplementation(()=>{
            return useRRRDataResult;
        });
        useRRRDataCountMock.mockImplementation(()=>{
            return useGetRRRCountResult ;
        });

    });
    it("renders Loading Overlay Component when loading", async()=>{
        useGetRRRUIConfigurationMock.mockImplementation(()=>{
            return {...useGetRRRUIConfigurationMockResult,isLoading:true};
        });
        render(contextWrapper(<RRR/>,store));
    })

    //  it("renders RRReport", async()=>{
    //     await act(async () => {
    //       render(contextWrapper(<RRR />,store));
    //       })
    // })

    //  it("Handles Pagination", async()=>{
    //     await act(async () => {
    //       render(contextWrapper(<RRR />,store));
    //       })
    //       const nextBtn = screen.getAllByAltText('pagination-next-arrow')
       
    //     fireEvent.click(nextBtn[0]);
    // })
})
  
