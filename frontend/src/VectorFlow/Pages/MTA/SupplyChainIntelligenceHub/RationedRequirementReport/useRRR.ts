import { useState,useMemo,useEffect,useRef } from "react"
import { AgGridReactProps } from "ag-grid-react"

import { useGetRRRData,useGetRRRDataCount } from "../../../../Services/MTA/SupplyChainIntelligenceHub/RRR"
import { useUserData } from "../../../../../context"
import { RRREcoColorCellRenderer,RRRTechColorCellRenderer,RRRDispatchColorCellRenderer } from "./RRRCellRenderers"
import { convertUiConfigToOptions, MainMenuItemsCustomization, getColumnDefinationsMTA, CsvExportMTA} from "../../../../../helpers/utils"
import { notifyError, notifyLoader, notifySuccess} from "../../../../../helpers/notify"
import { toast } from "react-toastify";

import useBPRFilter from "../../../../../hooks/useBPRFilter";
import { defaultAgGridSideBarForBPR } from "../../../../../helpers/BPRConstants";
import { useGetState } from "../../../../../VectorFlow/Services/MTA/Common/UserUIConfig";
import { GridRef } from "../../../../../VectorFlow/types/MDM"
import useGetLastRunData from "../../../../../hooks/useGetLastRunData"
import { useGetUIConfigData } from "../../../../Services/MTA/Common/UIConfig"
import { UIColumnConfigName, UserUIColumnConfigName } from "../../../../../helpers/Enum"
import { useSelector } from "react-redux"
import { RootState } from "../../../../../redux/store/store"
import { rrrFailureMessage } from './rrrFailure';
import { settleRequestPair } from "../../requestPair";

 
  
