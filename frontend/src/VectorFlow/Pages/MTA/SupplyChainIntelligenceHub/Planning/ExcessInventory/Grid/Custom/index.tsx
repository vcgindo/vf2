import {useEffect, useState,useContext } from "react";

// import "./styles.css";
import VFTable from "../../../../../../../../components/VectorFLOW/commons/VFTable";
// import _ from "lodash";
import '../../styles.css';
import { useGetPlanningDataCustom } from "../../../../../../../Services/MTA/SupplyChainIntelligenceHub/Planning";
import VFLoader from "../../../../../../../../components/VectorFLOW/commons/VFLoader";
import { notifyLoader,notifyError,notifySuccess } from "../../../../../../../../helpers/notify";
import { SCDynamicContainer } from "../../styles";
import { toast } from 'react-toastify';
import { useGetState } from "../../../../../../../Services/MTA/SupplyChainIntelligenceHub/BPR";
import { GridStateContext } from "../../../../../../../../context/GridStateContext";
import { GridState } from "../../../../../../../types/BPR";
import { getProductAndLocationHeirarchiesFromEnv, convertStringNumToNumber, getColumnDefinationsMTA } from '../../../../../../../../helpers/utils';
import { UserUIColumnConfigName } from "../../../../../../../../helpers/Enum";
import { useUserData } from "../../../../../../../../context";
import { GridFilterWrapper, TextBtn } from "../../../../../../../../VectorFlow/Pages/MTO/Common/VFPagination/styles";




const ExcessInventoryCustomCharts = ({recordCount}:{recordCount:any}) => {

    const [rowData,setRowData] = useState<any>();
    const [loadError,setLoadError] = useState<string | null>(null);
    const [colDefs,setColDefs] = useState<any>();
    const {ref,gridColDefs, setGlobalColDef} = useContext(GridStateContext);
    const [isDisabled, setIsDisabled]= useState<boolean>(true)

    const {user} = useUserData()
    const theme_ui = user.user.theme_ui

    const [gridState,setGridState] = useState<GridState>()

    const chunkSize = 10000;

    const {mutateAsync:getState,isLoading:isSavedDataLoading} = useGetState()
    const {mutateAsync:getPlanningDataCustom,isLoading} = useGetPlanningDataCustom();

    //remove after merge
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

            const data =  await getState({reportname: UserUIColumnConfigName.Excess_Inventory_Review_CS})
            setGridState(JSON.parse(data.data.data))
          }catch(err:any){
            setGridState({
                charts:[],
                columns: colDefs,
                pivot:false
            })
          }
        }
        getTableState()
    },[colDefs])

    useEffect(() => {
      if (
        ref?.current &&
        gridState &&
        gridState.columns?.length !== 0 
      ) {
        ref?.current?.api?.applyColumnState({ state: gridState.columns, applyOrder: true });
        // ref?.current?.api?.sizeColumnsToFit();
        ref?.current?.api?.setGridOption("pivotMode", gridState.pivot);
      }
    }, [ref,gridState]);
    
    useEffect(()=>{
        setColDefs(getColumnDefinationsMTA(gridColDefs));
        setGlobalColDef(getColumnDefinationsMTA(gridColDefs));
    },[gridColDefs]);

    useEffect(()=>{
        const fetchCustomPlanningData = async ()=> {
            const rows:any = [];
            try {
     
                const numberOfPages = Math.ceil(recordCount/chunkSize);
                const toastId = notifyLoader(`Downloading Data 0 / ${recordCount}`)
                
                for(let i=1; i<=numberOfPages; i++){
                    const body = {
                        category:'excessInventory',
                        type:'review',
                        filters:[],
                        paginationParameter:{
                            pageNumber:i,
                            recordsPerPage:chunkSize
                        }
                    }
                    const result = await getPlanningDataCustom(body);
                    if(result.data.data === null) throw new Error("Something Went Wrong")
                    const rowDataAfterTypeCasting = convertStringNumToNumber(result.data.data.data)
                    rows.push(...rowDataAfterTypeCasting)
                    if(i===numberOfPages) toast.update(toastId,{render:`Downloading Data ${recordCount} / ${recordCount}`})
                    else toast.update(toastId,{render:`Downloading Data ${i*chunkSize} / ${recordCount}`})
                }
                // remove after merge
                // setColDefs(mapUIConfigToColdefs(uiconfig)); 
                

                setLoadError(null);
                
                toast.dismiss(toastId);
           
                notifySuccess(`Data Fetched Successfully`);
              } catch (error) {
                toast.dismiss();
                rows.length = 0;
                setLoadError('The custom Excess view could not be loaded. Go Back and reopen it to retry. No partial or replacement results are shown.');
                notifyError('Something Went Wrong');
              }
            setRowData(rows);

        }
        fetchCustomPlanningData();
    },[])
   
    if(isLoading || isSavedDataLoading){
        return <VFLoader/>
    }
    if(loadError) return <p role="alert">{loadError}</p>;

    const sideBarForExcessInventory = {
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
      },
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
        {rowData?.length === 0 && <p role="status">No custom rows are available in the selected data. This view requires matching NMS metadata; its summary count does not guarantee matching custom rows. No missing metadata has been fabricated.</p>}
        <SCDynamicContainer>
            <VFTable
                ref={ref}
                columnDefs={colDefs}
                rowData={rowData}
                sideBar={sideBarForExcessInventory}
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
                pivotMode={false}
                suppressDragLeaveHidesColumns={true}
                disableZoomScaling={true}
                rowHeight={30}
                height={'100%'}
                maintainColumnOrder
                suppressColumnVirtualisation={true}
            />
        </SCDynamicContainer>
        </>
    )
    
}

export default ExcessInventoryCustomCharts;
