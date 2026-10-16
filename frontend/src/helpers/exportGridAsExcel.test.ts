import { exportGridAsExcel } from "./exportGridAsExcel";

describe("exportGridAsExcel", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: jest.fn(() => "blob:guided-export"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: jest.fn(),
    });
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  it("downloads AG Grid's XLSX blob during the click task", () => {
    const contents = new Blob(["xlsx"]);
    const api = { getDataAsExcel: jest.fn(() => contents) };
    const click = jest
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);

    expect(exportGridAsExcel(api, "ChronicUnavailabilityexport.xlsx")).toBe(
      true
    );
    expect(api.getDataAsExcel).toHaveBeenCalledWith({
      fileName: "ChronicUnavailabilityexport.xlsx",
    });
    expect(URL.createObjectURL).toHaveBeenCalledWith(contents);
    expect(click).toHaveBeenCalledTimes(1);
    expect(URL.revokeObjectURL).not.toHaveBeenCalled();

    jest.advanceTimersByTime(1_000);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:guided-export");
    expect(document.querySelector('a[download="ChronicUnavailabilityexport.xlsx"]')).toBeNull();
  });

  it("does not start a download when AG Grid cannot create the workbook", () => {
    const api = { getDataAsExcel: jest.fn(() => undefined) };
    const click = jest.spyOn(HTMLAnchorElement.prototype, "click");

    expect(exportGridAsExcel(api, "empty")).toBe(false);
    expect(click).not.toHaveBeenCalled();
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });
});
