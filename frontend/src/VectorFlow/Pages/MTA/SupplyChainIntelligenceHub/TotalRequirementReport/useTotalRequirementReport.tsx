import { useState,useMemo,useEffect,useRef } from "react"
import { AgGridReactProps } from "ag-grid-react"

import { useGetRRRDataCount } from "../../../../Services/MTA/SupplyChainIntelligenceHub/RRR"
import { useUserData } from "../../../../../context"
import { RRREcoColorCellRenderer,RRRDispatchColorCellRenderer } from "../RationedRequirementReport/RRRCellRenderers"
import { convertUiConfigToOptions, MainMenuItemsCustomization, getColumnDefinationsMTA } from "../../../../../helpers/utils"
import { notifyError} from "../../../../../helpers/notify"

import useBPRFilter from "../../../../../hooks/useBPRFilter";
import { defaultAgGridSideBarForBPR } from "../../../../../helpers/BPRConstants";
import { useGetState } from "../../../../Services/MTA/Common/UserUIConfig";
import { GridRef } from "../../../../types/MDM"
import { ColDef } from "ag-grid-enterprise"

import {RowData} from '../../../../../mock-data/RRR-Color-Bandwise'
import { TextToTextColorMapper } from "../BPR/BPRCellRenderers"
// import { type DailyDataGraph } from "../../../../types/MTA";
// import { useDispatch } from "react-redux"
// import { TOGGLE_GRAPH_MODAL, UPDATE_DAILY_DATA } from "../../../../../redux/actions/MTA"
import BPRGraphCellRenderer from "../BPR/BPRGraphCellRenderer"
import { useGetUIConfigData } from "../../../../Services/MTA/Common/UIConfig"
import { UIColumnConfigName, UserUIColumnConfigName } from "../../../../../helpers/Enum"
import { useSelector } from "react-redux"
import { RootState } from "../../../../../redux/store/store"


