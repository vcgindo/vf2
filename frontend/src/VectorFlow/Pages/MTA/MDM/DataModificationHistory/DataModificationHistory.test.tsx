import {  render } from "@testing-library/react";
import { ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { UserDataContext} from "../../../../../context";

import { setupReactQuery } from "../../../../../config/react-query-config";
import {store} from '../../../../../redux/store/store'
import 'ag-grid-enterprise';


import { BrowserRouter as Router } from "react-router-dom";
import { Provider } from "react-redux";
import DataModificationHistory from ".";
import {useGetMasterUIConfiguration,useGetSkuLoc,useGetTaskMastersHistory} from "../../../../Services/MTA/MDM";
import { getMasterUIConfigurationMockData,getSkuLocMockData,getTaskMasterHistoryMockData } from "../../../../../mock-data/MDM";

jest.mock("../../../../Services/MTA/MDM");

const useGetMasterUIConfigurationMock = useGetMasterUIConfiguration as jest.MockedFunction<
    typeof useGetMasterUIConfiguration
>

const useGetSkuLocMock= useGetSkuLoc as jest.MockedFunction<
    typeof useGetSkuLoc
>

const useGetTaskMasterHistoryMock = useGetTaskMastersHistory as jest.MockedFunction<
    typeof useGetTaskMastersHistory
>


const useGetMasterUIConfigurationMockData: any = {
    mutateAsync: () => {
      return { data: getMasterUIConfigurationMockData };
    },
  };

const useGetSkuLocMockData:any = {
    mutateAsync: () => {
        return { data:getSkuLocMockData };
      },
};

const useGetTaskMastersMockData:any ={
    mutateAsync: () =>{
        return {data: getTaskMasterHistoryMockData}
    }
}

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

const dummyprops = {

}

describe('Data Modification History Page', () => {

    beforeEach(()=>{ 
        useGetMasterUIConfigurationMock.mockImplementation(()=>{
            return useGetMasterUIConfigurationMockData
          })

        useGetSkuLocMock.mockImplementation(()=> {
            return useGetSkuLocMockData
          })
        
        useGetTaskMasterHistoryMock.mockImplementation(()=>{
            return useGetTaskMastersMockData
        })
     })

    afterEach(()=>{
        jest.clearAllMocks()
    })


    it('Handling Submit and Reset Buttons', () =>{
        render( contextWrapper(<DataModificationHistory {...dummyprops}></DataModificationHistory>, store))

        // const onSubmit = screen.getByText("Submit")
        // expect(onSubmit).toBeInTheDocument();
        // fireEvent.click(screen.getByText("Submit"))

        // const onReset = screen.getByText("Reset")
        // expect(onReset).toBeInTheDocument();
        // fireEvent.click(screen.getByText("Reset"))
    })

    // it('Selects Masters from Select',async ()=>{
    //     const {getAllByRole} = render(contextWrapper(<DataModificationHistory {...dummyprops}></DataModificationHistory>,store))
    //     await waitFor(async () => {
    //         const reactSelect = getAllByRole('combobox')[0]
    //         expect(reactSelect).toBeInTheDocument();
    //         await select(reactSelect, ['SKU']);
    //     });
    //     await waitFor(async () => {
    //         const reactSelect = getAllByRole('combobox')[0]
    //         expect(reactSelect).toBeInTheDocument();
    //         await select(reactSelect, ['Location']);
    //     });
    //     await waitFor(async () => {
    //         const reactSelect = getAllByRole('combobox')[0]
    //         expect(reactSelect).toBeInTheDocument();
    //         await select(reactSelect, ['SKULocation']);
    //     });
    // })

   

    
})
