import { ColDef } from "ag-grid-enterprise";
import _ from "lodash";
import { ColorsMTO } from "../VectorFlow/Pages/MTO/Common/Colors";

interface ApiResponseItem {
  cc: string;
  v: boolean;
  cp?: number;
  hd: string;
  cla: string;
  scc: string;
  ch?: ApiResponseItem[];
  pinned?: "left" | "right";
  dt?: string;
}


export interface GridOptions {
  bomActive?: boolean;
  orderClosingEnable?: boolean;
  canAddComments?: boolean;
  pinRemarkColumns?: boolean;
  onOpenRemarkHistory: (data: any) => void;
}

export const excelColorArr = ["Black", "Red", "White", "Green", "Yellow", "Blue"];

export const createDynamicColumnDefs = (
  apiResponse: ApiResponseItem[],
  options: GridOptions,
  user: any
): ColDef[] => {
  const modifiedResponse: ApiResponseItem[] = [];
  const cpMap: { [key: string]: number } = {};


  apiResponse.forEach((item) => {
    const modifiedItem = { ...item };

    if (!(item.cc in cpMap)) {
      cpMap[item.cc] = 3; // Start from 3 since 1 and 2 are taken by default objects
    }

    modifiedItem.cp = cpMap[item.cc]++;
    modifiedItem.hd = item.hd || item.cc;
    modifiedItem.cla = "Centre";
    modifiedItem.scc = item.scc;

    if (item.cc) {
      if (item.cc.includes("Dept") && modifiedItem.ch) {
        modifiedItem.ch = item.ch?.map((child) => {
          return { ...child, scc: `ddtl.${item.cc}.${child.scc}` };
        });
      }

      if (item.cc.includes("Default Attribute") && modifiedItem.ch && !options.canAddComments) {
        modifiedItem.ch = item.ch?.filter((child) => child.cc !== "Remark");
      }
    }

    modifiedResponse.push(modifiedItem);
  });

  const defaultOuterObject: ApiResponseItem = {
    cc: "chckbx",
    v: true,
    cp: 0,
    hd: " ",
    cla: "Centre",
    scc: "chckbx",
    pinned: "left",
  };
  modifiedResponse.unshift(defaultOuterObject);

    const defaultSecondObject: ApiResponseItem = {
      cc: "ic",
      cp: 1,
      hd: "",
      v: true,
      cla: "Centre",
      scc: "ic",
    };
    modifiedResponse.unshift(defaultSecondObject);

  const maxCp = Math.max(...modifiedResponse.map((item) => item.cp || 0));

  if (options.canAddComments) {
    const additionalObject: ApiResponseItem = {
      cc: "",
      cp: maxCp + 1,
      hd: " ",
      v: true,
      cla: "Centre",
      scc: "rmk",
      pinned: options.pinRemarkColumns ? "right" : undefined,
      ch: [],
    };
    modifiedResponse.push(additionalObject);
  }

  if (options.orderClosingEnable) {
    const short_complete_OrderColumn: ApiResponseItem = {
      cc: "",
      cp: maxCp + 2,
      hd: " ",
      v: true,
      cla: "Centre",
      scc: "",
      pinned: "right",
      ch: [
        {
          cc: "ct",
          cp: maxCp + 2,
          hd: "Order Close Action",
          v: true,
          cla: "Centre",
          scc: "ct",
          pinned: "right",
        },
      ],
    };
    modifiedResponse.push(short_complete_OrderColumn);
  }

  const mapChildren = (parent: string, children: ApiResponseItem[]): ColDef[] => {
    return children.map((child) => ({
      field: child.scc.trim(),
      headerName: child.hd,
      colId: `${parent}-${child.cc}`,
      initialHide: !child.v,
      suppressHeaderFilterButton: true,
      filter:
        child.dt === "number" || child.dt === "decimal"
          ? "agNumberColumnFilter"
          : child.dt === "date"
          ? "agDateColumnFilter"
          : "agMultiColumnFilter",
          pinned: 
          options.pinRemarkColumns && ['Remark', 'RemarkHistory', 'Remark History', 'LatestRemark'].includes(child.cc) 
            ? 'right' 
            : child.pinned,
      editable: (params: any): boolean => {
        if (!options.canAddComments) {
          return false;
        }
        return !_.isEmpty(params.data) && child.cc === "Remark";
      },    
      floatingFilter: child.cc !== "ec" && child.cc !== "ic",
      minWidth:
        child.cc === "ec" || child.cc === "ic" || child.scc === "bpp"
          ? 80
          : 150,
      cellRenderer:
        child.cc === "ec" && options.bomActive
          ? "agGroupCellRenderer"
          : child.cc === "ic"
          ? "AgeingCellRenderer"
          : child.cc === "BPP"
          ? "colorCellRenderer"
          : child.cc === "RemarkHistory" || child.cc === "Remark History"
          ? "RemarkHistoryRenderer"
          : child.cc === "ct"
          ? "DropDownCellRenderer"
          : undefined,
      cellRendererParams: child.hd.includes("Remark")
        ? {
            onClick: (data: string) => options.onOpenRemarkHistory(data),
          }
        : undefined,
      cellClassRules:
        child.cc === "BPP"
          ? excelColorArr.reduce(
              (acc, color) => ({
                ...acc,
                [color]: (params: any) =>
                  !_.isEmpty(params.data) && params.data?.cl === color,
              }),
              {}
            )
          : undefined,
      cellStyle: (params: any): any => {
        const style: any = {
          justifyContent: child.cla,
        };

        if (child.cc === "Remark" && options.canAddComments && !_.isEmpty(params.data)) {
          style.backgroundColor = "white";
          style.border = "1px solid #b9bdba";
          style.color = "black";
          style.padding = "1px";
        } else if (child.cc === "da") {
          style.color = ColorsMTO.Pink.code;
        } else {
          if (child.cla === "right") style.paddingRight = "3rem";
          if (child.cla === "left") style.paddingLeft = "1rem";
        }
        return style;
      },
      valueFormatter: (params: any) => {
        if (params.value != null) {
          const format = (user?.config_data?.NUMBER_FORMAT || "USA").toUpperCase();
          const locale =
            format === "USA" ? "en-US" : format === "IND" ? "hi-IN" : undefined;

          if (child.dt === "number") {
            return locale
              ? params.value.toLocaleString(locale)
              : params.value;
          }
          if (child.dt === "decimal") {
            const fixedValue = parseFloat(params.value.toFixed(2));
            return locale
              ? fixedValue.toLocaleString(locale, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })
              : fixedValue;
          }
        }
        return params.value;
      },
      filterParams: {
        buttons: ['reset'],
        comparator: (filterLocalDateAtMidnight: Date, cellValue: any) => {
          if (!cellValue) return -1;
          const cellDate = new Date(cellValue);
          if (isNaN(cellDate.getTime())) return -1;
          const cellDateOnly = new Date(
            cellDate.getFullYear(),
            cellDate.getMonth(),
            cellDate.getDate()
          );
          if (cellDateOnly < filterLocalDateAtMidnight) return -1;
          if (cellDateOnly > filterLocalDateAtMidnight) return 1;
          return 0;
        }
      },
    }));
  };

  const finalColDefs: ColDef[] = modifiedResponse.map((section) => ({
    headerName: section.hd !== undefined && section.hd !== null ? section.hd : section.cc,
    colId: section.cc,
    pinned: section.pinned,
    headerComponent:
      section.scc === "chckbx" && !options.orderClosingEnable
        ? "customHeaderCheckbox"
        : undefined,
    checkboxSelection:
      section.scc === "chckbx"
        ? (params: any) => params.node && !params.node.group
        : undefined,
    suppressMenu: section.scc === "chckbx" || section.cc === "ic",
    suppressHeaderFilterButton: section.scc === "chckbx" || section.cc === "ic",
    sortable: section.scc !== "chckbx" && section.cc !== "ic",
    maxWidth:
      section.scc === "chckbx" || section.cc === "ic" ? 60 : undefined,
    floatingFilter: section.scc !== "chckbx" && section.cc !== "ic",
    children: section.ch ? mapChildren(section.cc, section.ch) : undefined,
    cellRenderer:
      (section.cc === "ec" || section.scc === "chckbx") && options.bomActive
        ? "agGroupCellRenderer"
        : section.cc === "ic"
        ? "AgeingCellRenderer"
        : undefined,
  }));

  return finalColDefs;
};