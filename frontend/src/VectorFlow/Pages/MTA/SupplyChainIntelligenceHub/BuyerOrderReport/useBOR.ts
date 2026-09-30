import { useBORData, useBORDataCount,useSubmitBORRemark,useGetBORRemarkHistory } from "../../../../Services/MTA/SupplyChainIntelligenceHub/BuyerOrderReport"
import {useGetDailyData} from '../../../../Services/MTA/SupplyChainIntelligenceHub/BPR'
import { convertUiConfigToOptions, MainMenuItemsCustomization, getColumnDefinationsMTA , CsvExportMTA } from "../../../../../helpers/utils"
import { useState,useMemo, useEffect,useRef, CSSProperties } from "react"
import { AgGridReactProps } from "ag-grid-react"
import {DispatchColorCellRenderer} from "./CellRenderer"
import BPRGraphCellRenderer from "../../../../Pages/MTA/SupplyChainIntelligenceHub/BPR/BPRGraphCellRenderer"
import { BPRFilterState } from "../../../../../VectorFlow/types/BPR"

import { useSelector,useDispatch } from "react-redux"

import { RootState } from "../../../../../redux/store/store"
import {TOGGLE_GRAPH_MODAL,UPDATE_DAILY_DATA} from '../../../../../redux/actions/MTA';
import { type DailyDataGraph } from "../../../../types/MTA";
import { notifyError, notifyLoader,notifySuccess} from "../../../../../helpers/notify"
import { toast } from "react-toastify"

import useBPRFilter from "../../../../../hooks/useBPRFilter";
import { defaultAgGridSideBarForBPR } from "../../../../../helpers/BPRConstants";
import { GridRef } from "../../../../../VectorFlow/types/MDM"
import {  BPRSubmitRemarkCellRenderer } from "../BPR/BPRCellRenderers"
import useViewPort from "../../../../../hooks/useViewPort"
import { BORRemarksCellRenderer } from "./BORCellRenderers"
import useGetLastRunData from "../../../../../hooks/useGetLastRunData"
import { useGetUIConfigData } from "../../../../Services/MTA/Common/UIConfig";
import { UIColumnConfigName, UserUIColumnConfigName } from "../../../../../helpers/Enum"
import { useGetState } from "../../../../Services/MTA/Common/UserUIConfig"


