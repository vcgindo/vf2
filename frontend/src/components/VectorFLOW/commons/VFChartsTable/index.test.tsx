import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { exportGridAsExcel } from "../../../../helpers/exportGridAsExcel";
import VFChartsTable from ".";

var mockMountedApi: any;

jest.mock("../../../../helpers/exportGridAsExcel", () => ({
  exportGridAsExcel: jest.fn(),
}));

jest.mock("../../../../context", () => ({
  useUserData: () => ({ user: { user: { theme_ui: "NOIRFUSION" } } }),
}));

jest.mock("../VFModalCard", () => ({ children }: any) => <>{children}</>);

jest.mock("../VFButtonOutline", () => ({ children, onClick }: any) => (
  <button onClick={onClick}>{children}</button>
));

jest.mock("../../../../VectorFlow/Pages/MTO/Common/VFTable", () => {
  const React = require("react");
  mockMountedApi = {
    getDataAsExcel: jest.fn(() => new Blob(["xlsx"])),
    exportDataAsExcel: jest.fn(),
  };
  return React.forwardRef((_props: any, ref: any) => {
    React.useImperativeHandle(ref, () => ({ api: mockMountedApi }));
    return <div data-testid="grid" />;
  });
});

const renderTable = (useSynchronousExcelExport = false) => {
  const gridRef = React.createRef<any>();
  render(
    <VFChartsTable
      title="Locations"
      hideChart
      gridRef={gridRef}
      colDefs={[]}
      rowData={[]}
      setHideChart={jest.fn()}
      downloadName="DBM Location"
      useSynchronousExcelExport={useSynchronousExcelExport}
    />
  );
  fireEvent.click(screen.getByRole("button", { name: /Excel Export/i }));
};

describe("VFChartsTable Excel export", () => {
  beforeEach(() => jest.clearAllMocks());

  it("passes the mounted AG Grid API to the Guided synchronous export", () => {
    renderTable(true);

    expect(exportGridAsExcel).toHaveBeenCalledWith(
      mockMountedApi,
      "DBM_Location.xlsx"
    );
    expect(mockMountedApi.exportDataAsExcel).not.toHaveBeenCalled();
  });

  it("retains AG Grid's default export for callers without the opt-in", () => {
    renderTable();

    expect(exportGridAsExcel).not.toHaveBeenCalled();
    expect(mockMountedApi.exportDataAsExcel).toHaveBeenCalledWith({
      fileName: "DBM_Location.xlsx",
    });
  });
});
