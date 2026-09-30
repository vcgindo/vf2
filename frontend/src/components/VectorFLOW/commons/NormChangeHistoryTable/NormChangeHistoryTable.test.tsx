import { screen, render, fireEvent } from "@testing-library/react"
import NormChangeHistoryTable from "."
import { QueryClientProvider } from "@tanstack/react-query";
import { UserDataContext } from "../../../../context";
import { setupReactQuery } from "../../../../config/react-query-config";
import {ReactNode} from 'react'
import { Provider } from "react-redux";
import {store} from '../../../../redux/store/store'


const mockFunction = jest.fn()
const queryClient = setupReactQuery()

const dummyprops = {
    data:[],
    onGoBack:mockFunction
}

const contextWrapper = (children: ReactNode,store:any) => {
  return (
    <QueryClientProvider client={queryClient}>
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
    </QueryClientProvider>
  );
}
  

describe("Handle allNormChangeModal interactions",()=>{
  global.ResizeObserver = class MockedResizeObserver {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };
  it('Clicks on GoBack button',()=>{
    render(contextWrapper(<NormChangeHistoryTable {...dummyprops}></NormChangeHistoryTable>,store))
        const goBackButton = screen.getByText("Go Back!"); 
        expect(goBackButton).toBeInTheDocument()
         fireEvent.click(goBackButton)
})
// it('Clicks on X button',()=>{
//   render(contextWrapper(<NormChangeHistoryTable {...dummyprops}></NormChangeHistoryTable>,store))
//       const goBackButton = screen.getByTestId('close-modal-icon'); 
//       expect(goBackButton).toBeInTheDocument()
//        fireEvent.click(goBackButton)
// })
})


