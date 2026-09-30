import { useState,useMemo,useEffect,useRef } from "react"
import { AgGridReactProps } from "ag-grid-react"
import { useGetDBMData,useGetDBMDataCount,useGetDBMApplySelectedNorm, useGetDBMUpdateSleepTbl} from "../../../../Services/MTA/DBM"
import { convertUiConfigToOptions, getColumnDefinationsMTA  } from "../../../../../helpers/utils"
//import { useRef } from "react"
// import {DBMSleepCellRenderer} from "./Sleep"
import BPRGraphCellRenderer from "../../SupplyChainIntelligenceHub/BPR/BPRGraphCellRenderer"
import {DBMTickCellRenderer} from "./dbmTick"
import { GridRef } from "../../../../../VectorFlow/types/MDM"
import {useSelector, useDispatch} from 'react-redux';
import {TOGGLE_GRAPH_MODAL,UPDATE_DAILY_DATA} from '../../../../../redux/actions/MTA';
import { type RootState } from "../../../../../redux/store/store";
import { DailyDataGraph } from "../../../../types/MTA"
import { useGetDailyData } from "../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR"
import useBPRFilter from '../../../../../hooks/useBPRFilter'
import { notifyError, notifyLoader, notifySuccess } from "../../../../../helpers/notify"
import { toast } from "react-toastify"
import SuggestionCategoryCellRenderer from "./SuggestionCategoryCellRendere"
import { defaultAgGridSideBarForBPR } from "../../../../../helpers/BPRConstants";
import { ColDef } from 'ag-grid-community';
import useGetLastRunData from "../../../../../hooks/useGetLastRunData"
import { UIColumnConfigName, UserUIColumnConfigName } from "../../../../../helpers/Enum"
import { useGetUIConfigData } from "../../../../Services/MTA/Common/UIConfig"
import { useGetState } from "../../../../Services/MTA/Common/UserUIConfig"

