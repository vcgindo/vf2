import React,{ReactNode} from 'react';
import { render, fireEvent, screen } from '@testing-library/react';
import MaterialCov from './MaterialCov';
import { setupReactQuery } from '../../../../../config/react-query-config';
// Install this package if not already installed
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router } from 'react-router-dom';
import { Provider } from 'react-redux';
import { UserDataContext } from '../../../../../context';
import {createStore} from '../../../../../redux/store/store'

const queryClient = setupReactQuery();

const dummyStore:any ={
  AnalyticsData:{}
}

const mockedStore = createStore(dummyStore)

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
  

describe("FutureCoverage Component", () => {
    test("Div present on the screen", () => {
        render(contextWrapper(<MaterialCov/>,mockedStore));
        
    })
    test("Handles children's click",async()=>{
        render(contextWrapper(<MaterialCov/>,mockedStore));
        const navigate = screen.getByTestId("btn_navigate")
        fireEvent.click(navigate);
        fireEvent.click(navigate);
    })

    test("Handles tab change",async()=>{
        render(contextWrapper(<MaterialCov/>,mockedStore));
        const navigate = screen.getByText("Future Coverage")
        fireEvent.click(navigate);
    })

})