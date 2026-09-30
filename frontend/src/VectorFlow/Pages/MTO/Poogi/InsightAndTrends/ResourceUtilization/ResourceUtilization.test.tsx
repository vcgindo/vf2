import { render, screen } from "@testing-library/react";
import '@testing-library/jest-dom/extend-expect';
import ResourceUtilization from "."; 
import { setupReactQuery } from '../../../../../../config/react-query-config';
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router } from 'react-router-dom';
import { Provider } from 'react-redux';
import { UserDataContext } from '../../../../../../context';
import { createStore } from '../../../../../../redux/store/store';

jest.mock('ag-charts-react');

const queryClient = setupReactQuery();

const dummyStore:any ={
  AnalyticsData:{}
}

const mockedStore = createStore(dummyStore)

const contextWrapper = (children: any,store:any) => {
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

describe("ResourceUtilization", () => {

  global.ResizeObserver = class MockedResizeObserver {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };

  it("renders ResourceUtilization component", () => {
    render(contextWrapper(<ResourceUtilization />, mockedStore));
    
    expect(screen.getByText("Analytics")).toBeInTheDocument();
    expect(screen.getByTestId("utilization")).toBeInTheDocument();
    expect(screen.getByTestId("wipControl")).toBeInTheDocument();
  });

  it("renders CustomSelect component", () => {
    render(contextWrapper(<ResourceUtilization />, mockedStore));
    
    const customSelect = screen.getByTestId("custom-select");
    expect(customSelect).toBeInTheDocument();
    expect(customSelect).toHaveStyle({ width: "100%" });
  });


});
