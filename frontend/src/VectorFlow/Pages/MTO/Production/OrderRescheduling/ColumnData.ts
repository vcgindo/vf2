import { ColDef } from "ag-grid-enterprise"
const columnData: ColDef[] = [
    {
        colId: "oid",
        field: "oid",
        headerName: "Order Id",
        hide: false,
        cellStyle: { display: 'flex' },
        tooltipComponent: "availabilityToolTip",
        initialWidth: 800,
        autoHeaderHeight: true,
    },
    {
        colId: "lid",
        field: "lid",
        headerName: "Line Item",
        cellStyle: { display: 'flex', justifyContent: 'right' },
        hide: false,
        tooltipComponent: "availabilityToolTip",
        initialWidth: 150,
        width: 150,
        maxWidth: 150,
        autoHeaderHeight: true,
        wrapHeaderText: true
    },
    {
        colId: "PcSz",
        field: "PcSz",
        cellStyle: { display: 'flex', justifyContent: 'right' },
        headerName: "Procurement Buffer",
        hide: false,
        tooltipField: "rm",
        initialWidth: 180,
        width: 180,
        maxWidth: 180,
        filter: "agMultiColumnFilter",
        floatingFilter: true
    },
    {
        colId: "PdSz",
        field: "PdSz",
        cellStyle: { display: 'flex', justifyContent: 'right' },
        headerName: "Production Buffer",
        hide: false,
        autoHeaderHeight: true,
        wrapHeaderText: true,
        initialWidth: 200,
        filter: "agMultiColumnFilter",
        floatingFilter: true
    },
    {
        colId: "rnm",
        field: "rnm",
        cellStyle: { display: 'flex' },
        headerName: "Route",
        hide: false,
        autoHeaderHeight: true,
        wrapHeaderText: true,
        initialWidth: 200,
        filter: "agMultiColumnFilter",
        floatingFilter: true
    }
]

export default columnData