export const useBOR =()=>{
    const ref=  useRef<GridRef>()
    const tempRef = useRef<GridRef>()

    const [internalRef,setInternalRef] = useState<any>()

    const {state:currFilter,setState:setCurrFilter,onDelete} = useBPRFilter()

  const { mutateAsync: getUiConfig, isLoading: isUIConfigLoading } = useGetUIConfigData();
  
     const dispatch = useDispatch();
   
     const {getGridZoom,getScreenZoomValue} = useViewPort()
 
     const gridZoom = getGridZoom()
     const screenZoom = getScreenZoomValue() 

    //  const [toggleSubGrid] = useState<boolean>(false);
     const [currGridPage,setCurrGridPage] = useState<number>(1)

     const [rowData,setRowData] = useState([]);

     const [BORColumns,setBORColumns] = useState<any[]>([])

     const [recordCount,setRecordCount] = useState<number>(0)
     const [currentPage,setCurrentPage] = useState(1);

     const [tempDownloadData,setTempDownloadData] = useState<boolean>(false);

     const [exportExcelColumns,setExportExcelColumns] = useState<Array<any>>([])
 
     const [exportExcelRowData,setExportExcelRowData] = useState<Array<any>>([])
     const [generalFilterOptions,setGeneralFilterOptions] = useState();

     const [isSubmitRemarkToolTipOpen,setIsSubmitRemarkToolTipOpen] = useState<boolean>(false)
     const [submitRemarkToolTipPosition,setSubmitRemarkToolipPosition] = useState<CSSProperties>({})
     const [isRemarkHistoryToolTipOpen,setIsRemarkHistoryToolTipOpen] = useState<boolean>(false)
     const [remarkHistoryToolipPosition,setRemarkHistoryToolipPosition] = useState<CSSProperties>({})
     const {mutateAsync:getBORRemarkHistory} = useGetBORRemarkHistory();
     const [remarkHistory,setRemarkHistory] = useState<any[]>([])
     const [editedRows,setEditedRows] = useState<Array<any>>([])
     const [remark,setRemark] = useState<string>('')

     const columnsNotToBeIncluded = ['remarks','rh','dailydatagraph']

     const {mutateAsync:submitRemark} = useSubmitBORRemark()
     const {date:lastRunDate} = useGetLastRunData()




     const showDailyDataGraphModal = useSelector((state:RootState) => state.mta.showDailyDataGraphModal);
     const showNormChangeHistoryTable = useSelector((state:RootState) => state.mta.showNormChangeHistoryTable);
     const dailyData = useSelector((state:RootState) => state.mta.dailyData);
    //  const rowsPerPage=50;
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const BOR_ROWS_PER_PAGE = EnvConfig['BOR_ROWS_PER_PAGE'];   
     const rowsPerPage = parseInt(BOR_ROWS_PER_PAGE || '100');
    const [userPageSize , setUserPageSize]  = useState<number>(BOR_ROWS_PER_PAGE?parseInt(BOR_ROWS_PER_PAGE):50)  
     const handleChangePage = async (pageNo:any) => {
         setCurrentPage(pageNo);
         loadGridData(pageNo,currFilter);
      }


     const {mutateAsync:getBorData, isLoading: isBORDataLoading} = useBORData();
     const {mutateAsync:getBorDataCount, isLoading: isBORCountLoading} = useBORDataCount();
     const {mutateAsync:getDailyData} = useGetDailyData();

     const customCellRenderers = useMemo(() => ({
        grapCellRenderer:BPRGraphCellRenderer,
        colorDispatchCellRenderer:DispatchColorCellRenderer,
        submitRemarkCellRenderer:BPRSubmitRemarkCellRenderer,
        remarksCellRenderer:BORRemarksCellRenderer

        
      }), []);

      const onOpenDailyDataGraph = async (params:any) => {
        const payload:any = {
            SKUCode:params.data['SKUCode'],
            WHCode:params.data['WHCode']
        }
        const result = await getDailyData(payload)
        const data = result.data.data[0];
        const dailyData:DailyDataGraph = {
            rowData:params.data,
            chartData:data['StockData'],
            normChangeData:data['NormChangeHistoryData'],
            masterData:data['MasterData'][0],
            suggestionData:data['SuggestionHistoryData'] ? data['SuggestionHistoryData'] : [],
            monitoringData:data['MonitoringData']
        }
  
        dispatch(UPDATE_DAILY_DATA(dailyData));
        dispatch(TOGGLE_GRAPH_MODAL(true));
    }

    const onOpenSubmitRemark = (e:React.MouseEvent<HTMLElement>)=>{
      const {top,left} = e.currentTarget.getBoundingClientRect()
      setSubmitRemarkToolipPosition({
          top: top * gridZoom * screenZoom,
          left: left * gridZoom * screenZoom,
      })
      setIsSubmitRemarkToolTipOpen(true)

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
        const {data} = await getBORRemarkHistory(row)
        toast.dismiss(toastId)
        setRemarkHistory(data.data)
        setIsRemarkHistoryToolTipOpen(true)
    }catch(err:any){
        notifyError(err.message)
    }
    }

    // const onCellValueChanged = (newRow: any, primaryKey: string) => {
    //   console.log('ghsuiag')
    //   setEditedRows((prev:any) => {
    //     let found = false; // Flag to track if the row has been updated
    //     const updatedRows = prev.map((row:any) => {
    //       if (row[primaryKey] === newRow[primaryKey]) {
    //         found = true;
    //         return { ...newRow }; // Return updated row
    //       }
    //       return row; // Return unchanged row
    //     });
    
    //     if (!found) {
    //       // If no existing row was found, add the new row
    //       return [...updatedRows, {...newRow}];
    //     }
    //     return updatedRows;
    //   });
    // };

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
              whcode:e.WHCode,
              skucode:e.SKUCode,
              spc:e.SupplierCode
          }
          
      })
      const {data} = await submitRemark({data:payload})
      editedRows.forEach((editedRow) => {
          // Find the row node using both SKUCode and WHCode as unique identifiers
          const rowNode:any = ref.current?.api.getRowNode(`${editedRow.SKUCode}-${editedRow.WHCode}-${editedRow.SupplierCode}`);
          if (rowNode) {
            const RemarkColumn = BORColumns.find(obj => obj.colId === "Remark");
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

   const onCloseSubmitRemark =()=>setIsSubmitRemarkToolTipOpen(false)

   const onCloseRemarkHistory = ()=>setIsRemarkHistoryToolTipOpen(false)

   const updateRemark = (e:any)=>setRemark(e.currentTarget.value)
 
  // const BORColumns = useMemo(()=>mapBORFieldsToColDefs(data?.data.data,onOpenDailyDataGraph,onOpenSubmitRemark, onOpenRemarkHistory),[data])

      // const BORColumnData = useMemo(() => {
      //     return mapBORFieldsToColDefs(
      //           data?.data?.data, 
      //           onOpenSubmitRemark, 
      //           onOpenRemarkHistory, 
      //           onOpenDailyDataGraph
      //     );
      //   }, [data]);
      //       // Update columns state only if there is a change
      //   useEffect(() => {
      //     console.log("DAAATAAAAA",data?.data.data)
      //     console.log("BOOORRRCOLUMNNN",BORColumnData)
      //         // Check if the columns data has changed before setting state
      //     setBORColumns(BORColumnData);
      //   }, [BORColumnData, setBORColumns]); 


  const { mutateAsync: getState, isLoading: isSavedDataLoading } = useGetState();
      const [gridState,setGridState] = useState<any>()
  const [initialColumnState, setInitialColumnState] = useState<any>(undefined);
  const [masterUIConfig, setMasterUIConfig] = useState<any>([]);

  // useEffect(() => {
  //   fetchData();
  //   getBORUiConfig();
  // }, []);

  const fetchData = async () => {
    await getRecordsCount();
    await loadGridData(currentPage);
  };
      
  const getBORUiConfig = async () => {
    try {
      const response = await getUiConfig(UIColumnConfigName.BOR);
      setInitialColumnState(response.data.data);
    } catch (err: any) {
      notifyError("Something Went Wrong")
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
        setBORColumns(MappedColumns);
        getUserColumnConfig();
      } catch (err: any) {
        console.log(err)
      }
    }
    if (initialColumnState !== undefined) {
      getTableState();
      setGeneralFilterOptions(convertUiConfigToOptions(initialColumnState));
    }
  }, [initialColumnState]);

  useEffect(() => {
    if (BORColumns.length) {
      if (internalRef?.api) {
        setMasterUIConfig(internalRef.api.getColumnState());
      }
    }
  }, [internalRef, BORColumns]);
      
  const getUserColumnConfig = async () => {
    const stateData = await getState({ "reportname": UserUIColumnConfigName.BOR })
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

    const onColumnVisible = (event: any) => {
      const { column, visible , columns } = event;
      // console.log(column)
      // Optionally, you can update your state if needed (like in a sidebar with checkboxes)
      if(column!==null && column.colId!=="dailydatagraph" && event.source==='toolPanelUi'){
      setBORColumns((prevColumns:any) =>{
          const updatedColumns = prevColumns.map((col: any) =>
              col.field === column.colId
                ? { ...col, hide: !visible }
                : col
            );
          
            // Check if any columns, except the one with colId === "dailydatagraph", have hide: false
            const anyColumnWithHideFalse = updatedColumns.some(
              (col: any) => col.colId !== "dailydatagraph" && col.hide === false
            );
          
            // Now map over the updated columns and ensure dailydatagraph's hide is updated accordingly
            return updatedColumns.map((col: any) =>
              col.colId === "dailydatagraph"
                ? { ...col, hide: anyColumnWithHideFalse ? false : col.hide }
                : col
            );
      }
      );
      }else if(columns.length>1 && event.source==='toolPanelUi'){
          setBORColumns((prevColumns: any) => {
              // Create a new array with updated columns, excluding 'dailydatagraph
              if(visible===true){
                  return  prevColumns.map((col: any) => ({ ...col, hide: false }))
              }else{
                  const updatedColumns = prevColumns.map((col: any) =>
                      col.colId === "dailydatagraph"
                        ? col // Exclude this column for now
                        : col.field === columns.find((column: any) => column.colId === col.colId)?.colId
                        ? { ...col, hide: !visible }
                        : col
                    );
                  
                    // Check if all columns except 'dailydatagraph' have `hide: true`
                    const allHidden = updatedColumns.every(
                      (col: any) => col.colId === "dailydatagraph" || col.hide
                    );
                  
                    // Update 'dailydatagraph' column's `hide` property if all others are hidden
                    return updatedColumns.map((col: any) =>
                      col.colId === "dailydatagraph" && allHidden ? { ...col, hide: true } : col
                    );
              }
            });
            
          // setBPRColumns((prevColumns:any) =>
          //     prevColumns.map((col: any) =>
          //         col.colId === "dailydatagraph"
          //         ? col // Exclude this column from being updated
          //         : col.field === columns.find((column: any) => column.colId === col.colId)?.colId
          //         ? { ...col, hide: !visible }
          //         : col
          //       )              
          //   );
      }
    };


      const getRecordsCount=async(filter?:any)=>{
            const payload={
            filters:filter || {},
             paginationParameter: {
        pageNumber: currentPage,
        // recordPerPage:20
    recordsPerPage: parseInt(BOR_ROWS_PER_PAGE || '100')
    }
        }
        const resultCount=await getBorDataCount(payload);
        setRecordCount(resultCount?.data?.recordCount);
      }
    
    const loadGridData = async (pageNo:any,filter?:any , pageSize?:any)=> {

      try {
        
          notifyLoader("loading Grid Data")
          const payload={
            filters:filter || {},
            paginationParameter:{pageNumber:pageNo,recordsPerPage:pageSize || userPageSize ||rowsPerPage || 100}
        }
        const result = await getBorData(payload);
        setRowData(result.data.data || [])
        toast.dismiss()
        notifySuccess("Data Loaded Successfully")
        }catch(err:any){
          notifyError(err)
          setRecordCount(0)
          setRowData([])
        }

    }

    const onApplyFilter = async(filter:any)=>{
      await getBORUiConfig();
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
        enableFillHandle: true,
        getMainMenuItems: MainMenuItemsCustomization,
        paginationPageSize:parseInt(BOR_ROWS_PER_PAGE || '100'),
        gridOptions:{
            rowHeight:50,
            getRowStyle: (params: any) => {
            if (params.node.rowIndex % 2 === 0) {
                return { background: "#EBEBEB" };
            }
            return { background: "#F7F7F7" };
            },
            // onColumnVisible: onColumnVisible,
          //   onColumnMoved: (event:any) => {
          //     const columnState = event.api.getColumnState();
          //     columnState.forEach((state:any) => {
          //       if (state.pinned && (state.colId!=='remarks' && state.colId!=='rh')) {
          //         // Reset the pin to null
          //         state.pinned = null;
          //       }
          //     });
          //     event.api.applyColumnState({ state: columnState });
          // },
          getRowId: (params) => {
              return `${params.data.SKUCode}-${params.data.WHCode}-${params.data.SupplierCode}`
          },
        },
         pagination:false,
         sideBar:defaultAgGridSideBarForBPR,
        // pivotMode:true,
         defaultColDef:defaultColDefObject,
        // onGridReady:(params)=>setInternalRef(params)
        onCellValueChanged:(params)=>onCellValueChanged(params.data,"SKUCode","WHCode","SupplierCode"),
        onGridReady:(params)=>setInternalRef(params)
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

      const tempAgGridProps:AgGridReactProps = useMemo(() => {
        return {
        onRowDataUpdated:(event)=>{
          const columnsToBeIncluded = ref.current?.api.getAllDisplayedColumns().map((c)=>c.getColId()).filter((key:string)=>!columnsNotToBeIncluded.includes(key));
          if(tempDownloadData){
            event?.api?.exportDataAsExcel({fileName:'BuyerOrderReport',columnKeys:columnsToBeIncluded});
            setTempDownloadData(false)
          }
        }
      }
    },[ref,tempDownloadData])

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
          reportName:"BOR",
          stream:1,
          responseType: `arraybuffer`
      }
      notifyLoader("Downloading Data...")
      try {
          await CsvExportMTA(payload, "BuyerOrderReport");
          notifySuccess(`Data Exported Successfully`);
      }
      catch(error) {
          console.log(error);
          notifyError("Error Exporting Excel")
          throw error;
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
  
    const savePageSize = async( pageSize:number)=>{
        setUserPageSize(pageSize)
        await loadGridData(currentPage,currFilter, pageSize);
    }
     return {   
        ref,    
        isLoading :isUIConfigLoading || isBORDataLoading || isBORCountLoading,      
        BORColumns,
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
        isSubmitRemarkToolTipOpen,
        isRemarkHistoryToolTipOpen,
        remarkHistory,
        remark,
        submitRemarkToolTipPosition,
        remarkHistoryToolipPosition,
        onSubmitRemarks,
        editedRows,
        updateRemark,
        onCloseRemarkHistory,
        onCloseSubmitRemark,
        onResetCallback,
       lastRunDate,
       savePageSize,
        userPageSize

    }
}