const useRRR =()=>{

    const [internalRef,setInternalRef] = useState<any>()

    const {isSideBarOpen} = useUserData()
    const [RRRRowData,setRRRRowData] = useState<any[]>([])
    const [RRRColumns,setRRRColumns] = useState<any[]>([])
    const [RRRDataCount, setRRRDataCount]=useState<any>();
    const [reportError, setReportError] = useState<string | null>(null);

    const {state:currFilter,setState:setCurrFilter,onDelete} = useBPRFilter()
    const tempRef = useRef<GridRef>()
    const ref = useRef<GridRef>()

    const [currentPage,setCurrentPage] = useState<any>(1);

    const [tempDownloadData,setTempDownloadData] = useState<boolean>(false);

    const [exportExcelColumns,setExportExcelColumns] = useState<Array<any>>([])

    const [exportExcelRowData,setExportExcelRowData] = useState<Array<any>>([])

    const { mutateAsync: getUiConfig, isLoading: isUIConfigLoading } = useGetUIConfigData();
    const {mutateAsync:getRRRData, isLoading: isRRRLoading} =useGetRRRData();
    const {mutateAsync:getRRRDataCount, isLoading: isRRRCountLoading}=useGetRRRDataCount();

    const {mutateAsync:getState,isLoading:isSavedDataLoading} = useGetState()

    const [gridState,setGridState] = useState<any>()
    const [generalFilterOptions,setGeneralFilterOptions] = useState();

    const [initialColumnState, setInitialColumnState] = useState<any>(undefined);
    const [masterUIConfig, setMasterUIConfig] = useState<any>([]);
    const [hasSavedConfig, setHasSavedConfig] = useState<boolean>(false);

          
    const getRRRUiConfig = async () => {
        try {
            const response = await getUiConfig(UIColumnConfigName.RRR);
            setInitialColumnState(response.data.data);
        } catch (err: any) {
            notifyError("Something Went Wrong")
        }
    }


    // const [rowData,setRowData] = useState([]);
     
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const RRR_ROWS_PER_PAGE = EnvConfig['RRR_ROWS_PER_PAGE'];   
    const rowsPerPage = parseInt(RRR_ROWS_PER_PAGE || '100');
    const [userPageSize , setUserPageSize]  = useState<number>(RRR_ROWS_PER_PAGE?parseInt(RRR_ROWS_PER_PAGE):50)  
    const {date:lastRunDate} = useGetLastRunData()
  
    // useEffect(()=>{       
    //     const fetchData = async () => {
    //         await getDataCount();
    //         await getRRRRowData(currentPage);
    //         await getRRRUiConfig();
    //         setGeneralFilterOptions(convertUiConfigToOptions(initialColumnState))
    //     };
    //     fetchData();
    // }, []);

    useEffect(() => {
        const getTableState = async () => {
            try {
                const MappedColumns = getColumnDefinationsMTA(initialColumnState);
                  
                setGridState({
                    charts: [],
                    columns: MappedColumns,
                    pivot: false
                })
                setRRRColumns(MappedColumns);
                getUserColumnConfig();
            } catch (err: any) {
                console.log(err)

            }
        }
        if (initialColumnState !== undefined) {
            getTableState()
        }
    }, [initialColumnState]);

    useEffect(() => {
        if (RRRColumns.length) {
            if (internalRef?.api) {
                setMasterUIConfig(internalRef.api.getColumnState());
            }
        }
    }, [internalRef, RRRColumns]);
          
    const getUserColumnConfig = async () => {
        const stateData = await getState({ "reportname": UserUIColumnConfigName.RRR })
        if (stateData.data.data.length !== 0) {
            const parsedContent = JSON.parse(stateData.data.data)
            setGridState({
                charts: parsedContent.charts,
                columns: parsedContent.columns,
                pivot: parsedContent.pivot,
            })
            setHasSavedConfig(true);
          
        } else {
            setHasSavedConfig(false);
            console.log("Data not available");
        }
    }

    useEffect(() => {
    if (internalRef && gridState && gridState.columns) {
        const result = internalRef?.api.applyColumnState({ 
            state: gridState.columns, 
            applyOrder: true 
        });
        internalRef?.api.sizeColumnsToFit();
        
        if (hasSavedConfig && result) {
            setTimeout(() => {
                internalRef?.api.applyColumnState({ 
                    state: gridState.columns, 
                    applyOrder: true 
                });
            }, 0);
        }
    }
}, [internalRef, gridState, hasSavedConfig]);

    
    // const getRecordsCount=async(filter?:any)=>{
    //     const payload={
    //     filters:filter || currFilter,
    //     paginationParameter: {
    //     pageNumber: currentPage,
    //     // recordPerPage:20
    //     recordsPerPage: parseInt(process.env.REACT_APP_BOR_ROWS_PER_PAGE || '100')
    //     }
    // }
    // const resultCount=await getRRRDataCount(payload);
    // setRecordCount(resultCount?.data?.recordCount);
    // }

    // const loadGridData = async (pageNo:any,filter?:any)=> {
    // const payload={
    //     filters:filter || currFilter,
    //     paginationParameter:{pageNumber:pageNo,recordsPerPage:rowsPerPage}
    // }
    // const result = await getRRRData(payload);
    // setRRRRowData(result?.data.data)

    // }

    const onResetCallback = async () => {
        setGridState({
            charts: [],
            columns: masterUIConfig,
            pivot: false,
        })
    }

    const getDataCount=async (filter?:any) => {
        const rowDataCount =await getRRRDataCount({
            filters:filter || currFilter,
            paginationParameter:{
                pageNumber:1,
                recordsPerPage: rowsPerPage
            }
        })
        setRRRDataCount(rowDataCount?.data?.recordCount)
    }

    const getRRRRowData= async(pageNo:any , pageSize?:number)=>{
        try{
            if(RRRDataCount===0){
                await getDataCount(currFilter);
            }
            notifyLoader("Loading Grid Data")
            const rowData =await getRRRData({
                filters:currFilter,
                paginationParameter:{
                    pageNumber:pageNo,
                    recordsPerPage:pageSize ||parseInt(RRR_ROWS_PER_PAGE || '100')
                }
            }) 
        
        // setRecordCount(rowData.data.recordCount)
            setCurrentPage(pageNo)
            setRRRRowData(rowData?.data?.data)
            setReportError(null)
            toast.dismiss()
            notifySuccess("Data Loaded Successfully")
        }catch(err:any){
            toast.dismiss()
            setReportError(rrrFailureMessage(err))
            setRRRRowData([])
            setRRRDataCount(undefined)
        }
    }

    const onApplyFilter = async(filter:any)=>{
        setCurrFilter(filter);
        try {
          notifyLoader("Loading Grid Data");
          const [{ count: rowDataCount, grid: rowData }] = await Promise.all([settleRequestPair(
            () => getRRRDataCount({
              filters: filter,
              paginationParameter: { pageNumber: 1, recordsPerPage: rowsPerPage },
            }),
            () => getRRRData({
              filters: filter,
              paginationParameter: {
                pageNumber: 1,
                recordsPerPage: parseInt(
                  userPageSize || RRR_ROWS_PER_PAGE || "100"
                ),
              },
            })
          ), getRRRUiConfig()]);

          // setRecordCount(rowData.data.recordCount)
          setRRRDataCount(rowDataCount?.data?.recordCount)
          setCurrFilter(filter);
          setCurrentPage(1);
          if(rowData.data.data && Array.isArray(rowData.data.data))setRRRRowData(rowData?.data?.data);
          else setRRRRowData([])
          setReportError(null);
          toast.dismiss();
          notifySuccess("Data Loaded Successfully")
        } catch (err: any) {
          toast.dismiss();
          setReportError(rrrFailureMessage(err));
          setRRRRowData([])
          setRRRDataCount(undefined)
        }
    }

    const onDeleteFilter = async(parentId:any, filterId:any, value:any)=>{
        const updatedFilter = onDelete(parentId,filterId,value)
        onApplyFilter(updatedFilter)
    }

    const onColumnVisible = (event: any) => {
        const { column, visible } = event;
        console.log(column)
        // Optionally, you can update your state if needed (like in a sidebar with checkboxes)
        if(column!==null){
        setRRRColumns((prevColumns:any) =>
          prevColumns.map((col:any) =>
            col.field === column.colId ? { ...col, hide:!visible } : col
          )
        );
        }
    };

    const customCellRenderers = useMemo(() => (   
        {
        grapCellRenderer:'',
        colorTechCellRenderer:RRRTechColorCellRenderer,
        colorEcoCellRenderer:RRREcoColorCellRenderer,
        colorDispatchRender:RRRDispatchColorCellRenderer
      }), []);

      
  const defaultColDefObject = useMemo(()=>{
    return {
        floatingFilter: true,
        cellStyle: {       
            "textAlign": "center",
            "height": "50px",
            "fontStyle": "normal",
            "display": "block",
            "textOverflow": "ellipsis",
            "whiteSpace": "nowrap",
        },
    }
  },[])
    
    const agGridProps:AgGridReactProps = useMemo(()=>{
        return{
            tooltipShowDelay:0,
            tooltipTrigger:"focus",
            readOnlyEdit:true,
            suppressRowClickSelection:true,
            suppressRowTransform:true,
            components:customCellRenderers,
            enableBrowserTooltips:true,
            enableFillHandle: true,
            enableColResize:true,
            getMainMenuItems: MainMenuItemsCustomization,
            paginationPageSize:parseInt(RRR_ROWS_PER_PAGE|| '200'),
            gridOptions:{
                rowHeight:50,
                getRowStyle: (params: any) => {
                if (params.node.rowIndex % 2 === 0) {
                    return { background: "#EBEBEB" };
                }
                return { background: "#F7F7F7" };
                },
            },
            // onColumnVisible: onColumnVisible,
            pagination:false,
            sideBar:defaultAgGridSideBarForBPR,      
            defaultColDef:defaultColDefObject,
            onGridReady:(params)=>setInternalRef(params),
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


    const tempAgGridProps:AgGridReactProps =  useMemo (()=> {
        
        return {
          onRowDataUpdated:(event)=>{
            if(tempDownloadData) event?.api?.exportDataAsExcel({fileName:'RationedRequirementReport', columnKeys:ref.current?.api.getAllDisplayedColumns().map((c)=>c.getColId())});
           }
        }
    },[tempDownloadData])
      

    const onExportToExcelCallBack=async(pageNumber:number)=>{
        const payload = {
            id: 1,
            name: '',
            fields: [],
            filters: currFilter,
            paginationParameter: {
                pageNumber: pageNumber,
                recordsPerPage: 5000
            },
            ISExport:"1",
            reportName:"RRR",
            stream:1,
            responseType: `arraybuffer`
        }
        notifyLoader("Downloading Data...")
        try {
            await CsvExportMTA(payload, "RationedRequirementReport");
            notifySuccess(`Data Exported Successfully`);
        }
        catch(error) {
            console.log(error);
            notifyError("Error Exporting Excel")
            throw error;
        }
    }

    const savePageSize = async( pageSize:number)=>{
        setUserPageSize(pageSize)
        await getRRRRowData(currentPage,pageSize)
    }
    return {
        isSideBarOpen,
        RRRColumns,
        agGridProps,
        isLoading :  isUIConfigLoading || isRRRCountLoading || isRRRLoading,
        RRRRowData,
        RRRDataCount,
        reportError,
        currentPage,
        tempRef,
        tempDownloadData,
        setTempDownloadData,
        tempAgGridProps,
        exportExcelRowData,
        setExportExcelRowData,
        exportExcelColumns,
        setExportExcelColumns,
        onExportToExcelCallBack,
        getRRRRowData,
        onApplyFilter,
        currFilter,
        setCurrFilter,
        onDeleteFilter,
        isSavedDataLoading,
        ref,
        generalFilterOptions,
        onResetCallback,
        lastRunDate,
        savePageSize,
        userPageSize
    }
}

export default  useRRR


