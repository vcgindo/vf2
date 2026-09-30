import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom/extend-expect';
import RMPMOrderwiseCoverage from './index';
import React, { ReactNode } from 'react';
import { setupReactQuery } from '../../../../../../config/react-query-config';
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router } from 'react-router-dom';
import { Provider } from 'react-redux';
import { UserDataContext } from '../../../../../../context';
import { createStore } from '../../../../../../redux/store/store';


const queryClient = setupReactQuery();

const dummyStore: any = {
    AnalyticsData: {}
}

const mockedStore = createStore(dummyStore)

const contextWrapper = (children: ReactNode, store: any) => {
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



jest.mock('./GridView/GridView', () => ({
    __esModule: true,
    default: () => <div>GridView Mock</div>,
}));

jest.mock('./GraphView/GraphView', () => ({
    __esModule: true,
    default: () => <div>GraphView Mock</div>,
}));

describe('RMPM Component', () => {
    test('renders GraphView by default', () => {
        render(contextWrapper(<RMPMOrderwiseCoverage />, mockedStore));
        expect(screen.getByText('GraphView Mock')).toBeInTheDocument();
    });

    test('switches to GridView when the Grid View button is clicked', () => {
        render(contextWrapper(<RMPMOrderwiseCoverage />, mockedStore));
        fireEvent.click(screen.getByText('Grid View'));
        expect(screen.getByText('GridView Mock')).toBeInTheDocument();
    });
}
);

