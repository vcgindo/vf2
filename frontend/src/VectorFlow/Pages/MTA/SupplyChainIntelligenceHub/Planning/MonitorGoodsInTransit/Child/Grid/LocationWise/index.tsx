import {useState,useMemo, useContext, useEffect} from 'react';
import GridViewTable from "../../../../GridView/GridViewTable";
import { BPRTagsCellRenderer } from "../../../../../BPR/BPRCellRenderers";
import { AgGridReactProps } from "ag-grid-react";
import { VFPaginationProps } from "../../../../../../../../../components/VectorFLOW/commons/VFPagination";
import { SideBarDef } from 'ag-grid-enterprise';
import { getColumnDefinationsMTA } from '../../../../../../../../../helpers/utils';
import BPRGraphCellRenderer from '../../../../../BPR/BPRGraphCellRenderer';
import ColorCellRenderer from '../../../../../../InsightsAndTrends/BTR/ColorCellRenderer';
import { AgeingCellRenderer } from '../../../../../../../../../components/VectorFLOW/commons/AgeingCellRenderer';
import { MainMenuItemsCustomization } from '../../../../../../../../../helpers/utils'
import { GridStateContext } from '../../../../../../../../../context/GridStateContext';

const MonitorGITChildLocationWiseGrid = ({data,paginationProps,onOpenDailyDataGraph,currentCategory,currentTab}:{data:any,paginationProps:VFPaginationProps,onOpenDailyDataGraph:any,currentCategory:string,currentTab:string})=>{

    const [activeRow,setActiveRow] = useState<any>();
    const [isSubGridOpen,toggleSubGrid] = useState<any>(true);

    const [colDefs, setColDefs] = useState<any>([]);
    const {gridColDefs, setGlobalColDef} = useContext(GridStateContext);
    
    const customCellRenderers = useMemo(() => ({
        grapCellRenderer:BPRGraphCellRenderer,
        tagsCellRenderer:BPRTagsCellRenderer,
        colorCellRenderer:ColorCellRenderer,
        ageingCellRenderer:AgeingCellRenderer
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
        getMainMenuItems: MainMenuItemsCustomization,
        onRowClicked:(params:any)=>{
            if(params.data.transit && params.data.transit.length>0){
                setActiveRow(params.data.transit)
                toggleSubGrid(true)
            }
        },
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

    const customGridColDef = [
        {
            headerName:"Order No/Tracking No",
            colId:'lc',
            field:'lc'
        },
        // {
        //     headerName:"Creation Date",
        //     colId:'cd',
        //     field:'cd'
        // },
        // {
        //     headerName:"SLT",
        //     colId:'slt',
        //     field:'slt'
        // },
        // {
        //     headerName:"TLT",
        //     colId:'tlt',
        //     field:'tlt'
        // },
        {
            headerName:"Ageing",
            colId:'ag',
            field:'ag'
        },
        // {
        //     headerName:"ETA",
        //     colId:'eta',
        //     field:'eta'
        // },
        // {
        //     headerName:"Current Location",
        //     colId:'cl',
        //     field:'cl'
        // },
        {
            headerName:"Quantity",
            colId:'qty',
            field:'qty'
        },
        // {
        //     headerName:"Remarks",
        //     colId:'remarks',
        //     field:'remarks'
        // },
        {
            headerName:"Whereabouts",
            colId:'whereabouts',
            field:'whereabouts'
        }
    ]

    // const mapUIConfigToColdefs = (columns:Array<{header:string,colCode:string,colPosition:number}>) => {
    //     let colDefs = [];
    //     const dailyDataColDef = {...createIconColumn({id:'dailydatagraph',label:'',cellRenderer:'grapCellRenderer'}),cellRendererParams:{onOpenDailyDataGraph:onOpenDailyDataGraph}}
    //     const tagsColDef =  {
    //         colId:'tags',
    //         field:'t',
    //         headerName:"Tags",
    //         cellRenderer:'tagsCellRenderer',
    //         width:100,
    //     }
    //     const ageingColDef =  {
    //         colId:'AgeingOrder',
    //         field:'AgeingOrder',
    //         headerName:"",
    //         cellRenderer:'ageingCellRenderer',
    //         width:100,
    //         floatingFilter:false
    //     }
    //     columns.sort((column1:{header:string,colCode:string,colPosition:number},column2:{header:string,colCode:string,colPosition:number})=>{
    //         return column1.colPosition - column2.colPosition;
    //     })
    //     colDefs = columns.map((column:{header:string,colCode:string})=>{
    //         if(['plp','pip'].includes(column.colCode)){
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

    //         if(customColdef) return customColdef
            
    //         return {
    //             field:column['colCode'],
    //             colId:column['colCode'],
    //             headerName:column['header']
    //         }
    //     })
    //     // dispatch(UPDATE_GRID_STATE([ageingColDef,dailyDataColDef,...colDefs]))
    //     return [ageingColDef,dailyDataColDef,...colDefs]
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
        },
        plp:{
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
            customGridRowData={activeRow} 
            customGridColDef={customGridColDef} 
            isSubGridOpen={isSubGridOpen}
            paginationProps={paginationProps}
            gridHeight={"95%"}
            
        />
    )
}

export default MonitorGITChildLocationWiseGrid