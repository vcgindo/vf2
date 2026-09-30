import {useContext, useEffect, useMemo, useState} from 'react';
import GridViewTable from "../../GridView/GridViewTable";
import { BPRTagsCellRenderer } from "../../../BPR/BPRCellRenderers";
import { AgGridReactProps } from "ag-grid-react";
import {  getColumnDefinationsMTA, MainMenuItemsCustomization } from '../../../../../../../helpers/utils';
import BPRGraphCellRenderer from '../../../BPR/BPRGraphCellRenderer';
import ColorCellRenderer from '../../../../InsightsAndTrends/BTR/ColorCellRenderer';
import { OrderCoverageCellRenderer } from '../../../../../../../components/VectorFLOW/commons/OrderCoverageCellRenderer';
import { BPRViewTableColDef } from '../../../BPR/BPRViewTable';
import { defaultAgGridSideBarForBPR } from '../../../../../../../helpers/BPRConstants';
import { GridStateContext } from '../../../../../../../context/GridStateContext';

const OrderFulfillmentGrid = ({data, paginationProps, onOpenDailyDataGraph, currentCategory, currentTab}:any) => {

    const [activeRow, setActiveRow] = useState<any>();
    const [isSubGridOpen, toggleSubGrid] = useState<any>(true);

    const [colDefs, setColDefs] = useState<any>([]);
    const {gridColDefs, setGlobalColDef} = useContext(GridStateContext);

    const customCellRenderers = useMemo(() => ({
        grapCellRenderer: BPRGraphCellRenderer,
        tagsCellRenderer: BPRTagsCellRenderer,
        colorCellRenderer: ColorCellRenderer,
        orderCoverageCellRenderer: OrderCoverageCellRenderer
    }), []);


    const agGridProps: AgGridReactProps = {
        enableRangeSelection: true,
        rowSelection: "multiple",
        suppressRowTransform: true,
        tooltipShowDelay: 0.3,
        tooltipTrigger: 'focus',
        tooltipInteraction: true,
        readOnlyEdit: true,
        getMainMenuItems: MainMenuItemsCustomization,
        gridOptions: {
            rowHeight: 50,
            getRowStyle: (params: any) => {
                if (params.node.rowIndex % 2 === 0) {
                    return { background: "#EBEBEB" };
                }
                return { background: "#F7F7F7" };
            },
        },
        onRowClicked: (params: any) => {
            if (params.data.transit && params.data.transit.length > 0) {
                setActiveRow(params.data.transit);
                toggleSubGrid(true);
            }else{
                setActiveRow(null)
            }
        },
        sideBar: defaultAgGridSideBarForBPR,
        suppressRowClickSelection: true,
        components: customCellRenderers,
        defaultColDef: {
            floatingFilter: true,
            filter: "agMultiColumnFilter",
            cellDataType: false,
            resizable: true,
            cellStyle: {
                "flex": 1,
                'text-align': 'center',
                'height': '50px',
                "font-style": "normal",
                "font-variant": "normal",
                "font-weight": "300",
                "font-family": "Roboto",
                "display": "block",
                'text-overflow': 'ellipsis',
                'white-space': 'nowrap'
            },
        },
        statusBar: {
            statusPanels: [
                { statusPanel: 'agTotalAndFilteredRowCountComponent', align: 'left' },
                { statusPanel: 'agTotalRowCountComponent', align: 'left' },
                { statusPanel: 'agFilteredRowCountComponent', align: 'left' },
                { statusPanel: 'agSelectedRowCountComponent', align: 'left' },
                { statusPanel: 'agAggregationComponent', align: 'left' },
            ],
        }
    }

    // const mapUIConfigToColdefs = (columns:any) => {
    //     let colDefs = [];
    //     columns.sort((column1:any, column2:any) => {
    //         return column1.colPosition - column2.colPosition;
    //     });
    //     const dailyDataColDef = {...createIconColumn({id:'graph', label:'', cellRenderer:'grapCellRenderer'}), cellRendererParams: {onOpenDailyDataGraph: onOpenDailyDataGraph}};
    //     // const tagsColDef = {
    //     //     colId: 'tags',
    //     //     field: 'tags',
    //     //     headerName: "Tags",
    //     //     cellRenderer: 'tagsCellRenderer',
    //     //     width: 100
    //     // };

    //     colDefs = columns.map((column:any) => {
    //         if (['plp', 'pip'].includes(column.colCode)) {
    //             return {
    //                 field: column['colCode'],
    //                 colId: column['colCode'],
    //                 headerName: column['header'],
    //                 cellRenderer: 'colorCellRenderer',
    //             }
    //         }
    //         if (column.colCode === 'c') {
    //             return {
    //                 field: column['colCode'],
    //                 colId: column['colCode'],
    //                 headerName: column['header'],
    //                 cellRenderer: 'orderCoverageCellRenderer',
    //                 minWidth: 250,
    //             }
    //         }
    //         if(column.colCode==='t'){
    //             return {
    //                 field: column['colCode'],
    //                 colId: column['colCode'],
    //                 headerName: column['header'],
    //                 cellRenderer: 'tagsCellRenderer',
    //                 width: 100
    //             }
    //         }
    //         const customColdef = getProductAndLocationHeirarchiesFromEnv(column,{}); 
    //         if(customColdef) return customColdef;
    //         return {
    //             field: column['colCode'],
    //             colId: column['colCode'],
    //             headerName: column['header'],
    //         }
    //     });
    //     return [dailyDataColDef, ...colDefs];
    // }

    const CustomHeader = {
        dailydatagraph: {
            width: 45,
            minWidth: 45,
            filter: false,
            cellRenderer: 'grapCellRenderer',
            cellRendererParams: { onOpenDailyDataGraph: onOpenDailyDataGraph },
            pinned: 'left',
            resizable: false,
            floatingFilter: false,
            suppressColumnsToolPanel: false,
            headerTooltip: "Daily Data Graph",
            sortable:false,
            suppressMenu:true,
            headerName:"Daily Data Graph",
        },
        t: {
            cellRenderer: 'tagsCellRenderer',
            width: 100,
            minWidth: 100,
            filter: true,
            pinned: null,
            filterParams: {
                buttons: ['reset'], // Adds Apply and Clear buttons
            },
        },
        c:{
            cellRenderer: 'orderCoverageCellRenderer',
        },
        pin:{
            cellRenderer:'colorCellRenderer',
        },
        pip:{
            cellRenderer: "colorCellRenderer"
        },
        plp:{
            cellRenderer: "colorCellRenderer"
        }
    }

    // const colDefs = mapUIConfigToColdefs(data['uiConfig']);
    useEffect(()=>{
        if(gridColDefs!==null){
            const cols =  getColumnDefinationsMTA(gridColDefs,CustomHeader)
            setColDefs(cols);
            setGlobalColDef(cols);
        } 
    },[gridColDefs])

    const customGridColDef:Array<BPRViewTableColDef> = [
        {
            headerName: "Order No/Tracking No",
            colId: 'on',
            field: 'on',
            filter:true,
            dataType:'number'
        },
        {
            headerName: "Creation Date",
            colId: 'id',
            field: 'id',
            filter:true
        },
        {
            headerName: "Pending Quantity",
            colId: 'pq',
            field: 'pq',
            dataType:"number",
            filter:true
        },
        {
            headerName: "Due Date",
            colId: 'dd',
            field: 'dd',
            filter:true
        },
        {
            headerName: "Price",
            colId: 'p',
            field: 'p',
            dataType:"number",
            filter:true
        },
        {
            headerName: "Order Status",
            colId: 'os',
            field: 'os',
            filter:true
        },
    ]

    return (
        <GridViewTable
            currentTab={currentTab}
            currentCategory={currentCategory}
            agGridProps={agGridProps}
            agGridColDefs={colDefs}
            agGridRowData={data['data']}
            customGridRowData={activeRow}
            customGridColDef={customGridColDef}
            isSubGridOpen={isSubGridOpen}
            paginationProps={paginationProps}
            tablePrefixSrc={'/assets/img/VectorFLOW/BPR/order-fullfilment-table-prefix.svg'}
            tableHeader="Order Details"
            gridHeight={"95%"}
        />
    )
}

export default OrderFulfillmentGrid;