const useDBM =()=>{
    //const [DBMApplySelectedNormData,setDBMApplySelectedNormData] = useState<any[]>([])
    const gridRef = useRef<GridRef>();
    const tempRef:any = useRef()
    const [DBMRowData,setDBMRowData] = useState<any[]>([])
    const [DBMDataCount, setDBMDataCount]=useState<any>();
    // const [recordCount,setRecordCount] = useState<number>(0)

    const [internalRef,setInternalRef] = useState<any>()
    const [gridState,setGridState] = useState<any>()

    const {state:currentFilter,setState:setCurrentFilter,onDelete} = useBPRFilter()
    const [currentPage,setCurrentPage] = useState<any>(1);

    const [tempDownloadData,setTempDownloadData] = useState<boolean>(false);

    const [exportExcelColumns,setExportExcelColumns] = useState<Array<any>>([])

    const [exportExcelRowData,setExportExcelRowData] = useState<Array<any>>([])

    const exportTimeout = useRef<NodeJS.Timeout | null>(null);

    const { mutateAsync: getUiConfig, isLoading: isUIConfigLoading } = useGetUIConfigData();
    
    const {mutateAsync:getDBMData, isLoading: isDBMDataLoading} =useGetDBMData();
    const {mutateAsync:getDBMApplySelectedNorm} =useGetDBMApplySelectedNorm();
    const {mutateAsync: getDBMUpdateSleepTbl} = useGetDBMUpdateSleepTbl();
    const {mutateAsync:getDBMDataCount, isLoading: isDBMDataCountLoading}=useGetDBMDataCount();

    const showDailyDataGraphModal = useSelector((state:RootState) => state.mta.showDailyDataGraphModal);
    const showNormChangeHistoryTable = useSelector((state:RootState) => state.mta.showNormChangeHistoryTable);
    const dailyData = useSelector((state:RootState) => state.mta.dailyData);

    const {mutateAsync:getState} = useGetState()

    const {mutateAsync:getDailyData} = useGetDailyData();
    const [generalFilterOptions,setGeneralFilterOptions] = useState();


    const dispatch = useDispatch();
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const DBM_ROWS_PER_PAGE = EnvConfig['DBM_ROWS_PER_PAGE']; 

    const recordsPerPage = parseInt(DBM_ROWS_PER_PAGE || '50');
    const [userPageSize , setUserPageSize]  = useState<number>(DBM_ROWS_PER_PAGE?parseInt(DBM_ROWS_PER_PAGE):50) 
    const columnsToBeExcluded = ['checkbox', 'dailydatagraph', '0', 'Sleep']
    const [initialColumnState, setInitialColumnState] = useState<any>(undefined);
    const [masterUIConfig, setMasterUIConfig] = useState<any>([]);
    const [DBMColumns,setDBMColumns] = useState<ColDef[]>([])
    const {date:lastRunDate} = useGetLastRunData()

    const customCellRenderers = useMemo(() => ({
        tickCellRenderer:DBMTickCellRenderer,
        grapCellRenderer:BPRGraphCellRenderer,
        suggestionCategoryCellRenderer:SuggestionCategoryCellRenderer
      }), []);

    const getDBMUiConfig = async () => {
        try {
            const response = await getUiConfig(UIColumnConfigName.DBM);
            setInitialColumnState(response.data.data);
        } catch (err: any) {
            notifyError("Something Went Wrong")
        }
    }

    useEffect(() => {
        const getTableState = async () => {
            try {
                const MappedColumns = getColumnDefinationsMTA(initialColumnState, CustomHeader, extras);
                                  
                setGridState({
                    charts: [],
                    columns: MappedColumns,
                    pivot: false
                })
                setDBMColumns(MappedColumns);
                getUserColumnConfig();
                setGeneralFilterOptions(convertUiConfigToOptions(initialColumnState));
                  
            } catch (err: any) {
                console.log(err)
            }
        }
        if (initialColumnState !== undefined) {
            getTableState()
        }
    }, [initialColumnState]);

    useEffect(() => {
        if (DBMColumns.length) {
            if (internalRef?.api) {
                setMasterUIConfig(internalRef.api.getColumnState());
            }
        }
    }, [internalRef, DBMColumns]);
              
    const getUserColumnConfig = async () => {
        const stateData = await getState({ "reportname": UserUIColumnConfigName.DBM })
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

    const onOpenDailyDataGraph = async (params:any) => {
        const payload:any = {
            SKUCode:params.data['SKUCode'],
            WHCode:params.data['LocCode']
        }
        const result = await getDailyData(payload)
        const data = result.data.data[0];
        const dailyData:DailyDataGraph = {
            rowData:params.data,
            chartData:data['StockData'] ? data['StockData'] : [],
            normChangeData:data['NormChangeHistoryData'] ? data['NormChangeHistoryData'] : [],
            masterData:data['MasterData'][0],
            suggestionData:data['SuggestionHistoryData'] ? data['SuggestionHistoryData'] : [],
            monitoringData:data['MonitoringData']
        }
    
        dispatch(UPDATE_DAILY_DATA(dailyData));
        dispatch(TOGGLE_GRAPH_MODAL(true));

    }

    const refetchAfter = ()=>{
        getDataCount(currentFilter);
        getDBMRowData(currentFilter,currentPage);
    }

    const showAllCheckbox = () => {
        const rows:any[] = []
        let allSelected = true;

            gridRef.current?.api.forEachNode((n) => {
                rows.push(n);
                if (!n.isSelected()) {
                    allSelected = false;
                }
            });

            if (allSelected) {
                gridRef.current?.api.deselectAll();
            } else {
                gridRef.current?.api.selectAll();
            }
    }

    
    const onResetCallback = async () => {
        setGridState({
            charts: [],
            columns: masterUIConfig,
            pivot: false,
        })
    };
    

    const extras = [
        {
            field: 'checkbox',
            colId: 'checkbox',
            headerName: '',
            width: 45,
            minWidth: 45,
            floatingFilter: false,
            checkboxSelection: true,
            headerCheckboxSelection: true,
            headerCheckboxSelectionCurrentPageOnly: true,
            resizable: false,
            suppressMenu: true,
            maxWidth: 45,
            pinned: 'left',
            lockPosition: 'left',
            filter: false,
            position:0,
        }
    ];
    
    const CustomHeader = {
        dailydatagraph: {
            width: 60,
            minWidth: 60,
            maxWidth: 70,
            lockPosition: true,
            filter: false,
            cellRenderer: 'grapCellRenderer',
            cellRendererParams: { onOpenDailyDataGraph: onOpenDailyDataGraph },
            pinned: 'left',
            resizable: false,
            floatingFilter: false,
            suppressColumnsToolPanel: false,
            tooltipField: "DailyDataGraph",
            suppressMenu: true,
            headerTooltip: "Daily Data Graph",

        },
        // Sleep: {
        //     lockPosition: true,
        //     cellRenderer: 'sleepCellRenderer',
        //     cellRendererParams: {
        //         callBack: refetchAfter
        //     },
        //     floatingFilter: false,
        //     minWidth: 100,
        //     maxWidth: 100,
        //     pinned: 'left',
        //     suppressMenu: true
        // },
        Suggestions: {
            lockPosition: true,
            cellRenderer: 'suggestionCategoryCellRenderer',
            floatingFilter: false,
            minWidth: 40,
            maxWidth: 40,
            initialHide: false,
            pinned: 'left',
            suppressMenu: true
        },

    }

    const handleChangePage = async (pageNo:any) => {
        setCurrentPage(pageNo);
        getDBMRowData(currentFilter,pageNo);
    }

     const handleGoButton =  async(pageNo:any)=>{
        notifyLoader("Submitting Norms")
        const selectedRows = gridRef.current?.api.getSelectedRows();
        if (!selectedRows || selectedRows?.length === 0) { 
            notifyError("No Rows Selected.");
            return;
        }
        const extractedData:any = selectedRows?.map (items => ({
            SKUCode:items.SKUCode,
            WHCode:items.LocCode
        }));

            await getDBMApplySelectedNorm({
                data:extractedData,
                filters:[],
                paginationParameter:{
                    pageNumber:1,
                    recordsPerPage:recordsPerPage
                }
            })
        toast.dismiss()
        notifySuccess("Submitted Successfully")
        refetchAfter()
   }

   const handleGoButtonForSleep =  async(pageNo:any)=>{
        notifyLoader("Submitting Norms")
        const selectedRows = gridRef.current?.api.getSelectedRows();
        if (!selectedRows || selectedRows?.length === 0) { 
            notifyError("No Rows Selected.");
            return;
        }
        const extractedDataForSleep:any = selectedRows?.map (items => ({
            SKUCode:items.SKUCode,
            WHCode:items.LocCode
        }));

            await getDBMUpdateSleepTbl({
                data:extractedDataForSleep,
            });

        toast.dismiss();
        notifySuccess("Submitted Successfully");
        refetchAfter();
   }

    useEffect(()=>{       
        getDataCount(currentFilter);
        getDBMRowData(currentFilter,currentPage);
        getDBMUiConfig();

    },[])

   

  const tempAgGridProps: AgGridReactProps = useMemo(() => {
    return {
      onRowDataUpdated: (event) => {
        const columnsToBeIncluded = gridRef.current?.api
          .getAllDisplayedColumns()
          .map((c) => c.getColId())
          .filter((key: string) => !columnsToBeExcluded.includes(key));
        // const columnsToBeIncluded = ref.current?.api?.getAllDisplayedColumns().map((c:any)=>c.getColId()).filter((key:string)=>!columnsToBeExcluded.includes(key));
        if (
          tempDownloadData &&
          gridRef.current?.api &&
          gridRef.current.api.getDisplayedRowCount() > 0
        ) {
          if (exportTimeout.current) clearTimeout(exportTimeout.current);
          exportTimeout.current = setTimeout(() => {
            event?.api?.exportDataAsExcel({
              fileName: "DBMNormSuggestions",
              columnKeys: columnsToBeIncluded,
            });
            setTempDownloadData(false);
          }, 300); // adjust debounce as needed
        }
      },
    };
  }, [tempDownloadData, gridRef]);

    const getDataCount=async (filter:any) => {
        const rowDataCount =await getDBMDataCount({
            filters:filter,
            paginationParameter:{
                pageNumber:1,
                recordsPerPage:recordsPerPage
            }
        })
        setDBMDataCount(rowDataCount?.data?.recordCount)
    }

    const getDBMRowData= async(filter:any,pageNo:any, pageSize?:number)=>{
        notifyLoader("Loading Grid Data")
        const rowData =await getDBMData({
            filters:filter,
            paginationParameter:{
                pageNumber:pageNo,
                recordsPerPage:pageSize || userPageSize || recordsPerPage
            }
        })
        toast.dismiss()
        notifySuccess("Data Loaded Successfully")
        // console.log(rowData.data.data)
        setDBMRowData(rowData?.data?.data || [])
    }

    const handleApplyFilter = async(filter:any)=>{
        setCurrentPage(1)
        setCurrentFilter(filter)
        await getDataCount(filter)
        await getDBMRowData(filter,1)
        getDBMUiConfig()
    }

    const onDeleteFilter = async(parentId:any, filterId:any, value:any)=>{
        const updatedFilter = onDelete(parentId,filterId,value)
        handleApplyFilter(updatedFilter)
    }

    const onExportToExcelCallBack= async(pageNo:any)=>{
        const rowData =await getDBMData({
            filters:currentFilter,
            paginationParameter:{
                pageNumber:pageNo,
                recordsPerPage:5000
            }
        })

        getDBMUiConfig()
        // console.log(rowData.data.data)
        return rowData.data.data
    }


    const agGridProps:AgGridReactProps = useMemo(()=>{
        return {
            tooltipShowDelay:0,
            tooltipTrigger:"focus",
            readOnlyEdit:true,
            suppressRowClickSelection:true,
            components:customCellRenderers,
            enableBrowserTooltips:true,
            rowSelection:'multiple',
            gridOptions:{
                rowHeight:50,
                getRowStyle: (params: any) => {
                if (params.node.rowIndex % 2 === 0) {
                    return { background: "#EBEBEB" };
                }
                return { background: "#F7F7F7" };
                },
            },
            sideBar:defaultAgGridSideBarForBPR,
            pagination:false,
            defaultColDef:{
                floatingFilter: true,
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
            },
            onGridReady:(params)=>setInternalRef(params)
        }
    },[])

    const savePageSize = async( pageSize:number)=>{
        setUserPageSize(pageSize)
        await getDBMRowData(currentFilter , currentPage,pageSize)
    }

    return {
        DBMColumns,
        agGridProps,
        isLoading :  isUIConfigLoading || isDBMDataLoading || isDBMDataCountLoading,
        DBMRowData,
        handleChangePage,
        gridRef,
        showAllCheckbox,
        DBMDataCount,
        currentPage,
        handleGoButton,
        handleGoButtonForSleep,
        showDailyDataGraphModal,
        showNormChangeHistoryTable,
        dailyData,
        tempRef,
        tempDownloadData,
        setTempDownloadData,
        tempAgGridProps,
        exportExcelRowData,
        setExportExcelRowData,
        exportExcelColumns,
        setExportExcelColumns,
        handleApplyFilter,
        currentFilter,
        setCurrentFilter,
        onDeleteFilter,
        onExportToExcelCallBack,
        recordsPerPage,
        generalFilterOptions,
        onResetCallback,
        lastRunDate,
        savePageSize,
        userPageSize
    }
}

export default  useDBM