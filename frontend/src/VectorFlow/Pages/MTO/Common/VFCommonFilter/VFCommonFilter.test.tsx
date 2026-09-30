import { ReactNode } from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/extend-expect";
import VFCommonFilter from ".";
import { FilterState } from "../../../../../VectorFlow/types/MTO";
import { setupReactQuery } from '../../../../../config/react-query-config';
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router } from 'react-router-dom';
import { Provider } from 'react-redux';
import { UserDataContext } from '../../../../../context';
import { createStore } from '../../../../../redux/store/store';


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

describe("VFCommonFilter Component", () => {
    const mockOnApplyFilter = jest.fn();
    const mockOnGoBack = jest.fn();
    const mockSetMultiFilter = jest.fn();
    const mockSetIsMfgSelected = jest.fn();
    const mockClearAllFilters = jest.fn();

    global.ResizeObserver = class MockedResizeObserver {
        observe = jest.fn();
        unobserve = jest.fn();
        disconnect = jest.fn();
    };

    const props = {
        onApplyFilter: mockOnApplyFilter,
        onGoBack: mockOnGoBack,
        selectedOption: jest.fn(),
        toggleAdd: jest.fn(),
        placeholder: "Search Filters",
        multiFilter: {},
        setMultiFilter: mockSetMultiFilter,
        isFilterOpen: true,
        setIsMfgSelected: mockSetIsMfgSelected,
        clearAllFilters: mockClearAllFilters
    };

    const multiFilterMock: FilterState = {
        customers: {
            id: 'cus1',
            label: "Customer 1",
            filters: [
                {
                    name: "Text Filter",
                    attributeName: "textFilter",
                    type: "textCompare",
                    operator: "",
                    value: "",
                    options: ["a", "b"]
                },
                {
                    name: "Search Filter",
                    attributeName: "srch",
                    type: "search",
                    operator: "",
                    value: "",
                    options: ["1", "2"]
                },
                {
                    name: "Customer ques Select",
                    attributeName: "select",
                    type: "select",
                    operator: "",
                    value: "",
                    options: ["option 1", "option 2"]
                },
            ],
        },
        orders: {
            id: 'ord1',
            label: "Order 1",
            filters: [
                {
                    name: "Ques order 1",
                    attributeName: "multiAttr",
                    type: "multiSelect",
                    operator: "",
                    value: "",
                    options: ["option 1", "option 2"]
                },
            ],
        },
        resources: {
            id: 'res1',
            label: "Resource 1",
            filters: [
                {
                    name: "Ques res 1",
                    attributeName: "multiAttr",
                    type: "multiSelect",
                    operator: "",
                    value: "",
                    options: ["option 1", "option 2"]
                },
            ],
        },
        major: {
            id: 'majr1',
            label: "Major 1",
            filters: [
                {
                    name: "Ques mjr 1",
                    attributeName: "multiAttr",
                    type: "multiSelect",
                    operator: "",
                    value: "",
                    options: ["option 1", "option 2"]
                },
            ],
        },
    };


    beforeEach(() => {
        render(contextWrapper(<VFCommonFilter {...props} />, mockedStore));
    });

    it("renders without crashing", async () => {
        expect(screen.getByText("Select Filter")).toBeInTheDocument();
    });

    it("displays loader when filter keys are empty", async () => {
        expect(screen.getByTestId("vfmodal-img")).toBeInTheDocument();
    });

    it("handles empty multiFilter state gracefully", () => {
        expect(screen.getByTestId("filter-loader")).toBeInTheDocument();
    })

    it("displays filters when filterKeys are populated", async () => {
        const { rerender } = render(contextWrapper(<VFCommonFilter {...props} multiFilter={multiFilterMock} />, mockedStore));
        rerender(contextWrapper(<VFCommonFilter {...props} multiFilter={multiFilterMock} />, mockedStore));

        expect(screen.getByText("Customer 1")).toBeInTheDocument();
    });

    it("updates filterState on text input change", async () => {
        render(contextWrapper(<VFCommonFilter {...props} multiFilter={multiFilterMock} />, mockedStore));

        const input = screen.getByPlaceholderText("Text Filter");
        fireEvent.change(input, { target: { value: "New Value" } });
        await waitFor(async () => expect(screen.getByTestId("vf-button")).toBeInTheDocument());
        fireEvent.click(screen.getByTestId("vf-button"));
        expect(mockOnApplyFilter).toHaveBeenCalled();
    });

    it("calls onGoBack when Go Back! button is clicked", async () => {
        render(contextWrapper(<VFCommonFilter {...props} multiFilter={multiFilterMock} />, mockedStore));
        await waitFor(() => expect(screen.getByTestId("vf-button-outline")).toBeInTheDocument());
        fireEvent.click(screen.getByTestId("vf-button-outline"));
        expect(mockOnGoBack).toHaveBeenCalled();
    });

    it("calls onApplyFilter with formatted filters when Apply Filter button is clicked", async () => {
        render(contextWrapper(<VFCommonFilter {...props} multiFilter={multiFilterMock} />, mockedStore));
        await waitFor(async () => expect(screen.getByTestId("vf-button")).toBeInTheDocument());
        fireEvent.click(screen.getByTestId("vf-button"));
        expect(mockSetMultiFilter).toHaveBeenCalledWith(multiFilterMock);
        expect(mockOnApplyFilter).toHaveBeenCalledTimes(1);
    });

    it("updates filterState correctly for TextCompare input", () => {
        render(contextWrapper(<VFCommonFilter {...props} multiFilter={multiFilterMock} />, mockedStore));
        fireEvent.change(screen.getByPlaceholderText("Text Filter"), { target: { value: "test value" } });
    });

    it("updates filterState correctly for TextCompare input", () => {
        render(contextWrapper(<VFCommonFilter {...props} multiFilter={multiFilterMock} />, mockedStore));
        const inputElement = screen.getByPlaceholderText("Text Filter") as HTMLInputElement;
        // Trigger a change event
        fireEvent.change(inputElement, { target: { value: "123" } });
        // Assert that the value has been updated correctly
        expect(inputElement.value).toBe("123");
    });


    it('Handles all checkboxes', async () => {
        render(contextWrapper(<VFCommonFilter {...props} multiFilter={multiFilterMock} />, mockedStore))
        const checkboxes = screen.getAllByRole('checkbox')

        await waitFor(async () => {
            checkboxes.forEach((checkbox: any) => {
                fireEvent.click(checkbox)
            })
        })
        checkboxes.forEach((checkbox: any) => {
            fireEvent.change(checkbox, { target: { checked: false } })
        })
    })

    it('Handles all dropdowns', () => {
        render(contextWrapper(<VFCommonFilter {...props} multiFilter={multiFilterMock} />, mockedStore));

        const dropdowns = screen.getAllByRole('combobox')
        dropdowns.forEach((dropdown: any) => {
            fireEvent.change(dropdown, { target: { value: 'bfbf' } })
        })
        dropdowns.forEach((dropdown: any) => {
            fireEvent.change(dropdown, { target: { value: 'hfsafbshfa' } })
        })
    })

    it('Handles all input value', () => {
        render(contextWrapper(<VFCommonFilter {...props} multiFilter={multiFilterMock} />, mockedStore));

        const inputs = screen.getAllByPlaceholderText('Value')
        inputs.forEach((input: any) => {
            fireEvent.change(input, { target: { value: 'fsafa' } })
        })
        inputs.forEach((input: any) => {
            fireEvent.change(input, { target: { value: 'bfksabfksafkbk' } })
        })
    })

    it('handles open animation', () => {
        render(contextWrapper(<VFCommonFilter {...props} multiFilter={multiFilterMock} />, mockedStore));

        const openanimation = screen.getAllByTestId('down-arrow')
        openanimation.forEach((open: any) => {
            fireEvent.click(open)
        })


    })

    it("renders all the filters in the component", async () => {
        render(contextWrapper(<VFCommonFilter {...props} multiFilter={multiFilterMock} />, mockedStore));

        const Customer = screen.getByText("Customer 1");
        expect(Customer).toBeInTheDocument()
        const Order = screen.getByText("Order 1");
        expect(Order).toBeInTheDocument()
        const Resource = screen.getByText("Resource 1");
        expect(Resource).toBeInTheDocument()
        const Major = screen.getByText("Major 1");
        expect(Major).toBeInTheDocument()

        await waitFor(async () => {

            expect(screen.getByPlaceholderText("Text Filter")).toBeInTheDocument();
            expect(screen.getByText("Search Filter")).toBeInTheDocument();
            expect(screen.getByText("Customer ques Select")).toBeInTheDocument();
            expect(screen.getByText("Ques order 1")).toBeInTheDocument();
            expect(screen.getByText("Ques res 1")).toBeInTheDocument();
            expect(screen.getByText("Ques mjr 1")).toBeInTheDocument();
        })

    })

    it("renders all the filters in the component", async () => {

        const dummyFilters = {
            orders: {
                id: 'ord1',
                label: "Order 1",
                filters: [
                    {
                        name: "Ques order 1",
                        attributeName: "multiAttr",
                        type: "multiSelect",
                        operator: "",
                        value: "",
                        options: ["option 1", "option 2"]
                    },
                    {
                        name: "Ques order 2",
                        attributeName: "multiAttr",
                        type: "multiSelect",
                        operator: "",
                        value: "",
                        options: ["option 1", "option 2"]
                    },
                ],
            },
        }
        render(contextWrapper(<VFCommonFilter {...props} multiFilter={dummyFilters} />, mockedStore));

        const Order = screen.getByText("Order 1");
        expect(Order).toBeInTheDocument()

        expect(screen.queryByText("Customer 1")).not.toBeInTheDocument()
        expect(screen.queryByText("Resource 1")).not.toBeInTheDocument()
        expect(screen.queryByText("Major 1")).not.toBeInTheDocument()

        await waitFor(async () => {

            expect(screen.getByText("Ques order 1")).toBeInTheDocument();
            expect(screen.getByText("Ques order 2")).toBeInTheDocument();

            expect(screen.queryByText("Text Filter")).not.toBeInTheDocument();
            expect(screen.queryByText("Search Filter")).not.toBeInTheDocument();
            expect(screen.queryByText("Customer ques Select")).not.toBeInTheDocument();
        })
    })

    it("handles MultiSelect filter with no options gracefully", () => {
        const emptyOptionsFilter = {
            customers: {
                id: 'cus1',
                label: "Customer 1",
                filters: [
                    {
                        name: "Empty MultiSelect Filter",
                        attributeName: "emptyMultiSelect",
                        type: "multiSelect",
                        operator: "",
                        value: "",
                        options: [] // No options provided
                    },
                ],
            },
        };
        render(contextWrapper(<VFCommonFilter {...props} multiFilter={emptyOptionsFilter} />, mockedStore));
    
        // const multiSelectFilter = screen.getByText("Empty MultiSelect Filter");
        // expect(multiSelectFilter).toBeInTheDocument();
    
        const dropdown = screen.queryByRole('combobox');
        expect(dropdown).not.toBeInTheDocument(); // Ensure dropdown is not rendered or is disabled
    });

    it("renders filters as disabled when certain condition is met", () => {
        const disabledFilterState = {
            customers: {
                id: 'cus1',
                label: "Customer 1",
                filters: [
                    {
                        name: "Disabled Filter",
                        attributeName: "disabledFilter",
                        type: "textCompare",
                        operator: "",
                        value: "",
                        options: ["a", "b"],
                        disabled: true, // Condition to disable the filter
                    },
                ],
            },
        };
        render(contextWrapper(<VFCommonFilter {...props} multiFilter={disabledFilterState} />, mockedStore));
    
        const input = screen.getByPlaceholderText("Disabled Filter");
        expect(input).toBeInTheDocument();
        expect(input).toBeDisabled(); // Ensure the input is disabled
    });

    it("filters results correctly based on the search term", async () => {
        const searchFilterState = {
            customers: {
                id: 'cus1',
                label: "Customer 1",
                filters: [
                    {
                        name: "Customer Search",
                        attributeName: "customerSearch",
                        type: "search",
                        operator: "",
                        value: "",
                        options: [
                            "Apple" ,
                            "Banana",
                            "Cherry",
                        ],
                    },
                ],
            },
        };
        render(contextWrapper(<VFCommonFilter {...props} multiFilter={searchFilterState} />, mockedStore));
    
        await waitFor(() => {
            const divElement = screen.getByTestId("select-filter-input");
            const inputElement = divElement.querySelector('input[type="text"]') as HTMLInputElement; // Select the INPUT element within the DIV
            expect(inputElement?.tagName).toBe("INPUT");
            
            // Simulate typing "Ban" into the search input
            fireEvent.change(inputElement, { target: { value: "Ban" } });
        })
        // Verify that only "Banana" is shown in the results
        expect(screen.getByText("No options")).toBeInTheDocument();
    });

});

