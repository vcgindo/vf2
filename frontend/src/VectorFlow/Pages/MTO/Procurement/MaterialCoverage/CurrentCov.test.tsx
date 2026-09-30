import React,{ReactNode} from 'react';
import { render, fireEvent, screen } from '@testing-library/react';
import { setupReactQuery } from '../../../../../config/react-query-config';
// Install this package if not already installed
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router } from 'react-router-dom';
import { Provider } from 'react-redux';
import CurrentCov from './CurrentCov';
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

describe('CurrentCov component', () => {
  test("Div present on the screen", () => {
    const handleToggleComponentMock = jest.fn();
    const setDetailDataObj=jest.fn()
    const mockData = [
      {
          "col": "Black",
          "kit": "NK",
          "ordcnt": 3,
          "custcnt": 3,
          "ordval": 69,
          "bkt": 0,
          "S": 0,
          "E": 0
      },
      {
          "col": "Yellow",
          "kit": "NK",
          "ordcnt": 4,
          "custcnt": 4,
          "ordval": 92,
          "bkt": 0,
          "S": 0,
          "E": 0
      },
      {
          "col": "Red",
          "kit": "NK",
          "ordcnt": 7,
          "custcnt": 7,
          "ordval": 161,
          "bkt": 0,
          "S": 0,
          "E": 0
      },
      {
          "col": "Green",
          "kit": "NK",
          "ordcnt": 3,
          "custcnt": 3,
          "ordval": 69,
          "bkt": 0,
          "S": 0,
          "E": 0
      },
      {
          "col": "Green",
          "kit": "PK",
          "ordcnt": 1,
          "custcnt": 1,
          "ordval": 23,
          "bkt": 0,
          "S": 0,
          "E": 0
      },
      {
          "col": "Black",
          "kit": "PK",
          "ordcnt": 3,
          "custcnt": 3,
          "ordval": 69,
          "bkt": 0,
          "S": 0,
          "E": 0
      },
      {
          "col": "Blue",
          "kit": "PK",
          "ordcnt": 1,
          "custcnt": 1,
          "ordval": 23,
          "bkt": "1",
          "S": 0,
          "E": 7
      },
      {
          "col": "Blue",
          "kit": "FK",
          "ordcnt": 2,
          "custcnt": 2,
          "ordval": 46,
          "bkt": "2",
          "S": 8,
          "E": 12
      },
      {
          "col": "Blue",
          "kit": "NK",
          "ordcnt": 1,
          "custcnt": 1,
          "ordval": 23,
          "bkt": "3",
          "S": 13,
          "E": 18
      },
      {
          "col": "Blue",
          "kit": "NK",
          "ordcnt": 1,
          "custcnt": 1,
          "ordval": 23,
          "bkt": "4",
          "S": 19,
          "E": 23
      },
      {
          "col": "Blue",
          "kit": "FK",
          "ordcnt": 2,
          "custcnt": 1,
          "ordval": 46,
          "bkt": "3",
          "S": 13,
          "E": 18
      },
      {
          "col": "Blue",
          "kit": "FK",
          "ordcnt": 3,
          "custcnt": 1,
          "ordval": 69,
          "bkt": "4",
          "S": 19,
          "E": 23
      },
      {
          "col": "Blue",
          "kit": "FK",
          "ordcnt": 1,
          "custcnt": 1,
          "ordval": 23,
          "bkt": "1",
          "S": 0,
          "E": 7
      }
  ]
    render(contextWrapper(<CurrentCov setDetailDataObj={setDetailDataObj}handleToggleComponent={handleToggleComponentMock} data={mockData}/>,mockedStore))
    const navigate = screen.getByTestId("btn_navigate")
    expect(navigate).toBeInTheDocument();
    fireEvent.click(navigate);
  })

});
