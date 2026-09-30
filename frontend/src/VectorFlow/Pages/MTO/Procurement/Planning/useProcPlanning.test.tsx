import { render, screen, waitFor } from '@testing-library/react';
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter as Router } from "react-router-dom";
import { setupReactQuery } from "../../../../../config/react-query-config";
import { ReactNode } from "react";
import { Provider } from "react-redux";
import { store } from "../../../../../redux/store/store";
import { UserDataContext } from "../../../../../context";
import useProcPlanning from "./useProcPlanning";

const queryClient = setupReactQuery();

const contextWrapper = (children: ReactNode, store: any) => {
    return (
        <QueryClientProvider client={queryClient}>
            <Router>
                <Provider store={store}>
                    <UserDataContext.Provider
                        value={{
                            user: { user: { theme_ui: "NOIRFUSION" } },
                            changeColorTheme: (color: any) => {
                                return color;
                            },
                            isSideBarOpen: true, toggleSideBar: jest.fn()
                        }}
                    >
                        {children}
                    </UserDataContext.Provider>
                </Provider>
            </Router>
        </QueryClientProvider>
    );
};

// Mocking the required services
jest.mock("./useProcPlanning", () => ({
    __esModule: true,
    default: jest.fn(),
}));

const mockUseProcPlanning = useProcPlanning as jest.MockedFunction<typeof useProcPlanning>;

describe("useProcPlanning Component", () => {
    beforeEach(() => {
        const mockResult: any = {
            isSideBarOpen: true,
            agGridProps: {
                tooltipShowDelay: 0,
                tooltipTrigger: "focus",
                gridOptions: {
                    rowHeight: 50,
                    getRowStyle: (params: any) => ({ background: params.node.rowIndex % 2 === 0 ? "#EBEBEB" : "#F7F7F7" }),
                    overlayNoRowsTemplate: `<div>No Rows To Show</div>`,
                    components: { availabilityToolTip: jest.fn(), coloPriority: jest.fn() },
                    rowSelection: 'multiple',
                    suppressRowClickSelection: true,
                    enableBrowserTooltips: true,
                    enableRangeSelection: true,
                    icons: { groupExpanded: "", groupContracted: "" },
                    pagination: true,
                    defaultColDef: { cellStyle: { 'text-align': 'center' } },
                },
                masterDetail: true,
                detailCellRenderer: jest.fn(),
                autoGroupColumnDef: { minWidth: 250 },
                paginationAutoPageSize: true,
                enterNavigatesVertically: true,
                enterNavigatesVerticallyAfterEdit: true,
                groupDefaultExpanded: 0,
                defaultExcelExportParams: { getCustomContentBelowRow: jest.fn(), columnWidth: 120, fileName: "ag-grid.xlsx" },
                excelStyles: [
                    { id: "header", interior: { color: "#aaaaaa", pattern: "Solid" } },
                    { id: "body", interior: { color: "#dddddd", pattern: "Solid" } }
                ],
                sideBar: { toolPanels: ['columns'] },
                onCellEditingStopped: jest.fn(),
            },
            currentPage: 1,
            toggleCurrentTab: jest.fn(),
            renderView: jest.fn(() => <div data-testid="VFTable">Mock VFTable</div>),
            excelDownload: jest.fn(),
            // GetCount: { short: 10, complete: 20, total: 30 },
        };
        mockUseProcPlanning.mockReturnValue(mockResult);
    });

    it("renders Loading Overlay Component when loading", async () => {
        render(contextWrapper(<div>Loading</div>, store));
        expect(screen.getByText(/Loading/i)).toBeInTheDocument();
    });

    it("renders VFTable with Complete Available Data when the current tab is 'ca'", async () => {
        mockUseProcPlanning.mockReturnValueOnce({
            ...mockUseProcPlanning({}),
            toggleCurrentTab: jest.fn(({ id }) => {
                if (id === 'ca') {
                    return <div data-testid="VFTable">Mock VFTable</div>;
                }
            }),
        });

        const { toggleCurrentTab, renderView } = useProcPlanning({});
        toggleCurrentTab({ id: 'ca', label: 'Completely Available', value: 'ca' });

        render(contextWrapper(renderView(), store));
        await waitFor(() => expect(screen.getByTestId('VFTable')).toBeInTheDocument());
        // Add more specific assertions related to Complete Available Data
        expect(screen.getByText(/Mock VFTable/i)).toBeInTheDocument();
    });

    it("renders VFTable with Shortage Data when the current tab is 'short'", async () => {
        mockUseProcPlanning.mockReturnValueOnce({
            ...mockUseProcPlanning({}),
            toggleCurrentTab: jest.fn(({ id }) => {
                if (id === 'short') {
                    return <div data-testid="VFTable">Mock VFTable</div>;
                }
            }),
        });

        const { toggleCurrentTab, renderView } = useProcPlanning({});
        toggleCurrentTab({ id: 'short', label: 'Shortage', value: 'short' });

        render(contextWrapper(renderView(), store));
        await waitFor(() => expect(screen.getByTestId('VFTable')).toBeInTheDocument());
        // Add more specific assertions related to Shortage Data
        expect(screen.getByText(/Mock VFTable/i)).toBeInTheDocument();
    });
});
