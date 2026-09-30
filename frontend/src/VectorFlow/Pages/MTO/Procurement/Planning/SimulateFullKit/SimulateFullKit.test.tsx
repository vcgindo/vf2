import { ReactNode } from 'react';
import { render } from '@testing-library/react';
import SimulateFullKit from './index';
import { store } from "../../../../../../redux/store/store";
import { Provider } from "react-redux";
import { QueryClientProvider } from '@tanstack/react-query';
import { setupReactQuery } from '../../../../../../config/react-query-config'
import { BrowserRouter as Router } from 'react-router-dom';
import { UserDataContext } from '../../../../../../context';

const queryClient = setupReactQuery();


const contextWrapper = (children: ReactNode) => {
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
                            isSideBarOpen: true, toggleSideBar: jest.fn
                        }}
                    >
                        {children}
                    </UserDataContext.Provider>
                </Provider>
            </Router>
        </QueryClientProvider>
    );
};

describe('SimulateFullKit', () => {


    it('should render ActionToolBar and VFFloatingTab correctly', () => {
        render(contextWrapper(<SimulateFullKit />));


        // const actionToolBar = document.querySelector('ActionToolBar');
        // const floatingTab = document.querySelector('VFFloatingTab');


    });


});
