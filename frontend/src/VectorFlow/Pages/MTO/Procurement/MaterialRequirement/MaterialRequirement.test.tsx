import React,{ReactNode} from 'react';
import { render } from '@testing-library/react';
import { setupReactQuery } from '../../../../../config/react-query-config';
// Install this package if not already installed
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router } from 'react-router-dom';
import { Provider } from 'react-redux';
import { UserDataContext } from '../../../../../context';
import {createStore} from '../../../../../redux/store/store';
import MaterialRequirement from './MaterialRequirement';

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
  

describe("MaterialRequirement Component", () => {
    test("Div present on the screen", () => {
        render(contextWrapper(<MaterialRequirement/>,mockedStore));
        
    })

})