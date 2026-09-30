import React, { ReactNode } from 'react';
import { render, fireEvent, screen, waitFor } from '@testing-library/react';
import MTOActionToolBar from './MTOActionToolBar';
import moment from 'moment';
import { UserDataContext } from "../../../../../context";
import { FilterState } from '../../../../../VectorFlow/types/MTO';

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
        name: "Select Filter",
        attributeName: "select",
        type: "select",
        operator: "",
        value: "",
        options: ["option 1", "option 2"]
      },
    ],
  },
};


const contextWrapperWithCustomTheme = (children: ReactNode, theme: string) => {
  return (
    <UserDataContext.Provider
      value={{
        user: { user: { theme_ui: theme } },
        changeColorTheme: (color) => {
          return color;
        },
        isSideBarOpen: true, toggleSideBar: jest.fn
      }}
    >
      {children}
    </UserDataContext.Provider>
  );
};

describe('MTOActionToolBar Component', () => {
  // Mock functions
  const mockHandleGoBack = jest.fn();
  const mockOnDateChange = jest.fn();
  const mockSubmitDate = jest.fn();
  const mockSetIsGridView = jest.fn();
  const mockOnAddFilter = jest.fn();
  const mockRemoveFilters = jest.fn();
  const mockToggleFilter = jest.fn();
  const mockOnApplyFilter = jest.fn();
  const mockSetCurrFilter = jest.fn();
  const mockOnFilterRemove = jest.fn();
  const mockOnSaveClick = jest.fn();
  const mockOnResetClick = jest.fn();

  global.ResizeObserver = class MockedResizeObserver {
    observe = jest.fn();
    unobserve = jest.fn();
    disconnect = jest.fn();
  };


  const selectedFilters = [
    { label: 'Plant Name', values: ['Plant 1'] },
  ];

  const date = moment(new Date()).format('YYYY-MM-DD');

  test('renders without crashing', () => {
    render(<MTOActionToolBar />);
  });

  test('calls handleGoBack function when Go Back button is clicked', () => {
    render(<MTOActionToolBar isGoBackButton handleGoBack={mockHandleGoBack} />);
    fireEvent.click(screen.getByText('Go Back'));
    expect(mockHandleGoBack).toHaveBeenCalled();
  });

  test('calls save Grid UI Config function when Save button is clicked', () => {
    render(<MTOActionToolBar isGoBackButton handleResetClick={mockOnResetClick} handleSaveClick={mockOnSaveClick} />);
    fireEvent.click(screen.getByText('Save'));
    expect(mockOnSaveClick).toHaveBeenCalled();
  });

  test('Donot renders save button', () => {
    render(<MTOActionToolBar isGoBackButton />);
    expect(screen.queryByText('Save')).not.toBeInTheDocument();
  });

  test('Donot renders reset button', () => {
    render(<MTOActionToolBar isGoBackButton />);
    expect(screen.queryByText('Reset')).not.toBeInTheDocument();
  });

  test('calls reset Grid UI Config function when Reset button is clicked', () => {
    render(<MTOActionToolBar isGoBackButton handleResetClick={mockOnResetClick} handleSaveClick={mockOnSaveClick} />);
    fireEvent.click(screen.getByText('Reset'));
    expect(mockOnResetClick).toHaveBeenCalled();
  });

  test('calls onDateChange function with selected date', () => {
    render(<MTOActionToolBar isReleaseDate onDateChange={mockOnDateChange} date={date} />);
    const dateInput = screen.getByTestId('datepicker');
    fireEvent.change(dateInput, { target: { value: '2024-06-28' } });
    expect(mockOnDateChange).toHaveBeenCalledWith('2024-06-28');
  });


  it('renders correctly and triggers submitDate on click', () => {
    const submitDateMock = jest.fn(); // Mock function for submitDate
    const { getByTestId } = render(<MTOActionToolBar isReleaseDate submitDate={submitDateMock} date={date} />
    );
    // Check if the component is rendered
    const button = getByTestId('Group 627');
    expect(button).toBeInTheDocument();

    // Check if the image is rendered correctly
    const arrowImage = button.querySelector('img');
    expect(arrowImage).toBeInTheDocument();
    expect(arrowImage).toHaveAttribute('src', '/assets/img/rightArrowHorizontal.svg');

    // Simulate a click on the div
    fireEvent.click(button);
    // Assert that submitDate was called
    expect(submitDateMock).toHaveBeenCalled();
  });

  test('calls setIsGridView function when Chart View or Grid View toggle button is clicked', () => {
    render(<MTOActionToolBar isChartGridToggle setIsGridView={mockSetIsGridView} isGridView />);
    fireEvent.click(screen.getByText('Chart View'));
    expect(mockSetIsGridView).toHaveBeenCalled();

    fireEvent.click(screen.getByText('Grid View'));
    expect(mockSetIsGridView).toHaveBeenCalled();
  });

  test('renders Go Back button when isGoBackButton is true', () => {
    render(<MTOActionToolBar isGoBackButton handleGoBack={mockHandleGoBack} />);
    const goBackButton = screen.getByText('Go Back');
    expect(goBackButton).toBeInTheDocument();
    fireEvent.click(goBackButton);
    expect(mockHandleGoBack).toHaveBeenCalled();
  });

  // test('renders date picker and submit button when isReleaseDate is true', () => {
  //   render(<MTOActionToolBar isReleaseDate onDateChange={mockOnDateChange} submitDate={mockSubmitDate} date="2024-06-28" />);
  //   const datePicker = screen.getByTestId('datepicker');
  //   expect(datePicker).toBeInTheDocument();
  //   fireEvent.change(datePicker, { target: { value: '2024-06-29' } });
  //   expect(mockOnDateChange).toHaveBeenCalledWith('2024-06-29');
  //   const submitButton = screen.getByAltText(/Group 627/);
  //   fireEvent.click(submitButton);
  //   expect(mockSubmitDate).toHaveBeenCalled();
  // });
  /*it('renders correctly with the image and handles click event', () => {
    const onOrderReleaseMock = jest.fn(); // Mock function for onOrderRelease
        const { getByTestId } = render(<MTOActionToolBar onOrderRelease={onOrderReleaseMock} />);

        // Check if the component div is rendered
        const button = getByTestId('isReleaseBtn');
        expect(button).toBeInTheDocument();

        // Check if the image is rendered correctly
        const arrowImage = button.querySelector('img');
        expect(arrowImage).toBeInTheDocument();
        expect(arrowImage).toHaveAttribute('src', '/assets/img/rightArrowHorizontal.svg');
        expect(arrowImage).toHaveAttribute('height', '13');
        expect(arrowImage).toHaveAttribute('width', '7');

        // Simulate a click on the div
        fireEvent.click(button);

        // Assert that onOrderRelease was called
        expect(onOrderReleaseMock).toHaveBeenCalled();
});*/

  test('renders As on Date when isAsOnDate is true', () => {
    render(<MTOActionToolBar isAsOnDate />);
    expect(screen.getByText('As on Date')).toBeInTheDocument();
  });

  test('renders when remove filters is invoked', () => {
    render(<MTOActionToolBar selectedFilters={selectedFilters} removeFilters={mockRemoveFilters} />);
    expect(screen.getByTestId('closeIcon-filter')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('closeIcon-filter'));
    expect(mockRemoveFilters).toHaveBeenCalled();
  });

  test('renders when remove filters is not invoked', () => {
    render(<MTOActionToolBar selectedFilters={selectedFilters} />);
    expect(screen.getByTestId('closeIcon-filter')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('closeIcon-filter'));
    expect(mockRemoveFilters).not.toHaveBeenCalled();
  });

  test('renders with multiple selected filters', () => {
    const filters = [
      { label: 'Plant Name', values: ['Plant 1', 'Plant 2'] },
      { label: 'Department', values: ['Dept 1'] }
    ];
    render(<MTOActionToolBar selectedFilters={filters} removeFilters={mockRemoveFilters} />);
    filters.forEach(filter => {
      filter.values.forEach(value => {
        expect(screen.getByText(value)).toBeInTheDocument();
      });
    });
  });

  test('calls removeFilters function for each filter value', () => {
    const filters = [
      { label: 'Plant Name', values: ['Plant 1'] }
    ];
    render(<MTOActionToolBar selectedFilters={filters} removeFilters={mockRemoveFilters} />);
    filters[0].values.forEach(value => {
      fireEvent.click(screen.getAllByTestId('closeIcon-filter')[0]);
      expect(mockRemoveFilters).toHaveBeenCalledWith(filters[0].label, value);
    });
  });

  test('renders Add/Edit Filter button and calls onAddFilter when clicked', () => {
    render(<MTOActionToolBar isAddFilterButton onAddFilter={mockOnAddFilter} selectedFilters={selectedFilters} />);
    expect(screen.getByText('Edit Filter')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Edit Filter'));
    expect(mockOnAddFilter).toHaveBeenCalled();

    render(<MTOActionToolBar isAddFilterButton onAddFilter={mockOnAddFilter} />);
    expect(screen.getByText('+ Add Filter')).toBeInTheDocument();
    fireEvent.click(screen.getByText('+ Add Filter'));
    expect(mockOnAddFilter).toHaveBeenCalled();
  });



  test('renders Excel Export button', () => {
    render(<MTOActionToolBar isExcelExport />);
    const excelExportButton = screen.getByText('Excel Export');
    expect(excelExportButton).toBeInTheDocument();
  });


  // it('renders isReleaseButton button', () => {
  //   const { getByTestId } = render(<MTOActionToolBar isReleaseButton />);
  //   const button = getByTestId('isReleaseBtn');
  //   expect(button).toBeInTheDocument();
  //   const arrowImage = button.querySelector('img');
  //   expect(arrowImage).toBeInTheDocument();
  //   expect(arrowImage).toHaveAttribute('src', '/assets/img/rightArrowHorizontal.svg');
  //   expect(arrowImage).toHaveAttribute('height', '13');
  //   expect(arrowImage).toHaveAttribute('width', '7');
  // });


  it('renders with different themes', () => {
    const submitDateMock = jest.fn(); // Mock function for submitDate
    const { getByTestId } = render(contextWrapperWithCustomTheme(<MTOActionToolBar isReleaseDate submitDate={submitDateMock} date={date} />, "REGALBLAZE"));
    const button = getByTestId('Group 627');
    expect(button).toBeInTheDocument();
    const arrowImage = button.querySelector('img');
    expect(arrowImage).toBeInTheDocument();
    expect(arrowImage).toHaveAttribute('src', '/assets/img/rightArrowHorizontal.svg');
    fireEvent.click(button);
    expect(submitDateMock).toHaveBeenCalled();
  });

  test('renders isReleaseDate', () => {
    render(contextWrapperWithCustomTheme(<MTOActionToolBar isReleaseDate submitDate={mockSubmitDate} date={date} />, "REGALBLAZE"));
    const isReleaseDate = screen.getByTestId("isReleaseDate");
    expect(isReleaseDate).toBeInTheDocument();
  });

  test('renders isAsOnDate', () => {
    render(contextWrapperWithCustomTheme(<MTOActionToolBar isAsOnDate submitDate={mockSubmitDate} date={date} />, "REGALBLAZE"));
    const isAsOnDate = screen.getByTestId("isAsOnDate");
    expect(isAsOnDate).toBeInTheDocument();
  });

  test('renders isAsOnDate', async () => {
    render(contextWrapperWithCustomTheme(<MTOActionToolBar
      isChartGridToggle
      isAddFilterButton
      isFilterOpen={true}
      onAddFilter={mockOnAddFilter}
      toggleFilter={mockToggleFilter}
      onApplyFilter={mockOnApplyFilter}
      multiFilter={multiFilterMock}
      setMultiFilter={mockSetCurrFilter} />,
      "REGALBLAZE"));

    await waitFor(async () => expect(screen.getByTestId("vfmodal-img")).toBeInTheDocument())

    await waitFor(async () => {
      const goBackButton = screen.getByText("Go Back!");
      expect(goBackButton).toBeInTheDocument()
      const applybutton = screen.getByText("Apply Filter");
      expect(applybutton).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText("Apply Filter"));
    expect(mockSetCurrFilter).toHaveBeenCalledWith(multiFilterMock);
    expect(mockOnApplyFilter).toHaveBeenCalledTimes(1);

  });

  test('renders go back ', async () => {
    render(contextWrapperWithCustomTheme(<MTOActionToolBar
      isChartGridToggle
      isAddFilterButton
      isFilterOpen={true}
      onAddFilter={mockOnAddFilter}
      toggleFilter={mockToggleFilter}
      onApplyFilter={mockOnApplyFilter}
      multiFilter={multiFilterMock}
      setMultiFilter={mockSetCurrFilter} />,
      "REGALBLAZE"));

    await waitFor(async () => expect(screen.getByTestId("vfmodal-img")).toBeInTheDocument())

    await waitFor(async () => {
      const goBackButton = screen.getByText("Go Back!");
      expect(goBackButton).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText("Go Back!"));
    expect(mockToggleFilter).toHaveBeenCalledTimes(1);

  });

  test('renders with multiple selected filters from common filter modal', async () => {
    const multiFilterMock = {
      customers: {
        "id": "cus",
        "label": "Customer Filter",
        "filters": [
          {
            "type": "search",
            "name": "Customer Code",
            "attributeName": "cc",
            "operator": "",
            "value": [
              {
                "label": 1,
                "value": 1
              }
            ],
            "options": [
              {
                "label": "Cust 1",
                "value": "Cust 1"
              },
              {
                "label": "Cust 2",
                "value": "Cust 2"
              },
              {
                "label": "Cust 3",
                "value": "Cust 3"
              },
              {
                "label": 1,
                "value": 1
              },
              {
                "label": 2,
                "value": 2
              },
              {
                "label": 3,
                "value": 3
              }
            ]
          },
          {
            "type": "search",
            "name": "Customer Name",
            "attributeName": "cn",
            "operator": "",
            "value": [
              {
                "label": "Customer 1",
                "value": "Customer 1"
              },
              {
                "label": "Customer 2",
                "value": "Customer 2"
              }
            ],
            "options": [
              {
                "label": "Customer 1",
                "value": "Customer 1"
              },
              {
                "label": "Customer 2",
                "value": "Customer 2"
              }
            ]
          }
        ]
      },
    };

    const newFilters: any = {
      "customers": {
        "name": "Customer Filter",
        "parentId": "customers",
        "filters": [
          {
            "filterId": "cc",
            "type": "search",
            "operator": "",
            "label": "Customer Code",
            "value": [
              {
                "label": 1,
                "value": 1
              }
            ]
          },
          {
            "filterId": "cn",
            "type": "search",
            "operator": "",
            "label": "Customer Name",
            "value": [
              {
                "label": "Customer 1",
                "value": "Customer 1"
              },
              {
                "label": "Customer 2",
                "value": "Customer 2"
              }
            ]
          }
        ]
      }
    }
    render(contextWrapperWithCustomTheme(<MTOActionToolBar
      isChartGridToggle
      isAddFilterButton
      isFilterOpen={false}
      onAddFilter={mockOnAddFilter}
      toggleFilter={mockToggleFilter}
      onApplyFilter={mockOnApplyFilter}
      multiFilter={multiFilterMock}
      setMultiFilter={mockSetCurrFilter}
      onFilterRemove={mockOnFilterRemove} />,
      "REGALBLAZE"));

    await waitFor(async () => {
      // expect(screen.getByText("Apply Filter")).not.toBeInTheDocument()

      Object.keys(newFilters).forEach(key => {
        expect(screen.getByText(newFilters[key].name)).toBeInTheDocument();
        newFilters[key].filters.forEach((filter: any) => {
          // expect(screen.getByText(filter.label)).toBeInTheDocument();
          filter.value.forEach((val: any) => {
            expect(screen.getByText(val.label)).toBeInTheDocument();
          })
        });
      });


      fireEvent.click(screen.getAllByTestId('closeIcon-filter')[0]);
      expect(mockOnFilterRemove).toHaveBeenCalled();
    })

  });

  test('donot renders cross btn with disable remove filters', () => {
    render(<MTOActionToolBar multiFilter={multiFilterMock} disableRemoveFilter removeFilters={mockRemoveFilters} />);
    expect(screen.queryByTestId('closeIcon-filter')).not.toBeInTheDocument();
  });

});
