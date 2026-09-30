import React, { ReactNode } from 'react';
import { render,waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import GridView from './';
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router } from 'react-router-dom';
import { Provider } from 'react-redux';
import { UserDataContext } from '../../../../../context';
import { createStore } from '../../../../../redux/store/store';
import { setupReactQuery } from '../../../../../config/react-query-config';

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

describe('GridView Component', () => {

    const getDataMock = jest.fn();
    const setCurrentGridRefMock = jest.fn();

    const defaultProps = {
        getData: getDataMock,
        colDef: [],
        isLoading: false,
        isError: false,
        isSuccess: false,
        setCurrentGridRef: setCurrentGridRefMock,
        currentGridRef: null,
        columnState: [],
        appliedFilters: {}
    };

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('should trigger getData on mount', () => {
        render(contextWrapper(<GridView {...defaultProps} />, mockedStore));

        expect(getDataMock).toHaveBeenCalledTimes(1);
        expect(getDataMock).toHaveBeenCalledWith({ graphflag: 0, page: 1, appliedFilters: {} });
    });

    test('should apply column state when grid is ready', async () => {
        const currentGridRefMock = { current: { api: { applyColumnState: jest.fn() } } };

        render(contextWrapper(<GridView {...defaultProps} currentGridRef={currentGridRefMock} columnState={[{ colId: 'test' }]} colDef={[{ field: 'test' }]} />, mockedStore));

        await waitFor(() => {
            expect(currentGridRefMock.current.api.applyColumnState).toHaveBeenCalledWith({
                state: [{ colId: 'test' }],
                applyOrder: true,
            });
        });
    });

});
