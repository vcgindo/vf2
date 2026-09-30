import { ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";

import { BrowserRouter as Router } from "react-router-dom";
import { Provider } from "react-redux";
import { fireEvent, render,screen } from "@testing-library/react"

import { UserDataContext } from "../../../../../context";
import SavedDrafts from "."
import { store } from "../../../../../redux/store/store";
import { setupReactQuery } from "../../../../../config/react-query-config";
import { useDeleteDraft, useGetAllDrafts, useGetDraftById,useGetDraftCount,useGetMasterUIConfiguration } from "../../../../../VectorFlow/Services/MTA/MDM";
import { getAllDraftsMock, getDraftByIdMockData, getMasterUIConfigurationMockData, getDraftCountMockData } from "../../../../../mock-data/MDM";

jest.mock("../../../../Services/MTA/MDM");


jest.mock('react-toastify', () => ({
  toast: {
    error: jest.fn(),
    success:jest.fn(),
    dismiss:jest.fn()
  },
}))

const useDeleteDraftMock = useDeleteDraft as jest.MockedFunction<
   typeof useDeleteDraft
>

const useGetAllDraftsMock = useGetAllDrafts as jest.MockedFunction<
   typeof useGetAllDrafts
>

const useGetDraftByIdMock = useGetDraftById as jest.MockedFunction<
   typeof useGetDraftById
>

const useGetMasterUIConfigurationMock = useGetMasterUIConfiguration as jest.MockedFunction<
   typeof useGetMasterUIConfiguration
>

const useGetDraftCountMock = useGetDraftCount as jest.MockedFunction<
   typeof useGetDraftCount
>

window.URL.createObjectURL = jest.fn();

const useGetDraftByIdMockData: any = {
   mutateAsync: () => {
     return { data: getDraftByIdMockData };
   },
 };

 const useGetDraftCountMockData: any = {
  mutateAsync: () => {
    return { data: getDraftCountMockData };
  },
};
 
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
      useGetAllDraftsMock.mockImplementation(():any => {
         return {data: {data:getAllDraftsMock},isLoading:false};
       });
       useGetDraftByIdMock.mockImplementation(()=>{
         return useGetDraftByIdMockData;
       })
       useGetMasterUIConfigurationMock.mockImplementation(()=>{
         return useGetMasterUIConfigurationMockData
       })
       useDeleteDraftMock.mockImplementation(():any=>{
         return {}
       })

       useGetDraftCountMock.mockImplementation(():any=>{
        return useGetDraftCountMockData
      })
       
   })

   afterEach(()=>{
    jest.clearAllMocks()
   })

   it("renders on the dom",()=>{
    render(contextWrapper(<SavedDrafts/>,store))
   })

   it("renders the loading on the dom",()=>{
      useGetAllDraftsMock.mockImplementation(():any => {
         return {data: getAllDraftsMock,isLoading:true};
       });
      render(contextWrapper(<SavedDrafts/>,store))
      expect(screen.getByTestId('loader')).toBeInTheDocument()
     })

   it('handles all click events',()=>{
      render(contextWrapper(<SavedDrafts/>,store))
      const editIcon = screen.getAllByTestId('edit-draft')[0]
      const deleteIcon = screen.getAllByTestId('delete-draft')[0]
      fireEvent.click(editIcon)
      fireEvent.click(deleteIcon)
   })

})