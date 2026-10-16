import {useEffect, useContext, useState } from "react";
import { validateCustomRows } from './validateRows';

// import "./styles.css";
import VFTable from "../../../../../../../../components/VectorFLOW/commons/VFTable";
// import _ from "lodash";
import '../../styles.css';
import { useGetPlanningDataCustom } from "../../../../../../../Services/MTA/SupplyChainIntelligenceHub/Planning";
import VFLoader from "../../../../../../../../components/VectorFLOW/commons/VFLoader";
import { notifyLoader,notifyError,notifySuccess } from "../../../../../../../../helpers/notify";
import { SCDynamicContainer } from "../../styles";
import { toast } from 'react-toastify';
import { useGetState } from "../../../../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR";
import { GridStateContext } from "../../../../../../../../context/GridStateContext";
import { GridState } from "../../../../../../../../VectorFlow/types/BPR";
import {getProductAndLocationHeirarchiesFromEnv, convertStringNumToNumber, getColumnDefinationsMTA} from '../../../../../../../../helpers/utils';
import { UserUIColumnConfigName } from "../../../../../../../../helpers/Enum";
import { useUserData } from "../../../../../../../../context";
import { GridFilterWrapper, TextBtn } from "../../../../../../../../VectorFlow/Pages/MTO/Common/VFPagination/styles";



const OrderFulfillmentCustomCharts = ({recordCount}:{recordCount:any}) => {

  const {ref,gridColDefs, setGlobalColDef} = useContext(GridStateContext);
    const [rowData,setRowData] = useState<any>();
    const [colDefs,setColDefs] = useState<any>();
    const [gridState,setGridState] = useState<GridState>()
    const [isDisabled, setIsDisabled]= useState<boolean>(true)
    const [reportError, setReportError] = useState<string | null>(null);

    const {user} = useUserData()
    const theme_ui = user.user.theme_ui
    const chunkSize = 10000;

    const {mutateAsync:getState,isLoading:isSavedDataLoading} = useGetState()
    const {mutateAsync:getPlanningDataCustom,isLoading} = useGetPlanningDataCustom();

    // remove after merge
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
            const data =  await getState({reportname: UserUIColumnConfigName.Order_Fulfillment_Review_CS})
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
            // ref?.current?.api.sizeColumnsToFit();
            ref?.current?.api.setGridOption('pivotMode',gridState.pivot)
        }
    },[gridState,ref])

    useEffect(()=>{
        const fetchCustomPlanningData = async ()=> {
            const rows:any = [];
            setReportError(null);
            setRowData(undefined);
            try {
     
                const numberOfPages = Math.max(1, Math.ceil(recordCount/chunkSize));
                const toastId = notifyLoader(`Downloading Data 0 / ${recordCount}`)
                
                for(let i=1; i<=numberOfPages; i++){
                    const body = {
                        category:'orderFulfillment',
                        type:'review',
                        filters:[],
                        paginationParameter:{
                            pageNumber:i,
                            recordsPerPage:chunkSize
                        }
                    }
                    const result = await getPlanningDataCustom(body);
                    const sourceRows = validateCustomRows(result?.data?.data?.data);
                    const rowDataAfterTypeCasting = convertStringNumToNumber(sourceRows)
                    rows.push(...rowDataAfterTypeCasting)
                    if(i===numberOfPages) toast.update(toastId,{render:`Downloading Data ${recordCount} / ${recordCount}`})
                    else toast.update(toastId,{render:`Downloading Data ${i*chunkSize} / ${recordCount}`})
                }

                // remove after merge
                // setColDefs(mapUIConfigToColdefs(uiconfig));

                setColDefs(getColumnDefinationsMTA(gridColDefs));
                setGlobalColDef(getColumnDefinationsMTA(gridColDefs));
                toast.dismiss(toastId);
           
                notifySuccess(`Data Fetched Successfully`);
              } catch (error) {
                toast.dismiss();
                setReportError(error instanceof Error ? error.message : 'Custom view failed to load. Return to the normal view or retry later.');
                setRowData(undefined);
                return; // Never present partial/empty success after a failed request.
              }
           
            setRowData(rows);

        }
        fetchCustomPlanningData();
    },[])
   

    if(isLoading || isSavedDataLoading){
        return <VFLoader/>
    }
    if(reportError){
        return <SCDynamicContainer><p role="alert">{reportError}</p></SCDynamicContainer>;
    }
    if(Array.isArray(rowData) && rowData.length===0){
        return <SCDynamicContainer><p role="status">No custom-view rows are available for your current scope.</p></SCDynamicContainer>;
    }

    const sideBarForOrderFullFillment = {
        toolPanels: [
          {
            id: "columns",
            labelDefault: "Columns",
            labelKey: "columns",
            iconKey: "columns",
            toolPanel: "agColumnsToolPanel",
            // toolPanelParams: {},
            toolPanelParams: {
              suppressPivots: false,
              suppressPivotMode: false,
              suppressRowGroups: true,
              suppressValues: false,
            },
          }
          // },
          // {
          //   id: 'filters',
          //   labelDefault: 'Filters',
          //   labelKey: 'filters',
          //   iconKey: 'filter',
          //   toolPanel: 'agFiltersToolPanel',
          // }
        ],
        defaultToolPanel:'',
        }
      
        const clearGridFilter = () =>{
          ref?.current?.api.setFilterModel(null);
            setIsDisabled(true);
      }
    
              const CustomStatusPanel = () => {
                  return (
                      <GridFilterWrapper style={{marginTop:'25px'}}>
                          <TextBtn onClick={clearGridFilter} disabled={isDisabled} themeUi={theme_ui}>
                              Clear All Grid Filters
                          </TextBtn>  
                      </GridFilterWrapper>           
                  );
              };
    
    return(
        <>
        <SCDynamicContainer>
            <VFTable
                height={'100%'}
                ref={ref}
                columnDefs={colDefs}
                rowData={rowData}
                sideBar={sideBarForOrderFullFillment}
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
                      { statusPanel: CustomStatusPanel, align: "right" },

                    ],
                  }}
                  onFilterChanged={() => {
                    const filterModel = ref?.current?.api?.getFilterModel();
                    if (filterModel && Object.keys(filterModel).length > 0) {
                      setIsDisabled(false);
                    } else {
                      setIsDisabled(true);
                    }
                }} 
                defaultColDef={{
                floatingFilter:true,
                filter: "agMultiColumnFilter",
                cellStyle: {
                  textAlign: "center",
                  fontStyle: "normal",
                  fontVariant: "normal",
                  height: "50px", 
                }
                }}
                disableZoomScaling={true}
                rowHeight={30}
                suppressColumnVirtualisation={true}
            />
        </SCDynamicContainer>
        </>
    )
    
}

export default OrderFulfillmentCustomCharts;
