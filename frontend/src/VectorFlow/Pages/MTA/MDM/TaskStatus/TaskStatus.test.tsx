
import { ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";

import { BrowserRouter as Router } from "react-router-dom";
import { Provider } from "react-redux";
import { render,screen } from "@testing-library/react"

import { UserDataContext } from "../../../../../context";
import TaskStatus from ".";
import { store } from "../../../../../redux/store/store";
import { setupReactQuery } from "../../../../../config/react-query-config";
import { useGetTaskDetailDownloadData, useGetTaskStatusData,useGetMasterUIConfiguration } from "../../../../../VectorFlow/Services/MTA/MDM";
import { getTaskDetailsDownloadDataMockData, getTaskStatusDataMockData,getMasterUIConfigurationMockData } from "../../../../../mock-data/MDM";

jest.mock("../../../../Services/MTA/MDM");


jest.mock('react-toastify', () => ({
  toast: {
    error: jest.fn(),
    success:jest.fn()
  },
}))

const useGetTaskStatusDataMock = useGetTaskStatusData as jest.MockedFunction<
   typeof useGetTaskStatusData
>

const useGetTaskDetailDownloadDataMock = useGetTaskDetailDownloadData as jest.MockedFunction<
   typeof useGetTaskDetailDownloadData
>

const useGetMasterUIConfigurationMock = useGetMasterUIConfiguration as jest.MockedFunction<
   typeof useGetMasterUIConfiguration
>


window.URL.createObjectURL = jest.fn();


const useGetTaskDetailDownloadDataMockData = {
    mutateAsync:()=>{
        return {data:getTaskDetailsDownloadDataMockData}
    }
} 

const useGetMasterUIConfigurationMockData: any = {
  mutateAsync: () => {
    return { data: getMasterUIConfigurationMockData };
  },
};

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
 


describe("Handles all renders",()=>{
   global.ResizeObserver = class MockedResizeObserver {
      observe = jest.fn();
      unobserve = jest.fn();
      disconnect = jest.fn();
    };

   beforeEach(()=>{

       useGetTaskDetailDownloadDataMock.mockImplementation(():any=>{
         return useGetTaskDetailDownloadDataMockData;
       })
       
       useGetTaskStatusDataMock.mockImplementation(():any=>{
        return {data: {data:getTaskStatusDataMockData},isLoading:false} 
       })

       useGetMasterUIConfigurationMock.mockImplementation(()=>{
        return useGetMasterUIConfigurationMockData
      })
   })

   afterEach(()=>{
    jest.clearAllMocks()
   })

   it("renders on the dom",()=>{
    render(contextWrapper(<TaskStatus/>,store))
   })

   it("renders the loading on the dom",()=>{
    useGetTaskStatusDataMock.mockImplementation(():any=>{
        return {data: {data:getTaskStatusDataMockData},isLoading:true} 
       })
      render(contextWrapper(<TaskStatus/>,store))
      expect(screen.getByTestId('loader')).toBeInTheDocument()
     })

   it('handles all click events',()=>{
      render(contextWrapper(<TaskStatus/>,store))
   })

})