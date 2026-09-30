// import { useGetBORUIConfiguration, useBORData, useBORDataCount } from "../../../../Services/MTA/SupplyChainIntelligenceHub/BuyerOrderReport"
import {useGetDailyData} from '../../../../Services/MTA/SupplyChainIntelligenceHub/BPR'
import { convertUiConfigToOptions, MainMenuItemsCustomization, getColumnDefinationsMTA  } from "../../../../../helpers/utils"
import { useState,useMemo, useEffect,useRef } from "react"
import { AgGridReactProps } from "ag-grid-react"
import BPRGraphCellRenderer from "../BPR/BPRGraphCellRenderer"
import { BPRFilterState } from "../../../../types/BPR"

import { useSelector,useDispatch } from "react-redux"

import { RootState } from "../../../../../redux/store/store"
import {TOGGLE_GRAPH_MODAL,UPDATE_DAILY_DATA} from '../../../../../redux/actions/MTA';
import { type DailyDataGraph } from "../../../../types/MTA";
import { notifyError, notifyLoader, notifySuccess} from "../../../../../helpers/notify"
import { toast } from "react-toastify"

import useBPRFilter from "../../../../../hooks/useBPRFilter";
import { defaultAgGridSideBarForBPR } from "../../../../../helpers/BPRConstants";
import { GridRef } from "../../../../types/MDM"
import { BPRSubmitRemarkCellRenderer, TextToTextColorMapper } from "../BPR/BPRCellRenderers"

import { ColDef } from "ag-grid-enterprise"
import { useGetBORColorBandWisData, useGetBORColorBandWiseRecordCount, useGetBOROARemarkHistory, useSubmitBOROARemark } from '../../../../Services/MTA/SupplyChainIntelligenceHub/BORColorBandWise'
import useGetLastRunData from "../../../../../hooks/useGetLastRunData"
import { BORRemarksCellRenderer } from "../BuyerOrderReport/BORCellRenderers"
import { CSSProperties } from 'styled-components'
import useViewPort from '../../../../../hooks/useViewPort'
import { useGetUIConfigData } from '../../../../Services/MTA/Common/UIConfig'
import { useGetState } from '../../../../Services/MTA/Common/UserUIConfig'
import { UIColumnConfigName, UserUIColumnConfigName } from '../../../../../helpers/Enum'
import { useGetSupplierWiseAllocationCount, useGetSupplierWiseAllocationData } from '../../../../Services/MTA/SupplyChainIntelligenceHub/SupplierWiseAllocation'

