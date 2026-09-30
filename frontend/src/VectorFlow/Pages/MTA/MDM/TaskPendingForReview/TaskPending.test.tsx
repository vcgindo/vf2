import { ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";

import { BrowserRouter as Router } from "react-router-dom";
import { Provider } from "react-redux";
import {  render,screen } from "@testing-library/react"

import { UserDataContext } from "../../../../../context";
import TaskPendingForReview from ".";
import { store } from "../../../../../redux/store/store";
import { setupReactQuery } from "../../../../../config/react-query-config";
import {useApproveTask, useGetMasterUIConfiguration, useGetPendingTasks, useGetTaskCount, useGetTaskDetails } from "../../../../../VectorFlow/Services/MTA/MDM";
import { getAllDraftsMock,getMasterUIConfigurationMockData, getTaskCountMockData, getTaskDetailsMockData, getTaskPendingForReviewMockData, approveTaskMockData } from "../../../../../mock-data/MDM";

jest.mock("../../../../Services/MTA/MDM");


jest.mock('react-toastify', () => ({
  toast: {
    error: jest.fn(),
    success:jest.fn()
  },
}))

const useGetPendingTasksMock = useGetPendingTasks as jest.MockedFunction<
   typeof useGetPendingTasks
>

const useGetTaskDetailsMock = useGetTaskDetails as jest.MockedFunction<
   typeof useGetTaskDetails
>

const useGetTaskCountMock = useGetTaskCount as jest.MockedFunction<
   typeof useGetTaskCount
>


const useGetMasterUIConfigurationMock = useGetMasterUIConfiguration as jest.MockedFunction<
   typeof useGetMasterUIConfiguration
>

const useApproveTaskMock = useApproveTask as jest.MockedFunction<
   typeof useApproveTask
>

window.URL.createObjectURL = jest.fn();

 const useGetMasterUIConfigurationMockData: any = {
   mutateAsync: () => {
     return { data: getMasterUIConfigurationMockData,isLoading:false };
   },
 };

 const useGetTaskDetailsMockData: any = {
  mutateAsync: () => {
    return { data: getTaskDetailsMockData ,isLoading:false};
  },
};

const useGetTaskCountMockData: any = {
  mutateAsync: () => {
    return { data: approveTaskMockData,isLoading:false};
  },
};

const useApproveTaskMockData: any = {
  mutateAsync: () => {
    return { data: getTaskCountMockData ,isLoading:false};
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
      useGetPendingTasksMock.mockImplementation(():any => {
         return {data:{data:getTaskPendingForReviewMockData,isLoading:false}};
       });
       useGetTaskDetailsMock.mockImplementation(():any=>{
         return useGetTaskDetailsMockData
       })
       useGetMasterUIConfigurationMock.mockImplementation(()=>{
         return useGetMasterUIConfigurationMockData
       })

       useGetTaskCountMock.mockImplementation(()=>{
        return useGetTaskCountMockData
      })

      useApproveTaskMock.mockImplementation(()=>{
        return useApproveTaskMockData
      })
       
   })

   afterEach(()=>{
    jest.clearAllMocks()
   })

   it("renders on the dom",()=>{
    render(contextWrapper(<TaskPendingForReview/>,store))
   })

   it("renders the loading on the dom",()=>{
      useGetPendingTasksMock.mockImplementation(():any => {
         return {data: getAllDraftsMock,isLoading:true};
       });
      render(contextWrapper(<TaskPendingForReview/>,store))
      expect(screen.getByTestId('loader')).toBeInTheDocument()
     })

  //  it('handles all click events',()=>{
  //     render(contextWrapper(<TaskPendingForReview/>,store))
  //     const taskName = screen.getByText('Test Click')
  //     fireEvent.click(taskName)
  //     // screen.logTestingPlaygroundURL()

  //  })

})