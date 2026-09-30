import { render, fireEvent, screen} from '@testing-library/react';

import ControlPanel from './index';
import {QueryClientProvider} from '@tanstack/react-query';
import { setupReactQuery } from '../../../../../config/react-query-config';
import { BrowserRouter as Router } from 'react-router-dom'
import { UserDataContext } from '../../../../../context';
import { Provider } from "react-redux";
import {store} from '../../../../../redux/store/store'
import { ReactNode } from "react";



const queryClient = setupReactQuery()

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
describe('Control Component', () => {




        // render(
        //     contextWrapper
        // );

        // const viewModifyCard = screen.getAllByTestId('icon-card')[0];
        // expect(viewModifyCard).toBeInTheDocument();
        // fireEvent.click(viewModifyCard);
        // expect(global.window.location.pathname).toContain('/master-data-management/control-panel/view-modify');
        // fireEvent.click(screen.getAllByTestId('icon-card')[1]);
        // fireEvent.click(screen.getAllByTestId('icon-card')[2]);

        // const buttonCard = screen.getAllByTestId('button-card');
        // fireEvent.click(buttonCard[0]);
        // fireEvent.click(buttonCard[1]);
        // fireEvent.click(buttonCard[2]);
        it("renders the controlpanel", async () => {
            render(contextWrapper(<ControlPanel />,store));
            const viewModifyCard = screen.getAllByTestId('icon-card')[0];
            expect(viewModifyCard).toBeInTheDocument();
            fireEvent.click(viewModifyCard);
            expect(global.window.location.pathname).toContain('/master-data-management/control-panel/view-modify');
            fireEvent.click(screen.getAllByTestId('icon-card')[1]);
            fireEvent.click(screen.getAllByTestId('icon-card')[2]);
        
        
          });
    
      });

    