import { useState,useMemo, useEffect, CSSProperties,useRef } from "react"
import { AgGridReactProps } from "ag-grid-react"

import { useGetBPRData, useGetBPRRemarkHistory, useSubmitBPRRemark, useGetDailyData, useGetBPRDataCount } from "../../../../Services/MTA/SupplyChainIntelligenceHub/BPR"
import { BPREcoColorCellRenderer,BPRRemarksCellRenderer,BPRSubmitRemarkCellRenderer,BPRTagsCellRenderer,BPRTechColorCellRenderer } from "./BPRCellRenderers"
import { convertUiConfigToOptions, mapBPRRowData, MainMenuItemsCustomization, getColumnDefinationsMTA, CsvExportMTA } from "../../../../../helpers/utils"
import { notifyError, notifyLoader, notifySuccess } from "../../../../../helpers/notify"
import { toast } from "react-toastify"
import BPRGraphCellRenderer from "./BPRGraphCellRenderer"
import useViewPort from "../../../../../hooks/useViewPort"
import type { RootState } from '../../../../../redux/store/store';
import { useSelector, useDispatch } from 'react-redux';
import {TOGGLE_GRAPH_MODAL,UPDATE_DAILY_DATA} from '../../../../../redux/actions/MTA';
import { type DailyDataGraph } from "../../../../types/MTA";
import useBPRFilter from "../../../../../hooks/useBPRFilter"
import { useUserData } from "../../../../../context"
// import _ from 'lodash'
import { defaultAgGridSideBarForBPR } from "../../../../../helpers/BPRConstants";
import useGetLastRunData from "../../../../../hooks/useGetLastRunData"
import { GridRef } from "../../../../../VectorFlow/types/MDM"
import { getBPRDataForExcelDownload } from "../../../../Services/MTA/SupplyChainIntelligenceHub/BPR/api"
import { useGetUIConfigData } from "../../../../Services/MTA/Common/UIConfig"
import { UIColumnConfigName, UserUIColumnConfigName } from "../../../../../helpers/Enum"
import { useGetState } from "../../../../Services/MTA/Common/UserUIConfig"
import _ from "lodash"


