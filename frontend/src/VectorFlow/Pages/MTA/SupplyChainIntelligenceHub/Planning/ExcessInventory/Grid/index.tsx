import {useContext, useEffect, useMemo, useState} from 'react';
import GridViewTable from "../../GridView/GridViewTable";
import { BPRTagsCellRenderer } from "../../../BPR/BPRCellRenderers";
import { AgGridReactProps } from "ag-grid-react";
import { VFPaginationProps } from "../../../../../../../components/VectorFLOW/commons/VFPagination";
import { SideBarDef } from 'ag-grid-enterprise';
import {  getColumnDefinationsMTA } from '../../../../../../../helpers/utils';
import BPRGraphCellRenderer from '../../../BPR/BPRGraphCellRenderer';
import ColorCellRenderer from '../../../../InsightsAndTrends/BTR/ColorCellRenderer';
import { GridStateContext } from '../../../../../../../context/GridStateContext';

const ExcessInventoryGrid = ({data,paginationProps,onOpenDailyDataGraph,currentCategory,currentTab}:{data:any,paginationProps:VFPaginationProps,onOpenDailyDataGraph:any,currentCategory:string,currentTab:string})=>{

    const [colDefs, setColDefs] = useState<any>([]);
    const {gridColDefs, setGlobalColDef} = useContext(GridStateContext);

    const customCellRenderers = useMemo(() => ({
        grapCellRenderer:BPRGraphCellRenderer,
        tagsCellRenderer:BPRTagsCellRenderer,
        colorCellRenderer:ColorCellRenderer,
      }), []);

      const sideBar:SideBarDef = {
        toolPanels: [
          {
            id: "columns",
            labelDefault: "Columns",
            labelKey: "columns",
            iconKey: "columns",
            toolPanel: "agColumnsToolPanel",
            toolPanelParams: {
                suppressPivots: true,
                suppressPivotMode: true,
                suppressRowGroups: true,
                suppressValues: true,
              },
          },
        ],
        defaultToolPanel:'',
      }

    const agGridProps:AgGridReactProps = {
        
        suppressRowTransform:true,
        tooltipShowDelay:0.3,
        tooltipTrigger:'focus',
        tooltipInteraction:true,
        // rowSelection:'single',
        readOnlyEdit:true,
        enableRangeSelection: true,
        rowSelection: "multiple",
        statusBar: {
          statusPanels: [
            { statusPanel: 'agTotalAndFilteredRowCountComponent', align: 'left' },
            { statusPanel: 'agTotalRowCountComponent', align: 'left' },
            { statusPanel: 'agFilteredRowCountComponent', align: 'left' },
            { statusPanel: 'agSelectedRowCountComponent', align: 'left' },
            { statusPanel: 'agAggregationComponent', align: 'left' },
          ],
        },
        gridOptions:{
            rowHeight:50,
            getRowStyle: (params: any) => {
            if (params.node.rowIndex % 2 === 0) {
                return { background: "#EBEBEB" };
            }
            return { background: "#F7F7F7" };
            },
        },
        sideBar:sideBar,
        suppressRowClickSelection:true,
        components:customCellRenderers,
        defaultColDef:{
            floatingFilter: true,
            filter: "agMultiColumnFilter",
            cellDataType:false,
            resizable:true,
            cellStyle:{
                "flex":1,
                'text-align':'center',
                'height':'50px',
                "font-style":"normal",
                " font-variant":"normal",
                " font-weight":"300",
                " font-family":"Roboto",
                "display":"block",
                'text-overflow':'ellipsis',
                'white-space':'nowrap'
            },
        }
    }

    // replaced this method with new getColumnDefinationsMTA for code reuseablity
    // const mapUIConfigToColdefs = (columns:Array<{header:string,colCode:string,colPosition:number}>) => {
    //     let colDefs = [];
    //     const dailyDataColDef = generateDailyDataGraphCell(onOpenDailyDataGraph) 
    //     columns.sort((column1:{header:string,colCode:string,colPosition:number},column2:{header:string,colCode:string,colPosition:number})=>{
    //         return column1.colPosition - column2.colPosition;
    //     })
    //     const tagsColDef =  {
    //         colId:'t',
    //         field:'t',
    //         headerName:"Tags",
    //         cellRenderer:'tagsCellRenderer',
    //         width:100,
    //     }
    //     colDefs = columns.map((column:{header:string,colCode:string})=>{
    //         if(['plp','pip','pin'].includes(column.colCode)){
    //             return {
    //                 field:column['colCode'],
    //                 colId:column['colCode'],
    //                 headerName:column['header'],
    //                 cellRenderer:'colorCellRenderer',
    //             }
    //         }
    //         if(column.colCode === 't'){
    //             return tagsColDef
    //         }
    //         const customColdef = getProductAndLocationHeirarchiesFromEnv(column,{}); 
    //         if(customColdef) return customColdef;
    //         return {
    //             field:column['colCode'],
    //             colId:column['colCode'],
    //             headerName:column['header']
    //         }
    //     })
    //     return [dailyDataColDef,...colDefs]
    // }

    const CustomHeader = {
        dailydatagraph: {
            width: 45,
            minWidth: 45,
            filter: false,
            cellRenderer: 'grapCellRenderer',
            cellRendererParams: { onOpenDailyDataGraph },
            pinned: 'left',
            resizable: false,
            floatingFilter: false,
            suppressColumnsToolPanel: false,
            suppressMenu:true,
            headerTooltip: "Daily Data Graph",
            headerName:"Daily Data Graph",
            sortable: false,
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
        pin:{
            cellRenderer:'colorCellRenderer',
        },
        pip:{
            cellRenderer: "colorCellRenderer"
        }
    }

    // const colDefs = mapUIConfigToColdefs(data['uiConfig'])
    useEffect(()=>{
        if(gridColDefs!==null){
            const cols =  getColumnDefinationsMTA(gridColDefs,CustomHeader)
            setColDefs(cols);
            setGlobalColDef(cols);
        } 
    },[gridColDefs])

    return(
        <GridViewTable 
            currentCategory={currentCategory}
            currentTab={currentTab}
            agGridProps={agGridProps} 
            agGridColDefs={colDefs} 
            agGridRowData={data['data']} 
            customGridRowData={[]} 
            customGridColDef={[]} 
            isSubGridOpen={false}
            paginationProps={paginationProps}
            gridHeight={"80%"}        
        />
    )
}

export default ExcessInventoryGrid