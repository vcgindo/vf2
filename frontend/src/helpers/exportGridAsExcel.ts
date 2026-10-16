import type { ExcelExportParams, GridApi } from "ag-grid-enterprise";

type ExcelGridApi = Pick<GridApi, "getDataAsExcel">;

const XLSX_MIME_TYPE =
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

export const exportGridAsExcel = (
  api: ExcelGridApi,
  fileName: string,
  params: Omit<ExcelExportParams, "fileName"> = {}
): boolean => {
  const contents = api.getDataAsExcel({ ...params, fileName });
  if (contents === undefined) return false;

  const blob =
    contents instanceof Blob
      ? contents
      : new Blob([contents], { type: XLSX_MIME_TYPE });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = fileName.endsWith(".xlsx") ? fileName : `${fileName}.xlsx`;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
  return true;
};
