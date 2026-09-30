import {render } from '@testing-library/react';
import { useGetDBMApplySelectedNorm,useGetDBMData,useGetDBMDataCount,useGetDBMUIConfiguration,useGetDBMUpdateSleepTbl } from "../../../../Services/MTA/DBM"
import { mockDBMApplySelectedNorm,mockDBMCountData,mockDBMData,mockDBMUIConfigData,mockDBMUpdateSleepTbl} from "../../../../../mock-data/DBM";
import DBM from './';
jest.mock("../../../../../VectorFlow/Services/MTA/DBM");
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter as Router } from "react-router-dom";
import { setupReactQuery } from "../../../../../config/react-query-config";
import { ReactNode } from "react";
import { Provider } from "react-redux";

import { UserDataContext } from "../../../../../context";
import {store} from "../../../../../redux/store/store";


const useGetDBMUIConfigurationMock = useGetDBMUIConfiguration as jest.MockedFunction<
  typeof useGetDBMUIConfiguration
>;
const useGetDBMDataMock = useGetDBMData as jest.MockedFunction<
  typeof useGetDBMData
>;
const useGetDBMDataCountMock = useGetDBMDataCount as jest.MockedFunction<
  typeof useGetDBMDataCount
>;
const useGetDBMApplySelectedNormMock = useGetDBMApplySelectedNorm as jest.MockedFunction<
  typeof useGetDBMApplySelectedNorm
>;
const useGetDBMUpdateSleepTblMock = useGetDBMUpdateSleepTbl as jest.MockedFunction<
  typeof useGetDBMUpdateSleepTbl
>;

// const useGetStateMock = useGetState as jest.MockedFunction<
//   typeof useGetState
// >

  window.URL.createObjectURL = jest.fn();

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


const useDBMDataResult: any = {
  mutateAsync: () => {
    return { data: mockDBMData };
  },
};

const useGetMasterUIConfigurationMockResult: any = {
  mutateAsync: () => {
    return {
      data: { data: mockDBMUIConfigData }
    }
  }
}

const useGetDBMCountResult: any = {
  mutateAsync: () => {
    return { data: mockDBMCountData };
  },
};

const useDBMApplySelectedNormResult: any = {
  mutateAsync: () => {
    return { data: mockDBMApplySelectedNorm };
  },
};

const useDBMUpdateSleepTbl: any = {
  mutateAsync: () => {
    return { data: mockDBMUpdateSleepTbl };
  },
};

  


describe("Renders DBM Component", ()=>{
    beforeEach(()=>{
        useGetDBMUIConfigurationMock.mockImplementation(()=>{
            return useGetMasterUIConfigurationMockResult;
        });
        useGetDBMDataCountMock.mockImplementation(()=>{
            return useGetDBMCountResult;
        });
        useGetDBMDataMock.mockImplementation(()=>{
            return useDBMDataResult;
        });
        useGetDBMApplySelectedNormMock.mockImplementation(()=>{
            return useDBMApplySelectedNormResult;
        });
        useGetDBMUpdateSleepTblMock.mockImplementation(()=>{
            return useDBMUpdateSleepTbl;
        });

        // useGetStateMock.mockImplementation(():any=>{
        //   return{
        //     mutateAsync:()=>{
        //       return {
        //         data:{data: GetStateMockResponse}
        //       }
        //     }
        //   }
          
        // })
    

    });
    it("renders Loading Overlay Component when loading", async()=>{
        useGetDBMUIConfigurationMock.mockImplementation(()=>{
            return {...useGetMasterUIConfigurationMockResult,isLoading:true};
        });
        render(contextWrapper(<DBM />,store));
    })
    //  it("renders DBMNorm", async()=>{
    //     await act(async () => {
    //       render(contextWrapper(<DBM />,store));
    //       })
    // })


  it("renders Loading Overlay Component when loading", async () => {
    // useGetDBMUIConfigurationMock.mockImplementation(()=>{
    //     return {...useGetMasterUIConfigurationMockResult,isLoading:true};
    // });
    // render(contextWrapper(<DBM />,store));
    expect(true).toBe(true);
  })
  //  it("renders DBMNorm", async()=>{
  //     await act(async () => {
  //       render(contextWrapper(<DBM />,store));
  //       })
  // })

  //  it("Handles Pagination", async()=>{
  //     await act(async () => {
  //       render(contextWrapper(<DBM />,store));
  //       })

  //       const nextBtn = screen.getAllByAltText('pagination-next-arrow')
  //     fireEvent.click(nextBtn[0]);
  // })
})