const useBPR =()=>{

    const ref = useRef<GridRef>()
    const tempRef = useRef<GridRef>()

    const [internalRef,setInternalRef] = useState<any>()

    const {getGridZoom,getScreenZoomValue} = useViewPort()
    const dispatch = useDispatch();

    const gridZoom = getGridZoom()
    const screenZoom = getScreenZoomValue() 

    const {user} = useUserData()
    const themeUi = user.user.theme_ui

    const showDailyDataGraphModal = useSelector((state:RootState) => state.mta.showDailyDataGraphModal);
    const showNormChangeHistoryTable = useSelector((state:RootState) => state.mta.showNormChangeHistoryTable);
    const dailyData = useSelector((state:RootState) => state.mta.dailyData);

    const [editedRows,setEditedRows] = useState<Array<any>>([])

    const [isSubGridOpen,toggleSubGrid] = useState<boolean>(true)
    const [currGridPage,setCurrGridPage] = useState<number>(1)
    const [recordCount,setRecordCount] = useState<number>(0)
    const [activeRow,setActiveRow] = useState<any>()
    const [BPRRowData,setBPRRowData] = useState<any[]>([])
    const [BPRColumns,setBPRColumns] = useState<any[]>([])


    const [submitRemarkToolTipPosition,setSubmitRemarkToolipPosition] = useState<CSSProperties>({})
    const [remarkHistoryToolipPosition,setRemarkHistoryToolipPosition] = useState<CSSProperties>({})

    const [isSubmitRemarkToolTipOpen,setIsSubmitRemarkToolTipOpen] = useState<boolean>(false)
    const [isRemarkHistoryToolTipOpen,setIsRemarkHistoryToolTipOpen] = useState<boolean>(false)
   
    const [remark,setRemark] = useState<string>('')

    const {state:currFilter,setState:setCurrFilter,onDelete} = useBPRFilter()

    const [tempDownloadData,setTempDownloadData] = useState<boolean>(false);

    const [exportExcelColumns,setExportExcelColumns] = useState<Array<any>>([])

    const [exportExcelRowData,setExportExcelRowData] = useState<Array<any>>([])

    const [remarkHistory,setRemarkHistory] = useState<any[]>([])
  
    const { mutateAsync: getUiConfig, isLoading: isUIConfigLoading, isError } = useGetUIConfigData();
   
    const {date:lastRunDate} = useGetLastRunData()
    
    const {mutateAsync:getBPRData,isLoading:isRowDataLoading} = useGetBPRData()

    const {mutateAsync:submitRemark} = useSubmitBPRRemark()

    const {mutateAsync:getRemarkHistory} = useGetBPRRemarkHistory()

    const {mutateAsync:getDailyData} = useGetDailyData();

    const {mutateAsync:getBPRDataCount,isLoading:isBPRDataCountLoading} = useGetBPRDataCount()

    const { mutateAsync: getState, isLoading: isSavedDataLoading } = useGetState();
    
    const [gridState,setGridState] = useState<any>()
    const [generalFilterOptions,setGeneralFilterOptions] = useState();
    const columnsNotToBeIncluded = ['remarks','rh','dailydatagraph']
    const [initialColumnState, setInitialColumnState] = useState<any>(undefined);
    const [masterUIConfig, setMasterUIConfig] = useState<any>([]);
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const BPR_ROWS_PER_PAGE = EnvConfig['BPR_ROWS_PER_PAGE']; 
    const [userPageSize , setUserPageSize]  = useState<number>(BPR_ROWS_PER_PAGE?parseInt(BPR_ROWS_PER_PAGE):50)   
    // useEffect(() => {   
    //     getInitialBPRRowData()
    //     getBPRUiConfig();
    // }, []);
    
    const getBPRUiConfig = async () => {
        try {
            const response = await getUiConfig(UIColumnConfigName.BPR);
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
                setBPRColumns(MappedColumns);
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
        if (BPRColumns.length) {
            if (internalRef?.api) {
                setMasterUIConfig(internalRef.api.getColumnState());
            }
        }
    }, [internalRef, BPRColumns]);
    
    const getUserColumnConfig = async () => {
        const stateData = await getState({ "reportname": UserUIColumnConfigName.BPR })
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

    useEffect(()=>{
        if (internalRef && gridState && gridState.columns) {
            const result = internalRef?.api.applyColumnState({ state: gridState.columns, applyOrder: true });
            internalRef?.api.sizeColumnsToFit();
            if (!result) {
                console.error("Failed to apply column state", result);
            }
        }
    },[internalRef,gridState])

    const customCellRenderers = useMemo(() => ({
        grapCellRenderer:BPRGraphCellRenderer,
        colorTechCellRenderer:BPRTechColorCellRenderer,
        colorEcoCellRenderer:BPREcoColorCellRenderer,
        tagsCellRenderer:BPRTagsCellRenderer,
        submitRemarkCellRenderer:BPRSubmitRemarkCellRenderer,
        remarksCellRenderer:BPRRemarksCellRenderer
      }), []);


    //   const onColumnVisible = (event: any) => {
    //     const { column, visible , columns } = event;
    //     // console.log(column)
    //     // Optionally, you can update your state if needed (like in a sidebar with checkboxes)
    //     if(column!==null && column.colId!=="dailydatagraph" && event.source==='toolPanelUi'){
    //     setBPRColumns((prevColumns:any) =>{
    //         const updatedColumns = prevColumns.map((col: any) =>
    //             col.field === column.colId
    //               ? { ...col, hide: !visible }
    //               : col
    //           );
            
    //           // Check if any columns, except the one with colId === "dailydatagraph", have hide: false
    //           const anyColumnWithHideFalse = updatedColumns.some(
    //             (col: any) => col.colId !== "dailydatagraph" && col.hide === false
    //           );
            
    //           // Now map over the updated columns and ensure dailydatagraph's hide is updated accordingly
    //           return updatedColumns.map((col: any) =>
    //             col.colId === "dailydatagraph"
    //               ? { ...col, hide: anyColumnWithHideFalse ? false : col.hide }
    //               : col
    //           );
    //     }
    //     );
    //     }else if(columns.length>1 && event.source==='toolPanelUi'){
    //         setBPRColumns((prevColumns: any) => {
    //             // Create a new array with updated columns, excluding 'dailydatagraph
    //             if(visible===true){
    //                 return  prevColumns.map((col: any) => ({ ...col, hide: false }))
    //             }else{
    //                 const updatedColumns = prevColumns.map((col: any) =>
    //                     col.colId === "dailydatagraph"
    //                       ? col // Exclude this column for now
    //                       : col.field === columns.find((column: any) => column.colId === col.colId)?.colId
    //                       ? { ...col, hide: !visible }
    //                       : col
    //                   );
                    
    //                   // Check if all columns except 'dailydatagraph' have `hide: true`
    //                   const allHidden = updatedColumns.every(
    //                     (col: any) => col.colId === "dailydatagraph" || col.hide
    //                   );
                    
    //                   // Update 'dailydatagraph' column's `hide` property if all others are hidden
    //                   return updatedColumns.map((col: any) =>
    //                     col.colId === "dailydatagraph" && allHidden ? { ...col, hide: true } : col
    //                   );
    //             }
    //           });
              
    //         // setBPRColumns((prevColumns:any) =>
    //         //     prevColumns.map((col: any) =>
    //         //         col.colId === "dailydatagraph"
    //         //         ? col // Exclude this column from being updated
    //         //         : col.field === columns.find((column: any) => column.colId === col.colId)?.colId
    //         //         ? { ...col, hide: !visible }
    //         //         : col
    //         //       )              
    //         //   );
    //     }
    //   };


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
        
            suppressRowTransform:true,
            // rowSelection:'single',
            readOnlyEdit:false,
            enableColResize: true,
            sideBar:defaultAgGridSideBarForBPR,
            getMainMenuItems: MainMenuItemsCustomization,
            enableFillHandle: true,
            rowSelection:"single",
            paginationPageSize:parseInt(BPR_ROWS_PER_PAGE || '50'),
            onRowSelected:(params:any)=>{
                if(params.data.intransit && params.data.intransit.length>0){
                    setActiveRow(JSON.parse(params.data.intransit))
                    toggleSubGrid(true)
                }
            },
            gridOptions:{
                rowHeight:50,
                getRowStyle: (params: any) => {
                if (params.node.rowIndex % 2 === 0) {
                    return { background: "#EBEBEB" };
                }
                return { background: "#F7F7F7" };
                },
                // onColumnVisible: onColumnVisible,
                getRowId: (params) => {
                    return `${params.data.SKUCode}-${params.data.WHCode}`
                },
            },
            // suppressRowClickSelection:true,
            components:customCellRenderers,
            defaultColDef:defaultColDefObject,
            onCellValueChanged:(params)=>onCellValueChanged(params.data,"SKUCode","WHCode"),
            onGridReady:(params)=>setInternalRef(params),
            // autoSizeStrategy:{
            //     type:"fitCellContents"
            // }
        }
    },[])

    
    const tempAgGridProps:AgGridReactProps = useMemo(()=>{
        return {
        onRowDataUpdated:(event)=>{
            const columnsToBeIncluded = ref?.current?.api.getAllDisplayedColumns().map((c)=>c.getColId()).filter((key:string)=>!columnsNotToBeIncluded.includes(key));
            if(tempDownloadData){
                event?.api?.exportDataAsExcel({fileName:'BufferPenetrationReport',columnKeys:columnsToBeIncluded})
                setTempDownloadData(false)
            }
        }
    }
    },[ref,tempDownloadData])


      const getInitialBPRRowData=async()=>{
          try {    
            await getBPRRecordCount(currFilter)
            await getBPRRowData(currFilter,1)
        }catch(err:any){
            notifyError(err)
        }
    }

    const getBPRRecordCount = async(filter:any)=>{
        const countData = await getBPRDataCount({
            id: 1,
            name: "",
            fields: [],
            filters:filter,
            paginationParameter:{
                pageNumber:currGridPage,
                recordsPerPage:parseInt(BPR_ROWS_PER_PAGE || '50') 
            }
        })

        setRecordCount(countData.data.recordCount)
    }

    const onCellValueChanged = (newRow: any, primaryKey1: string,primaryKey2:string) => {
        setEditedRows((prev) => {
          let found = false; // Flag to track if the row has been updated
          const updatedRows = prev.map((row) => {
            if (row[primaryKey1] === newRow[primaryKey1] && row[primaryKey2]===newRow[primaryKey2]) {
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

    const getBPRRowData = async(filter:any,pageNo:number , pageSize?:number)=>{
        notifyLoader("Loading Grid Data")
        const rowData =await  getBPRData({
            id: 1,
            name: "",
            fields: [],
            filters:filter,
            paginationParameter:{
                pageNumber:pageNo,
                recordsPerPage:pageSize || userPageSize || parseInt(BPR_ROWS_PER_PAGE || '50') 
            }
        })
        toast.dismiss()
        notifySuccess("Data Loaded Successfully")
        if(rowData.data.data && Array.isArray(rowData.data.data))setBPRRowData(mapBPRRowData(rowData.data.data))
        else setBPRRowData([])
        
    }



    const updateRemark = (e:any)=>setRemark(e.currentTarget.value)
    

    // const onSubmitRemark = async()=>{
        
    //     try{
    //         if(remark.length===0) throw new Error("Remark cannot be empty")
    //         const toastId = notifyLoader("Submitting Remark")
    //         const {data} = await submitRemark({
    //             remark:remark,
    //             whcode:submitRemarkData.whcode,
    //             skucode:submitRemarkData.skucode
    //         })
    //         toast.dismiss(toastId)
    //         // if(data.status!==200)notifyError('Something went wrong')
            
    //         notifySuccess(data.msg)
    //         setRemark('')
            
    //         setIsSubmitRemarkToolTipOpen(false)
    //     }catch(err:any){
    //         notifyError(err.message)
    //     }
    // }

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
                 skucode:e.SKUCode
             }
            
         })
         const {data} = await submitRemark({data:payload})
         editedRows.forEach((editedRow) => {
             // Find the row node using both SKUCode and WHCode as unique identifiers
             const rowNode:any = ref.current?.api.getRowNode(`${editedRow.SKUCode}-${editedRow.WHCode}`);
             if (rowNode) {
                 const RemarkColumn = BPRColumns.find(obj => obj.colId === "Remark");
                 if(rowNode?.data?.Remark!==undefined && RemarkColumn!==undefined){
                    //  rowNode?.setDataValue('Remark', editedRow?.remarks);
                    const updatedData = { ...rowNode.data };
                    updatedData.Remark = editedRow?.remarks;
                    rowNode.setData(updatedData);
                 }
               rowNode?.setDataValue('remarks', '');
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
            const {data} = await getRemarkHistory(row)
            toast.dismiss(toastId)
            setRemarkHistory(data.data)
            setIsRemarkHistoryToolTipOpen(true)
        }catch(err:any){
            notifyError(err.message)
        }
    }

    const onOpenDailyDataGraph = async (params:any) => {
        const payload:any = {
            SKUCode:params.data['SKUCode'],
            WHCode:params.data['WHCode']
        }
        const result = await getDailyData(payload)
        const data = result.data.data[0];
        const dailyData:DailyDataGraph = {
            rowData:_.cloneDeep(params.data) || [],
            chartData:data['StockData'] || [],
            normChangeData:data['NormChangeHistoryData'] || [],
            masterData:data['MasterData']?.[0] || [],
            suggestionData:data['SuggestionHistoryData'] ? data['SuggestionHistoryData'] : [],
            monitoringData:data['MonitoringData'] || []
        }
        dispatch(UPDATE_DAILY_DATA(dailyData));
        dispatch(TOGGLE_GRAPH_MODAL(true));
    }

    // const onExportToExcelCallBack=async(pageNumber:number)=>{
    //     const rowDta =  await getBPRDataForExcelDownload({
    //         id:1,
    //         name:'',
    //         fields:[],
    //         filters:currFilter,
    //         paginationParameter:{
    //             pageNumber:pageNumber,
    //             recordsPerPage:5000
    //         }
    //     })
    //     return rowDta.data.data
    // }

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
            reportName:"BPR",
            stream:1,
            responseType: `arraybuffer`
        }
        notifyLoader("Downloading Data...")
        try {
            await CsvExportMTA(payload, "BufferPenetrationReport");
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
            headerTooltip: "Daily Data Graph",
            headerName:"Daily Data Graph",
            sortable:false,
            suppressMenu:true,
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
            headerTooltip: "Enter New Remark",
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
            headerTooltip: "Remark History",
        },
        tags: {
            cellRenderer: 'tagsCellRenderer',
            width: 100,
            minWidth: 100,
            filter: true,
            pinned: null,
            filterParams: {
                buttons: ['reset'], // Adds Apply and Clear buttons
            },
        }
    }

    const handleOnPageChange = async(pageNumber:number)=>{
        setCurrGridPage(pageNumber)
        await getBPRRowData(currFilter,pageNumber,userPageSize)
    }
    const savePageSize = async( pageSize:number)=>{
        setUserPageSize(pageSize)
        await getBPRRowData(currFilter,currGridPage,pageSize)
    }

    const onApplyFilter = (filter: any) => {
        setCurrFilter(filter)
        getBPRRecordCount(filter)
        setCurrGridPage(1)
        getBPRRowData(filter,1 ,userPageSize)
        getBPRUiConfig()
    }

    const onDeleteFilter = async(parentId:any, filterId:any, value:any)=>{
        const updatedFilter = onDelete(parentId,filterId,value)
        onApplyFilter(updatedFilter)
    }

    const rowsPerPage = useMemo(()=>parseInt(BPR_ROWS_PER_PAGE || '50'),[]) 
    
    // const BPRColumnData = useMemo(() => {
    //     return mapBPRFieldsToColDefs(
    //       data?.data?.data, 
    //       onOpenSubmitRemark, 
    //       onOpenRemarkHistory, 
    //       onOpenDailyDataGraph
    //     );
    //   }, [data]);
    //   // Update columns state only if there is a change
    //   useEffect(() => {
    //     // Check if the columns data has changed before setting state
    //     setBPRColumns(BPRColumnData);
    //   }, [BPRColumnData, setBPRColumns]); 
    
    return {
        isSubGridOpen,
        isLoading :  isUIConfigLoading || isBPRDataCountLoading || isRowDataLoading,
        isError,
        activeRow,
        BPRColumns,
        BPRRowData,
        agGridProps,
        remark,
        remarkHistory,
        isRemarkHistoryToolTipOpen,
        remarkHistoryToolipPosition,
        isSubmitRemarkToolTipOpen,
        submitRemarkToolTipPosition,
        updateRemark,
        setIsSubmitRemarkToolTipOpen,
        setSubmitRemarkToolipPosition,
        toggleSubGrid,
        setActiveRow,
        onSubmitRemarks,
        onCloseRemarkHistory,
        onCloseSubmitRemark,
        dailyData,
        showDailyDataGraphModal,      
        handleOnPageChange,       
        recordCount,
        currGridPage,
        rowsPerPage,
        showNormChangeHistoryTable,
        ref,
        isSavedDataLoading,
        tempRef,
        tempDownloadData,
        setTempDownloadData,
        tempAgGridProps,
        exportExcelRowData,
        setExportExcelRowData,
        exportExcelColumns,
        setExportExcelColumns,
        // getBPRRowData,
        onExportToExcelCallBack,
        currFilter,
        onDelete,
        setCurrFilter,
        onApplyFilter,
        themeUi,
        editedRows,
        onDeleteFilter,
        isRowDataLoading,
        gridState,
        lastRunDate,
        generalFilterOptions,
        onResetCallback,
        savePageSize,
        userPageSize

    }
}

export default useBPR