export const useSupplierWiseAllocation =()=>{

    const ref=  useRef<GridRef>()

    const tempRef = useRef()

    const [internalRef,setInternalRef] = useState<any>()

    const [editedRows,setEditedRows] = useState<Array<any>>([])

    const {state:currFilter,setState:setCurrFilter,onDelete} = useBPRFilter()


  const { mutateAsync: getUiConfig, isLoading: isUIConfigLoading } = useGetUIConfigData();

     const {mutateAsync:submitRemark} = useSubmitBOROARemark()

     const dispatch = useDispatch();
   
    //  const [toggleSubGrid] = useState<boolean>(false);
     const [currGridPage,setCurrGridPage] = useState<number>(1)

     const [rowData,setRowData] = useState<Array<any>>([]);

     const [recordCount,setRecordCount] = useState<number>(0)

     const [currentPage,setCurrentPage] = useState(1);

     const [tempDownloadData,setTempDownloadData] = useState<boolean>(false);

     const [exportExcelColumns,setExportExcelColumns] = useState<Array<any>>([])
 
     const [exportExcelRowData,setExportExcelRowData] = useState<Array<any>>([])


     const showDailyDataGraphModal = useSelector((state:RootState) => state.mta.showDailyDataGraphModal);

     const showNormChangeHistoryTable = useSelector((state:RootState) => state.mta.showNormChangeHistoryTable);

     const dailyData = useSelector((state:RootState) => state.mta.dailyData);
    //  const rowsPerPage=50;
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const SUPPLY_WISE_ALLOCATION_HUB_ROWS_PER_PAGE = EnvConfig['SUPPLY_WISE_ALLOCATION_HUB_ROWS_PER_PAGE'];   
     const rowsPerPage = parseInt(SUPPLY_WISE_ALLOCATION_HUB_ROWS_PER_PAGE || '5000');
    const [userPageSize , setUserPageSize]  = useState<number>(SUPPLY_WISE_ALLOCATION_HUB_ROWS_PER_PAGE?parseInt(SUPPLY_WISE_ALLOCATION_HUB_ROWS_PER_PAGE):50)  

     const {date:lastRunDate} = useGetLastRunData()

     const handleChangePage = async (pageNo:any) => {
         setCurrentPage(pageNo);
         loadGridData(pageNo,currFilter);
      }

     const {mutateAsync:getData, isLoading: isDataLoading} = useGetSupplierWiseAllocationData();

     const {mutateAsync:getDataCount, isLoading: isCountLoading} = useGetSupplierWiseAllocationCount();

     const {mutateAsync:getDailyData, isLoading: isDailyDataLoading} = useGetDailyData();
  const [initialColumnState, setInitialColumnState] = useState<any>(undefined);
  const [masterUIConfig, setMasterUIConfig] = useState<any>([]);
  const [BORCBColumns, setBORCBColumns] = useState<ColDef[]>([])
     const [isRemarkHistoryToolTipOpen,setIsRemarkHistoryToolTipOpen] = useState<boolean>(false)
     const [remarkHistory,setRemarkHistory] = useState<any[]>([])
        
     const {getGridZoom,getScreenZoomValue} = useViewPort()
     const screenZoom = getScreenZoomValue() 
 
     const gridZoom = getGridZoom()
    const [remarkHistoryToolipPosition,setRemarkHistoryToolipPosition] = useState<CSSProperties>({})
     
      const {mutateAsync:getBORRemarkHistory} = useGetBOROARemarkHistory();

  const onCloseRemarkHistory = () => setIsRemarkHistoryToolTipOpen(false)
  const { mutateAsync: getState, isLoading: isSavedDataLoading } = useGetState()
  const [gridState, setGridState] = useState<any>()


     const customCellRenderers = useMemo(() => ({
        grapCellRenderer:BPRGraphCellRenderer,
        submitRemarkCellRenderer:BPRSubmitRemarkCellRenderer,
        colorCellRenderer:TextToTextColorMapper,
        remarksCellRenderer:BORRemarksCellRenderer
        
      }), []);

      const onCellValueChanged = (newRow: any, primaryKey1: string,primaryKey2:string,primaryKey3:string) => {
        setEditedRows((prev) => {
          let found = false; // Flag to track if the row has been updated
          const updatedRows = prev.map((row) => {
            if (row[primaryKey1] === newRow[primaryKey1] && row[primaryKey2]===newRow[primaryKey2] && row[primaryKey3]===newRow[primaryKey3]) {
              found = true;
              return newRow.remarks && newRow.remarks.length !== 0 ? { ...newRow } : null; // Return updated row
            }
            return row; // Return unchanged row
          });
  
          const filteredUpdatedRows = updatedRows.filter(row => row !== null);
      
          if (!found && newRow.remarks && newRow.remarks.length > 0) {
            // If no existing row was found, add the new row
            return [...filteredUpdatedRows, {...newRow}];
          }
          return filteredUpdatedRows;
        });
      };
  

  const onOpenDailyDataGraph = async (params: any) => {
    notifyLoader("Loading Daily Data Graph...");
        const payload:any = {
            SKUCode:params.data['SKUCode'],
            WHCode:params.data['WHCode']
    }
    try {
      
      const result = await getDailyData(payload)
      const data = result.data.data[0];
      const dailyData:DailyDataGraph = {
        rowData:params.data,
        chartData:data['StockData'] ? data['StockData'] : [],
        normChangeData:data['NormChangeHistoryData'] ? data['NormChangeHistoryData'] : [],
        masterData: Array.isArray(data['MasterData']) && data['MasterData']?.length > 0 ? data['MasterData'][0] : undefined,
        suggestionData:data['SuggestionHistoryData'] ? data['SuggestionHistoryData'] : [],
        monitoringData:data['MonitoringData'] ? data['MonitoringData'] : []
      }
      
      dispatch(UPDATE_DAILY_DATA(dailyData));
      dispatch(TOGGLE_GRAPH_MODAL(true));
      notifySuccess("Fetched Daily Data graph!")
    }
    catch (e) {
      notifyError("Failed to load graph data!");
    }
    }

    const onOpenRemarkHistory = async(e:React.MouseEvent<HTMLElement>,row:any)=>{
      try{
          setIsRemarkHistoryToolTipOpen(false)
          const toastId = notifyLoader("Getting remark history")
          const {top,left} = e.currentTarget.getBoundingClientRect()
          setRemarkHistoryToolipPosition({
              top: top *  gridZoom * screenZoom,
              left: left *  gridZoom * screenZoom,
              height:360,
              width:350
          })
          console.log("row...", row)
          const {data} = await getBORRemarkHistory(row)
          toast.dismiss(toastId)
          setRemarkHistory(data.data)
          setIsRemarkHistoryToolTipOpen(true)
      }catch(err:any){
          notifyError(err.message)
      }
      }


  useEffect(() => {
    const getTableState = async () => {
      try {
        const MappedColumns = getColumnDefinationsMTA(initialColumnState, CustomHeader);
                  
        setGridState({
          charts: [],
          columns: MappedColumns,
          pivot: false
        })
        setBORCBColumns(MappedColumns);
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
    if (BORCBColumns.length) {
      if (internalRef?.api) {
        setMasterUIConfig(internalRef.api.getColumnState());
      }
    }
  }, [internalRef, BORCBColumns]);

  const getUserColumnConfig = async () => {
    const stateData = await getState({ "reportname": UserUIColumnConfigName.SupplierWiseAllocation })
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

      useEffect(()=>{       
        const fetchData = async () => {
            await getRecordsCount();
            await getSupplierWiseAllocationUIConfig()
            await loadGridData(currentPage);

        };
        fetchData();

    }, []);


      const getRecordsCount=async(filter?:any , pageSize?:number)=>{
        const payload={
          filters:filter || {},
          paginationParameter: {
            pageNumber: currentPage,
            recordsPerPage: pageSize || userPageSize || parseInt(SUPPLY_WISE_ALLOCATION_HUB_ROWS_PER_PAGE || '100')
          }
        }
        const resultCount=await getDataCount(payload);
        
        setRecordCount(resultCount?.data?.data[0]?.count || 0); 
      }
    
    const loadGridData = async (pageNo:any,filter?:any , pageSize ?:number)=> {
        try{
          notifyLoader("loading Grid Data")
          const payload={
            filters:filter || {},
            paginationParameter:{pageNumber:pageNo,recordsPerPage:pageSize || userPageSize || userPageSize}
        }
        const result = await getData(payload);
        setRowData(result.data.data)
        toast.dismiss()
        notifySuccess("Data Loaded Successfully")
        }catch(err:any){
          notifyError(err)
          setRecordCount(0)
          setRowData([])
        }

    }


  const onResetCallback = async () => {
    setGridState({
      charts: [],
      columns: masterUIConfig,
      pivot: false,
    })
  }

  const CustomHeader = {
    dailydatagraph: {
      width: 45,
      minWidth: 45,
      filter: false,
      cellRenderer: 'grapCellRenderer',
      cellRendererParams: { onOpenDailyDataGraph: onOpenDailyDataGraph },
      pinned: 'left',
      lockPosition: true,
      resizable: false,
      floatingFilter: false,
      suppressColumnsToolPanel: false,
      suppressMenu:true,
      headerTooltip: "Daily Data Graph",
      headerName:"Daily Data Graph",
      sortable: false,
    },
    remarks: {
      cellStyle: {
        backgroundColor: 'white',
        border: '1px solid #b9bdba',
        color: 'black',
        padding: '1px'
      },
      pinned: 'right',
      editable: true,
      minWidth: 130,
      maxWidth: 160,
      lockPosition: 'right',
      menuTabs: [],
      suppressMenu: true,
      resizable: false,
      floatingFilter: false,
    },
    rh: {
      cellRenderer: 'remarksCellRenderer',
      cellRendererParams: {
        onClick: onOpenRemarkHistory
      },
      pinned: 'right',
      minWidth: 120,
      maxWidth: 120,
      lockPosition: 'right',
      menuTabs: [],
      suppressMenu: true,
      resizable: false,
      floatingFilter: false,
    },
  }

    const getSupplierWiseAllocationUIConfig = async()=>{
      try{
        const response = await getUiConfig(UIColumnConfigName.SupplierWiseAllocation);
          setInitialColumnState(response.data.data);
      }catch(err:any){
          notifyError("Something Went Wrong")
      }
  }

    const onApplyFilter = async(filter:any)=>{
      await getRecordsCount(filter)
      await loadGridData(1,filter)
      setCurrFilter(filter)
      setCurrentPage(1)
    }

    const onDeleteFilter = async(parentId:any, filterId:any, value:any)=>{
      const updatedFilter = onDelete(parentId,filterId,value)
      onApplyFilter(updatedFilter)
  }

    
    const defaultColDefObject = useMemo(()=>{
      return {
          floatingFilter: true,
          cellStyle:{
              "flex":1,
              'textAlign':'center',
              'height':'50px',
              "fontStyle":"normal",
              "display":"block",
              'textOverflow':'ellipsis',
              'whiteSpace':'nowrap'
          },
      }
    },[])


     const agGridProps:AgGridReactProps = useMemo(()=>{
      return {
        tooltipShowDelay:0,
        tooltipTrigger:"focus",
        readOnlyEdit:false,
        suppressRowClickSelection:true,
        components:customCellRenderers,
        enableBrowserTooltips:true,
        getMainMenuItems: MainMenuItemsCustomization,
        paginationPageSize:parseInt(SUPPLY_WISE_ALLOCATION_HUB_ROWS_PER_PAGE || '100'),
        gridOptions:{
            rowHeight:50,
            getRowStyle: (params: any) => {
            if (params.node.rowIndex % 2 === 0) {
                return { background: "#EBEBEB" };
            }
            return { background: "#F7F7F7" };
            },
            getRowId: (params) => {
              return `${params.data.SKUCode}-${params.data.WhCode}-${params.data.SupplierCode}`
          },
        },
         pagination:false,
         sideBar:defaultAgGridSideBarForBPR,
        // pivotMode:true,
         defaultColDef:defaultColDefObject,
        onGridReady:(params)=>setInternalRef(params),
        onCellValueChanged:(params)=>onCellValueChanged(params.data,"SKUCode","WhCode","SupplierCode")
      }
     },[])

      const getBORRowData=async(filter:BPRFilterState)=>{
        if(filter)setCurrFilter(filter)
        try{
            if(recordCount===0 || filter){
                await getRecordsCount(filter)
                setCurrGridPage(currGridPage)
            }

            await loadGridData(currentPage,filter)
         }
       catch(err:any){
            notifyError(err)
        }
    }

      const tempAgGridProps:AgGridReactProps = {
          onRowDataUpdated:(event)=>{
            if(tempDownloadData) event?.api?.exportDataAsExcel({fileName:'SupplierWiseAllocationReport',columnKeys:ref.current?.api.getAllDisplayedColumns().map((c)=>c.getColId())});
           }
        }

      const onExportToExcelCallBack=async(pageNumber:number)=>{
        const data =  await getData({
            filters:currFilter,
            paginationParameter:{
                pageNumber:pageNumber,
                recordsPerPage:5000
            }
        })
        
        return data.data.data
    }

    const onSubmitRemarks = async()=>{
          try{
            if(editedRows.length===0){
              notifyError('Please add remarks/remark to save')
              return
            }
          const toastId = notifyLoader("Submitting Remark")
          const payload = editedRows.map((e)=>{
              return {
                remark:e.remarks,
                whcode:e.WhCode || e.WHCode,
                skucode:e.SKUCode,
                spc:e.SupplierCode
              }
              
          })
          const {data} = await submitRemark({data:payload})
          editedRows.forEach((editedRow) => {
            // Find the row node using both SKUCode and WHCode as unique identifiers
            const rowNode:any = ref.current?.api.getRowNode(`${editedRow.SKUCode}-${editedRow.WhCode}-${editedRow.SupplierCode}`);
            if (rowNode) {
              const RemarkColumn = BORCBColumns.find(obj => obj.colId === "Remark");
              if(rowNode?.data?.Remark!==undefined && RemarkColumn!==undefined){
                // Check if Remark column exist in both columnDef and RowData , only then update its value for better ui
                rowNode?.setDataValue('Remark', editedRow?.remarks);
              }
              rowNode.setDataValue('Remark', editedRow.remarks);
      
              // Clear the 'Edit Remarks' column after submission
              rowNode.setDataValue('remarks', '');
            }
          });
           toast.dismiss(toastId)
           notifySuccess(data.msg)
           setEditedRows([])
          }catch(err:any){
           notifyError(err.message)
          }
       }

      const generalFilterOptions = useMemo(()=>{
        if(BORCBColumns.length!==0){
          return convertUiConfigToOptions(BORCBColumns)
        }
      }, [BORCBColumns])

      const savePageSize = async( pageSize:number)=>{
        setUserPageSize(pageSize)
        await loadGridData(currentPage,currFilter ,pageSize)
      await getRecordsCount(currFilter , pageSize)
    }
     return {   
        ref,    
        isLoading :isUIConfigLoading || isDataLoading || isCountLoading,      
        BORCBColumns,
        agGridProps,
        rowData ,
        currentPage,
        rowsPerPage,
        recordCount,
        gridState,
        isSavedDataLoading,
        handleChangePage,
        tempRef,
        tempDownloadData,
        setTempDownloadData,
        tempAgGridProps,
        exportExcelRowData,
        setExportExcelRowData,
        exportExcelColumns,
        setExportExcelColumns,
        onExportToExcelCallBack,
        showDailyDataGraphModal,
        showNormChangeHistoryTable,
        dailyData,
        getBORRowData,
        onApplyFilter,
        currFilter,
        setCurrFilter,
        onDeleteFilter,
        generalFilterOptions,
        onSubmitRemarks,
        editedRows,
        onResetCallback,
        lastRunDate,
        isRemarkHistoryToolTipOpen,
        setIsRemarkHistoryToolTipOpen,
        remarkHistory,
        onCloseRemarkHistory,
        savePageSize,
        userPageSize
    }
}
