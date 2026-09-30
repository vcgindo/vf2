import { ColDef } from "ag-grid-enterprise"
import AvlCellRenderer from "../../../Common/AvlCellRenderer/AvlCellRenderer"
import BPPRenderer from "../../../Common/BPRRenderer/BPPRenderer"
const columnData: ColDef[] = [
    {
        colId: "bpp",
        field: "bpp",
        headerName: "BPP",
        hide: false,
        cellRenderer: BPPRenderer,
        tooltipComponent: "availabilityToolTip",
        initialWidth: 100,
        autoHeaderHeight: true,
        wrapHeaderText: true,
        filter: "agMultiColumnFilter",
        floatingFilter: true,

    },
    {
        colId: "pnm",
        field: "pnm",
        headerName: "Plant",
        hide: false,
        cellRenderer: "coloPriority",
        tooltipComponent: "availabilityToolTip",
        initialWidth: 200,
        autoHeaderHeight: true,
        filter: "agMultiColumnFilter",
        wrapHeaderText: true,
        floatingFilter: true,
        cellStyle: {
            display: 'flex',
            justifyContent: 'left',
        }
    },
    {
        colId: "oid",
        field: "oid",
        headerName: "Order ID",
        hide: false,
        cellStyle: {
            display: 'flex',
            justifyContent: 'left',
        },
        tooltipField: "rm",
        initialWidth: 200,
        filter: "agMultiColumnFilter",
        floatingFilter: true
    },
    {
        colId: "lid",
        field: "lid",
        headerName: "Line Item ID",
        hide: false,

        autoHeaderHeight: true,
        wrapHeaderText: true,
        initialWidth: 200,
        filter: "agMultiColumnFilter",
        floatingFilter: true,
        cellStyle: {
            display: 'flex',
            justifyContent: 'left',
        }
    },
    {
        colId: "ic",
        field: "ic",
        headerName: "Item Code",
        hide: false,

        autoHeaderHeight: true,
        wrapHeaderText: true,
        initialWidth: 200,
        filter: "agMultiColumnFilter",
        floatingFilter: true,
        cellStyle: {
            display: 'flex',
            justifyContent: 'left',
        }
    },
    {
        colId: "id",
        field: "id",
        headerName: "Item Description",
        hide: false,

        autoHeaderHeight: true,
        wrapHeaderText: true,
        initialWidth: 200,
        filter: "agMultiColumnFilter",
        floatingFilter: true,
        cellStyle: {
            display: 'flex',
            justifyContent: 'left',
        }
    },
    {
        colId: "dd",
        field: "dd",
        headerName: "Due Date",
        hide: false,

        autoHeaderHeight: true,
        wrapHeaderText: true,
        initialWidth: 200,
        filter: "agMultiColumnFilter",
        floatingFilter: true,
        cellStyle: {
            display: 'flex',
            justifyContent: 'center',
        }
    },
    {
        colId: "rd",
        field: "rd",
        headerName: "Release Date",
        hide: false,

        autoHeaderHeight: true,
        wrapHeaderText: true,
        initialWidth: 200,
        filter: "agMultiColumnFilter",
        floatingFilter: true
    },
    {
        colId: "oq",
        field: "oq",
        headerName: "Order Quantity",
        hide: false,

        autoHeaderHeight: true,
        wrapHeaderText: true,
        initialWidth: 200,
        filter: "agMultiColumnFilter",
        floatingFilter: true,
        cellStyle: {
            display: 'flex',
            justifyContent: 'right',
        }
    },
    {
        colId: "bs",
        field: "bs",
        headerName: "Batch Size",
        hide: false,
        autoHeaderHeight: true,
        wrapHeaderText: true,
        initialWidth: 200,
        filter: "agMultiColumnFilter",
        floatingFilter: true,
        cellStyle: {
            display: 'flex',
            justifyContent: 'right',
        }
    },
    {
        colId: "fk",
        field: "fk",
        headerName: "Full Kit Available",
        hide: false,
        cellRenderer: AvlCellRenderer,
        autoHeaderHeight: true,
        wrapHeaderText: true,
        initialWidth: 200,
        filter: "agMultiColumnFilter",
        floatingFilter: true

    },
    {
        colId: "rmpm",
        field: "rmpm",
        headerName: "RM / PM Coverage",
        hide: false,
        autoHeaderHeight: true,
        wrapHeaderText: true,
        initialWidth: 400,
        filter: "agMultiColumnFilter",
        floatingFilter: true,
    },
    {
        colId: "cc",
        field: "cc",
        headerName: "Customer Code",
        hide: false,

        autoHeaderHeight: true,
        wrapHeaderText: true,
        initialWidth: 200,
        filter: "agMultiColumnFilter",
        floatingFilter: true
    },
    {
        colId: "cn",
        field: "cn",
        headerName: "Customer Name",
        hide: false,

        autoHeaderHeight: true,
        wrapHeaderText: true,
        initialWidth: 200,
        filter: "agMultiColumnFilter",
        floatingFilter: true
    }
]

export default columnData