import { ReactNode } from 'react';

import { fireEvent, render, screen, waitFor} from '@testing-library/react';
import { setupReactQuery } from '../../../../../../config/react-query-config';
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router } from 'react-router-dom';
import { Provider } from 'react-redux';
import { UserDataContext } from '../../../../../../context';
import { createStore } from '../../../../../../redux/store/store';
import BMTrends from '.';

jest.mock('ag-charts-react');

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

describe('BMTrends Component', () => {
    
    // test('to check capsule action toolbar render properly', () => {
    //     render(contextWrapper(<BMTrends />, mockedStore));
    //     expect(screen.getByText('+ Add Filter')).toBeInTheDocument();
    // });

    test('toggles between Percentage and Absolute Value and updates the chart', async () => {
      render(contextWrapper(<BMTrends />, mockedStore));

      const capsuleButton = screen.getByText('Percentage');
      fireEvent.click(capsuleButton);

      await waitFor(() => {
          expect(screen.getByText('Absolute Value')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Absolute Value'));

      await waitFor(() => {
          expect(screen.getByText('Percentage')).toBeInTheDocument();
      });
  });

});