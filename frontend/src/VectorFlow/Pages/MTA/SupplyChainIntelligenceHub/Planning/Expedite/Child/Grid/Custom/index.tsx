import {useEffect, useContext, useState } from "react";
import { validateCustomRows } from '../../../../OrderFulfillment/Grid/Custom/validateRows';

// import "./styles.css";
import VFTable from "../../../../../../../../../components/VectorFLOW/commons/VFTable";
// import _ from "lodash";
import '../../../styles.css';
import { useGetPlanningDataCustom } from "../../../../../../../../Services/MTA/SupplyChainIntelligenceHub/Planning";
import VFLoader from "../../../../../../../../../components/VectorFLOW/commons/VFLoader";
import { SCDynamicContainer } from "../../../styles";
import { notifyLoader,notifyError,notifySuccess } from "../../../../../../../../../helpers/notify";
import { toast } from 'react-toastify';
import { useGetState } from "../../../../../../../../Services/MTA/SupplyChainIntelligenceHub/BPR";
import { GridStateContext } from "../../../../../../../../../context/GridStateContext";
import { GridState } from "../../../../../../../../types/BPR";
import { getColumnDefinationsMTA, getProductAndLocationHeirarchiesFromEnv } from '../../../../../../../../../helpers/utils';
import { UIColumnConfigName, UserUIColumnConfigName } from "../../../../../../../../../helpers/Enum";



const ExpediteChildCustomCharts = ({recordCount}:{recordCount:any}) => {

    const [rowData,setRowData] = useState<any>();
    const [customError,setCustomError] = useState<string | null>(null);
    const [colDefs,setColDefs] = useState<any>();
    const {ref,gridColDefs, setGlobalColDef} = useContext(GridStateContext);
    const [gridState,setGridState] = useState<GridState>()

    const chunkSize = 10000;

    const {mutateAsync:getState,isLoading:isSavedDataLoading} = useGetState()
    const {mutateAsync:getPlanningDataCustom,isLoading} = useGetPlanningDataCustom();

    // const mapUIConfigToColdefs = (columns:Array<{header:string,colCode:string}>) => {
    //     let colDefs = [];

    //     colDefs = columns.map((column:{header:string,colCode:string})=>{
    //         const customColdef = getProductAndLocationHeirarchiesFromEnv(column,{enablePivot:true, enableValue:true,enableRowGroup:true}); 
    //         if(customColdef) return customColdef;

    //         return {
    //             field:column['colCode'],
    //             colId:column['colCode'],
    //             headerName:column['header'],
    //             enablePivot:true,
    //             enableValue:true,
    //             enableRowGroup:true,

    //         }
    //     })
    //     return [...colDefs];
    // }

    useEffect(()=>{
        const getTableState = async()=>{
            try{
                const data =  await getState({reportname: UserUIColumnConfigName.Expedite_To_Child_CS})
                setGridState(JSON.parse(data.data.data))
            }catch(err:any){
                setGridState({
                    charts:[],
                    columns:colDefs,
                    pivot:false
                })
            }
        }
        getTableState()
    },[colDefs])
    
    useEffect(()=>{
        if(ref?.current?.api && gridState && gridState?.columns.length>0){
            ref?.current?.api.applyColumnState({state:gridState.columns, applyOrder:true})
            // ref?.current?.api?.sizeColumnsToFit();
            ref?.current?.api.setGridOption('pivotMode',gridState.pivot)
        }
    },[gridState,ref])


    useEffect(()=>{
        const fetchCustomPlanningData = async ()=> {

            const rows:any = [];
            try {
     
                const numberOfPages = Math.ceil(recordCount/chunkSize);
                const toastId = notifyLoader(`Downloading Data 0 / ${recordCount}`)
                
                for(let i=1; i<=numberOfPages; i++){
                    const body = {
                        category:'expedite',
                        type:'child',
                        filters:[],
                        paginationParameter:{
                            pageNumber:i,
                            recordsPerPage:chunkSize
                        }
                    }
                    const result = await getPlanningDataCustom(body);
                    if(result.data.data === null) throw new Error("Something Went Wrong")
                    rows.push(...result.data.data.data)
                    if(i===numberOfPages) toast.update(toastId,{render:`Downloading Data ${recordCount} / ${recordCount}`})
                    else toast.update(toastId,{render:`Downloading Data ${i*chunkSize} / ${recordCount}`})
                }
                // P3 approved unavailable-state treatment: selected empty NMS
                // rows have quantities but no SKU/location identity.
                validateCustomRows(rows);
                setCustomError(null);
                // setColDefs(mapUIConfigToColdefs(uiconfig));
                setColDefs(getColumnDefinationsMTA(gridColDefs))
                setGlobalColDef(getColumnDefinationsMTA(gridColDefs));
                toast.dismiss(toastId);
           
                notifySuccess(`Data Fetched Successfully`);
              } catch (error) {
                toast.dismiss();
                setCustomError(error instanceof Error ? error.message : 'Custom view could not be loaded. Return to the normal view or retry.');
                setRowData([]);
                return;
              }
           
            setRowData(rows);

        }
        fetchCustomPlanningData();
    },[gridColDefs])
   

    if(customError) return <p role="alert">{customError}</p>;
    if(isLoading || isSavedDataLoading){
        return <VFLoader/>
    }

    
    return(
        <>
        <SCDynamicContainer style={{height:'100%'}}>
            <VFTable
                ref={ref}
                columnDefs={colDefs}
                rowData={rowData}
                sideBar= {{
                    toolPanels: [
                      {
                        id: "columns",
                        labelDefault: "Columns",
                        labelKey: "columns",
                        iconKey: "columns",
                        toolPanel: "agColumnsToolPanel",
                        toolPanelParams: {
                            suppressPivots: false,
                            suppressPivotMode: false,
                            suppressRowGroups: true,
                            suppressValues: false,
                        },
                      }
                    ]}
                  }
                enableCharts={true}
                enableRangeSelection={true} 
                rowSelection="multiple"
                statusBar = {{
                    statusPanels: [
                      { statusPanel: 'agTotalAndFilteredRowCountComponent', align:'left' },
                      { statusPanel: 'agTotalRowCountComponent', align:'left' },
                      { statusPanel: 'agFilteredRowCountComponent', align:'left' },
                      { statusPanel: 'agSelectedRowCountComponent', align:'left' },
                      { statusPanel: 'agAggregationComponent', align:'left' },
                    ],
                  }}                
                defaultColDef={{
                    floatingFilter:true,
                    filter: "agMultiColumnFilter",
                    cellStyle: {
                        textAlign: "center",
                        fontStyle: "normal",
                        fontVariant: "normal",
                        height: "50px",
                        display: "block",           
                        textOverflow: "ellipsis",   
                        whiteSpace: "nowrap",       
                    }
                }}
                disableZoomScaling={true}
                rowHeight={30}
                height={"80%"}
            />
        </SCDynamicContainer>
        </>
    )
    
}

export default ExpediteChildCustomCharts;