const useTotalRequirementReport =()=>{

    const [internalRef,setInternalRef] = useState<any>()

    const {isSideBarOpen} = useUserData()

    const [rowData,setRowData] = useState<any[]>(RowData)

    const [colDefs,setColDefs] = useState<Array<ColDef>>([])

    const [recordCount, setRecordCount]=useState<any>(30);

    const {state:currFilter,setState:setCurrFilter,onDelete} = useBPRFilter()

    const tempRef = useRef()

    const ref = useRef<GridRef>()

    // const dispatch = useDispatch()
   

    const [currentPage,setCurrentPage] = useState<any>(1);


    const [tempDownloadData,setTempDownloadData] = useState<boolean>(false);

    const [exportExcelColumns,setExportExcelColumns] = useState<Array<any>>([])

    const [exportExcelRowData,setExportExcelRowData] = useState<Array<any>>([])

    const { mutateAsync: getUiConfig, isLoading: isUIConfigLoading } = useGetUIConfigData();
    
    // const {mutateAsync:getRRRBandwiseData} =useGetRRRData();

    const {mutateAsync:getRRRBandwiseDataCount, isLoading: isRRRBandwiseDataCount}=useGetRRRDataCount();

    const {mutateAsync:getState,isLoading:isSavedDataLoading} = useGetState()

    const [gridState, setGridState] = useState<any>()
    const [masterUIConfig, setMasterUIConfig] = useState<any>([]);
    

    // const [rowData,setRowData] = useState([]);

 
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const TOTAL_REQUIREMENT_ROWS_PER_PAGE = EnvConfig['TOTAL_REQUIREMENT_ROWS_PER_PAGE']; 
    const rowsPerPage = parseInt(TOTAL_REQUIREMENT_ROWS_PER_PAGE || '100');

    // const RRRColorBandWiseColumns = useMemo(()=>mapRRRColorBandWiseFieldsToColDefs(data?.data.data),[data])

  
    useEffect(()=>{       
        const fetchData = async () => {
            // await getBandwiseDataCount();
            await getRRRColorBandWiseUiConfig()
            // await getRRRBandwiseRowData(currentPage);
            
        };
        fetchData();
    }, []);

    useEffect(() => {
        if (colDefs.length) {
          if (internalRef?.api) {
            setMasterUIConfig(internalRef.api.getColumnState());
          }
        }
    }, [internalRef, colDefs]);
    
    const getUserColumnConfig = async () => {
        const stateData = await getState({ "reportname": UserUIColumnConfigName.TRR })
        if (stateData.data.data.length !== 0) {
          const parsedContent = JSON.parse(stateData.data.data)
                        
          setGridState({
            charts: parsedContent.charts,
            columns: parsedContent.columns,
            pivot: parsedContent.pivot,
          })
                  
        } else {
          console.log("Data not available");
        }
    }
  
    useEffect(() => {
        if (internalRef && gridState && gridState.columns) {
            const result = internalRef.api.applyColumnState({ state: gridState.columns, applyOrder: true });
            internalRef?.api.sizeColumnsToFit();
            if (!result) {
                console.error("Failed to apply column state", result);
            }
        }
    }, [internalRef, gridState]);

    const onResetCallback = async () => {
        setGridState({
            charts: [],
            columns: masterUIConfig,
            pivot: false,
        })
    };

    const getBandwiseDataCount=async (filter?:any) => {
        const rowDataCount =await getRRRBandwiseDataCount({
            filters:filter || currFilter,
            paginationParameter:{
                pageNumber:1,
                recordsPerPage: rowsPerPage
            }
        })
        setRecordCount(rowDataCount?.data?.recordCount)
    }

    const getRRRColorBandWiseUiConfig = async () => {
        try {
            const response = await getUiConfig(UIColumnConfigName.TRR);
            const MappedColumns = getColumnDefinationsMTA(response.data.data, CustomHeader);
            setColDefs(MappedColumns);
            setGridState({
                charts: [],
                columns: MappedColumns,
                pivot: false
            });
        } catch (err: any) {
            notifyError("Something Went Wrong")
        }
    }

    useEffect(() => {
        if (colDefs.length) {
            getUserColumnConfig();
        }
    }, [colDefs]);


    const onApplyFilter = async(filter:any)=>{
        console.debug(filter)
        return 
    }

    const onDeleteFilter = async(parentId:any, filterId:any, value:any)=>{
        const updatedFilter = onDelete(parentId,filterId,value)
        onApplyFilter(updatedFilter)
    }

    const customCellRenderers = useMemo(() => (   
        {
        grapCellRenderer:BPRGraphCellRenderer,
        colorCellRenderer:TextToTextColorMapper,
        colorEcoCellRenderer:RRREcoColorCellRenderer,
        colorDispatchRender:RRRDispatchColorCellRenderer
        
      }), []);

    const agGridProps:AgGridReactProps = useMemo(()=>{
        return{
            tooltipShowDelay:0,
            tooltipTrigger:"focus",
            readOnlyEdit:true,
            gridOptions:{
                rowHeight:50,
                getRowStyle: (params: any) => {
                if (params.node.rowIndex % 2 === 0) {
                    return { background: "#EBEBEB" };
                }
                return { background: "#F7F7F7" };
                },
            },
            pagination:false,
            sideBar:defaultAgGridSideBarForBPR,
            getMainMenuItems: MainMenuItemsCustomization,          
            // overlayLoadingTemplate:'<object style="position:absolute;top:50%;left:50%;transform:translate(-50%, -50%) scale(2)" type="image/svg+xml" data="/assets/img/VectorFLOW/loaderMedium.svg" aria-label="loading"></object>',
            // rowSelection:'multiple',
            paginationPageSize:parseInt(TOTAL_REQUIREMENT_ROWS_PER_PAGE || '200'),
            suppressRowClickSelection:true,
            components:customCellRenderers,
            enableBrowserTooltips:true,
            defaultColDef:{
                floatingFilter: true,
                // filter: "agMultiColumnFilter",
                // tooltipComponent:'remarksToolTipComponent',
                cellStyle:{
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
                }
                // ,
                // onCellClicked:(params:any)=>{
                //     console.log(params)
                //     if(params.data.transit && params.data.transit.length>0){
                //         setActiveRow(params.data.transit)
                //         toggleSubGrid(true)
                //         return 
                //     }
                //     return setActiveRow(null)
                // }
            },
            onGridReady:(params)=>setInternalRef(params)      
        }
    
    },[])
    // const getRRRrowData=async(filter:BPRFilterState)=>{
    //     setActiveRow({})
    //     setCurrFilter(filter)



    //     if(filter)setCurrFilter(filter)
    //     try{
    //         if(recordCount===0 || filter){
    //             await getRecordsCount(filter)
    //             setCurrGridPage(currGridPage)
    //         }
    //         notifyLoader("Loading Grid Data")
    //         await loadGridData(currentPage,filter)
    //         toast.dismiss()
    //      }
    //    catch(err:any){
    //         notifyError(err)
    //     }
    // }


    const tempAgGridProps:AgGridReactProps = {
        onRowDataUpdated:(event)=>{
         if(tempDownloadData) event.api.exportDataAsExcel({fileName:'TotalRequirementReport', columnKeys:ref.current?.api.getAllDisplayedColumns().map((c)=>c.getColId())});
        }
      };

    const onExportToExcelCallBack=async(pageNumber:number)=>{
        console.debug(pageNumber)
        // const data =  await getRRRBandwiseData({
        //     filters:currFilter,
        //     paginationParameter:{
        //         pageNumber:pageNumber,
        //         recordsPerPage:5000
        //     }
        // })
        return rowData
        // return data.data.data
    }

    const generalFilterOptions = useMemo(()=>{
        return convertUiConfigToOptions(colDefs)
    }, [colDefs])
    
    const CustomHeader = {
        DispatchColor: {
            floatingFilter: true,
            cellRenderer: 'colorCellRenderer',
        },
    }

    return {
        isSideBarOpen,
        colDefs,
        agGridProps,
        isLoading :  isUIConfigLoading || isRRRBandwiseDataCount,
        rowData,
        recordCount,
        currentPage,
        setCurrentPage,
        tempRef,
        tempDownloadData,
        setTempDownloadData,
        tempAgGridProps,
        exportExcelRowData,
        setExportExcelRowData,
        exportExcelColumns,
        setExportExcelColumns,
        onExportToExcelCallBack,
        // getRRRBandwiseRowData,
        onApplyFilter,
        currFilter,
        setCurrFilter,
        onDeleteFilter,
        isSavedDataLoading,
        getBandwiseDataCount,
        ref,
        generalFilterOptions,
        setRowData,
        onResetCallback
    }
}

export default  useTotalRequirementReport


