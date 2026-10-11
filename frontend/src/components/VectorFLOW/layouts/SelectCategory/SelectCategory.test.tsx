import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { configureStore } from "@reduxjs/toolkit";
import { ReactNode } from "react";
import { Provider } from "react-redux";
import { BrowserRouter } from "react-router-dom";
import { setupReactQuery } from "../../../../config/react-query-config";
import { UserDataContext } from "../../../../context";
import SelectCategory from ".";

const dummyProps = {
  businessDate: "19 Sep 2026",
  childMonitorCount: 100,
  parentMonitorCount: 100,
  childExpediteCount: 100,
  parentExpediteCount: 100,
  reviewExcessInventoryCount: 100,
  reviewOrderFulfillmentCount: 100,
  onMonitorParentClick: jest.fn(),
  onMonitorChildClick: jest.fn(),
  onExpediteParentClick: jest.fn(),
  onExpediteChildClick: jest.fn(),
  onExcessInventoryReviewClick: jest.fn(),
  onOrderFulfillmentReviewClick: jest.fn(),
  currCategory: "",
  multiFilter: {},
  setMultiFilter: jest.fn(),
  onDelete: jest.fn(),
  onApplyFilter: jest.fn(),
};

const queryClient = setupReactQuery();
const store = configureStore({
  reducer: {
    mta: (state = { EnvConfig: undefined }) => state,
  },
});

const contextWrapper = (children: ReactNode) => (
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <Provider store={store}>
        <UserDataContext.Provider
          value={{
            user: { user: { theme_ui: "NOIRFUSION" } },
            changeColorTheme: (color: any) => color,
            isSideBarOpen: true,
            toggleSideBar: jest.fn(),
          }}
        >
          {children}
        </UserDataContext.Provider>
      </Provider>
    </BrowserRouter>
  </QueryClientProvider>
);

describe("SelectCategory", () => {
  beforeEach(() => jest.clearAllMocks());

  it("renders the latest MTA filter", async () => {
    render(contextWrapper(<SelectCategory {...dummyProps} />));

    expect(screen.getByText("19 Sep 2026")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Add Filter"));

    expect(await screen.findByText("Supply Chain Node")).toBeInTheDocument();
    expect(screen.getByText("Coverage Filter")).toBeInTheDocument();
    expect(screen.getByText("Historical Filter")).toBeInTheDocument();
    expect(screen.getByText("Horizon Filter")).toBeInTheDocument();
    expect(screen.getByText("Show All")).toBeInTheDocument();
  });

  it("handles category clicks", () => {
    render(contextWrapper(<SelectCategory {...dummyProps} />));

    fireEvent.click(screen.getAllByText("From Parent")[0]);
    fireEvent.click(screen.getAllByText("To Child")[0]);
    fireEvent.click(screen.getAllByText("Review")[0]);

    expect(dummyProps.onMonitorParentClick).toHaveBeenCalled();
    expect(dummyProps.onMonitorChildClick).toHaveBeenCalled();
    expect(dummyProps.onExcessInventoryReviewClick).toHaveBeenCalled();
  });
});
