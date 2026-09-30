import {useState,useMemo}from 'react';
import GridViewTable from "../../../GridView/GridViewTable";
import { BPRTagsCellRenderer } from "../../../../BPR/BPRCellRenderers";
import { AgGridReactProps } from "ag-grid-react";
import { VFPaginationProps } from "../../../../../../../../components/VectorFLOW/commons/VFPagination";
import { SideBarDef } from 'ag-grid-enterprise';
import { createIconColumn,getProductAndLocationHeirarchiesFromEnv } from '../../../../../../../../helpers/utils';
import BPRGraphCellRenderer from '../../../../BPR/BPRGraphCellRenderer';
import ColorCellRenderer from '../../../../../InsightsAndTrends/BTR/ColorCellRenderer';
import RequestExpeditingModal from '../../../../BPR/RequestExpeditingModal';
import { useSubmitOpenExpediteRequest } from '../../../../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/Planning';
import { notifyError, notifyLoader, notifySuccess } from '../../../../../../../../helpers/notify';
import { toast } from 'react-toastify';

const ExpediteChildGrid = ({data,paginationProps,onOpenDailyDataGraph,currentCategory,currentTab}:{data:any,paginationProps:VFPaginationProps,onOpenDailyDataGraph:any,currentCategory:string,currentTab:string})=>{

    const [isExpeditingModalOpen,toggleExpeditingModal] =  useState<boolean>(false)
    const [currentRowData,setCurrentRowData] = useState<any>();
    const [activeRow,setActiveRow] = useState<any>();
    const [isSubGridOpen,toggleSubGrid] = useState<any>(true);
    const {mutateAsync:submitRemark} = useSubmitOpenExpediteRequest()
    const submitOpenExpediteRemark = async(remark:string)=>{
        if(remark.length===0){
            notifyError('Message cannot be empty')
            return
        }
        notifyLoader('Submiting request')
        try{
            const tempEta = currentRowData.eta.replaceAll("-","/").substring(0,10)
            await submitRemark({
                data:[
                    {
                        "wc":"GE04",
                        "eta":tempEta,
                        "Request":remark,
                        "pwc":"",
                        "sc": currentRowData.sc                    
                       
                       
                      }
                ]
            })
        toast.dismiss()
        notifySuccess('Request Submitted sucessfully')
        }catch(err:any){
            notifyError(err)
        }finally{
            toggleExpeditingModal(false)
        }
    }

    const customCellRenderers = useMemo(() => ({
        grapCellRenderer:BPRGraphCellRenderer,
        tagsCellRenderer:BPRTagsCellRenderer,
        colorCellRenderer:ColorCellRenderer
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
        onRowClicked:(params:any)=>{
            if(params.data.intransit && params.data.intransit.length>0){
                setCurrentRowData(params.data)
                setActiveRow(params.data.intransit)
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
                " font-size":"20px",
                " font-family":"Roboto",
                "display":"block",
                'text-overflow':'ellipsis',
                'white-space':'nowrap'
            },
        }
    }

    const mapUIConfigToColdefs = (columns:Array<{header:string,colCode:string,colPosition:number}>) => {
        let colDefs = [];
        const dailyDataColDef = {...createIconColumn({id:'graph',label:'',cellRenderer:'grapCellRenderer'}),cellRendererParams:{onOpenDailyDataGraph:onOpenDailyDataGraph}}
        columns.sort((column1:{header:string,colCode:string,colPosition:number},column2:{header:string,colCode:string,colPosition:number})=>{
            return column1.colPosition - column2.colPosition;
        })
        const tagsColDef =  {
            colId:'tags',
            field:'t',
            headerName:"Tags",
            cellRenderer:'tagsCellRenderer',
            width:100,
        }
        colDefs = columns.map((column:{header:string,colCode:string})=>{
            if(['plp','pip','pin'].includes(column.colCode)){
                return {
                    field:column['colCode'],
                    colId:column['colCode'],
                    headerName:column['header'],
                    cellRenderer:'colorCellRenderer',
                }
            }
            if(column.colCode === 't'){
                return tagsColDef
            }

            const customColdef = getProductAndLocationHeirarchiesFromEnv(column,{}); 
            if(customColdef) return customColdef;
            return {
                field:column['colCode'],
                colId:column['colCode'],
                headerName:column['header']
            }
        })
        return [dailyDataColDef,...colDefs]
    }

    const colDefs = mapUIConfigToColdefs(data['uiConfig'])

    // if(isLoading){
    //   return (
    //     <VFLoader/>
    //   )
    // }

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
        {
            headerName:"Whereabouts",
            colId:'whereabouts',
            field:'whereabouts'
        }
        // {
        //     headerName:"Remarks",
        //     colId:'remarks',
        //     field:'remarks'
        // }
    ]

    return(
        <>
            <GridViewTable 
                currentCategory={currentCategory}
                currentTab={currentTab}
                agGridProps={agGridProps} 
                agGridColDefs={colDefs} 
                agGridRowData={data['data']} 
                customGridRowData={activeRow} 
                customGridColDef={customGridColDef} 
                showStockGrid 
                stockGridData={currentRowData?[{...currentRowData}]:[]} 
                isSubGridOpen={isSubGridOpen} 
                onRequestExpediting={()=>toggleExpeditingModal(true)}
                paginationProps={paginationProps}
                gridHeight={"95%"}
            />
            <RequestExpeditingModal isOpen={isExpeditingModalOpen} onClose={()=>toggleExpeditingModal((prev:boolean)=>!prev)} onSubmit={submitOpenExpediteRemark}/>
        </>
    )
}

export default ExpediteChildGrid