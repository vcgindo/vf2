import { ColDef } from "ag-grid-enterprise";

export const colDefForPie: ColDef[] = [
    {
      field: "color",
      headerName: "Color",
      colId: "color",
    },
    {
      field: "pre",
      headerName: "Availability Pre Rationing",
      colId: "pre",
      filter:"agNumberColumnFilter"

    },
    {
      field: "post",
      headerName: "Availability Post Rationing",
      colId: "post",
      filter:"agNumberColumnFilter"

    },
  ];