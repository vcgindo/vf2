import { CSSProperties, useMemo, useState,useEffect ,useRef} from "react";

import {toast} from 'react-toastify'

import useViewPort from "../../../../../hooks/useViewPort";

import { AgGridReactProps } from "ag-grid-react";
import { ColDef } from "ag-grid-enterprise";

import { notifyLoader,notifyError,notifySuccess } from "../../../../../helpers/notify";
import ColorCellRenderer from "./ColorCellRenderer";
import ETACellRenderer from "./ETACellRenderer";
import ShowRemarkCellRenderer from "./ShowRemarkCellRenderer";
// import { useSelector } from "react-redux";

// import { RootState } from "../../../../../redux/store/store";
import { useAddRemarkForExpedite, useGetOpenExpediteRequestData, useGetRemarkDetailsForExpedite } from "../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/OpenExpeditingRequests";
import SubmitRemarkCellRenderer from "./SubmitRemarkCellRenderer";
import useBPRFilter from "../../../../../hooks/useBPRFilter";
import { useUserData } from "../../../../../context";
import { defaultAgGridSideBarForBPR } from "../../../../../helpers/BPRConstants";
import { useGetState } from "../../../../../VectorFlow/Services/MTA/Common/UserUIConfig";
import { getColumnDefinationsMTA, MainMenuItemsCustomization } from "../../../../../helpers/utils"
import { GridRef } from "../../../../../VectorFlow/types/MDM"
import useGetLastRunData from "../../../../../hooks/useGetLastRunData"
import { useGetUIConfigData } from "../../../../Services/MTA/Common/UIConfig";
import { UIColumnConfigName, UserUIColumnConfigName } from "../../../../../helpers/Enum";

const useOpenExpeditingRequests = () => {

    const ref = useRef<GridRef>()
    const tempRef = useRef<GridRef>()

    const [internalRef,setInternalRef] = useState<any>()

    const {user} = useUserData()
    const themeUi = user.user.theme_ui

  const { mutateAsync: getData, isLoading: isRowDataLoading } = useGetOpenExpediteRequestData();
    const {mutateAsync:addRemark} = useAddRemarkForExpedite()
    const {mutateAsync:getRemark} = useGetRemarkDetailsForExpedite()

    const [submitRemarkToolTipPosition,setSubmitRemarkToolipPosition] = useState<CSSProperties>({})
    const [remarkHistoryToolipPosition,setRemarkHistoryToolipPosition] = useState<CSSProperties>({})
    const {state:currentFilter,setState:setCurrentFilter,onDelete} = useBPRFilter()

    const [editedRows,setEditedRows] = useState<Array<any>>([])
    const [remark,setRemark] = useState<string>('')
    const [rowData,setRowData] = useState<Array<any>>([])
    const [OERColumns,setOERColumns] = useState<any>([])
    const [colDefs,setColDefs] = useState<Array<any>>([])
    const [activeRow,setActiveRow] = useState<any>({
      sc:'',
      wc:''
    })
    const [remarkHistory,setRemarkHistory] = useState<any[]>([])

    const [tempDownloadData,setTempDownloadData] = useState<boolean>(false);

    const [exportExcelColumns,setExportExcelColumns] = useState<Array<any>>([])

    const [exportExcelRowData,setExportExcelRowData] = useState<Array<any>>([])

    const [isSubmitRemarkToolTipOpen,setIsSubmitRemarkToolTipOpen] = useState<boolean>(false)
    const [isRemarkHistoryToolTipOpen,setIsRemarkHistoryToolTipOpen] = useState<boolean>(false)

    const { getGridZoom, getScreenZoomValue } = useViewPort()

    const gridZoom = getGridZoom()
    const screenZoom = getScreenZoomValue()
    const {date:lastRunDate} = useGetLastRunData()

    const customCellRenderers = useMemo(() => ({
        // grapCellRenderer:BPRGraphCellRenderer,
        // colorTechCellRenderer:BPRTechColorCellRenderer,
        // colorEcoCellRenderer:BPREcoColorCellRenderer,
        // tagsCellRenderer:BPRTagsCellRenderer,
        etaCellRenderer:ETACellRenderer,
        colorCellRenderer:ColorCellRenderer,
        submitRemarkCellRenderer: SubmitRemarkCellRenderer,
        remarksCellRenderer: ShowRemarkCellRenderer
    }), []);

  const { mutateAsync: getState } = useGetState();
  const [gridState, setGridState] = useState<any>()
  const { mutateAsync: getUiConfig, isLoading: isUIConfigLoading } = useGetUIConfigData();
  const [initialColumnState, setInitialColumnState] = useState<any>(undefined);
  const [masterUIConfig, setMasterUIConfig] = useState<any>([]);
  
    // const {currentGridState} = useSelector((state:RootState)=>state.mta)

    const columnsNotToBeIncluded = ['remarks','rk','dailydatagraph']

  useEffect(() => {
    const getTableState = async () => {
      try {
        const MappedColumns = getColumnDefinationsMTA(initialColumnState, CustomHeader);
                                          
        setGridState({
          charts: [],
          columns: MappedColumns,
          pivot: false
        })
        setOERColumns(MappedColumns);
        getUserColumnConfig();
      } catch (err: any) {
        console.error(err);
      }
    }
    if (initialColumnState !== undefined) {
      getTableState()
    }
  }, [initialColumnState]);

  useEffect(() => {
    if (OERColumns.length) {
      if (internalRef?.api) {
        setMasterUIConfig(internalRef.api.getColumnState());
      }
    }
  }, [internalRef, OERColumns]);
                
  const getUserColumnConfig = async () => {
    const stateData = await getState({ "reportname": UserUIColumnConfigName.OER })
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
  
  const getOERUiConfig = async () => {
    try {
      const response = await getUiConfig(UIColumnConfigName.OER);
      setInitialColumnState(response.data.data);
    } catch (err: any) {
      notifyError("Something Went Wrong")
    }
  }

  useEffect(() => {
    const getRowData = async () => {
      try {
        notifyLoader("Loading Grid Data")
        const data = await getData(currentFilter)

        //// idar_issue_hai_
        //// need_a_new_api_route_to_get_OER_Configurations
        //// currently_not_avaiable
        // const ColumnDefinitions = mapFieldsToColDefs(data.data.data.config)
        // setColDefs(ColumnDefinitions)
        // setOERColumns(ColumnDefinitions);
        const tempRowData = data?.data?.data?.data || [];
        toast.dismiss()
        notifySuccess("Data Loaded Successfully")
        if (!tempRowData.length) {
          setRowData([])
        } else {
          setRowData(tempRowData.map((r: any, index: number) => ({ ...r, id: index, action: '' })))
          notifySuccess("Data Loaded Successfully")
        }
        // notifySuccess("Data Loaded Successfully")
      } catch (err: any) {
        console.error(err)
        notifyError(err)
      }
    }
    getRowData();
    getOERUiConfig();
  }, []);

    const onColumnVisible = (event: any) => {
      const { column, visible , columns } = event;
      // Optionally, you can update your state if needed (like in a sidebar with checkboxes)
      if(column!==null && column.colId!=="dailydatagraph" && event.source==='toolPanelUi'){
      setOERColumns((prevColumns:any) =>{
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
          setOERColumns((prevColumns: any) => {
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
      }
    };

    const agGridProps: AgGridReactProps =useMemo(()=>{
      return{
        suppressRowTransform: true,
        tooltipShowDelay: 0.3,
        tooltipTrigger: 'focus',
        tooltipInteraction: true,
        // rowSelection:'single',
        readOnlyEdit: false,
        gridOptions: {
            rowHeight: 50,
            getRowStyle: (params: any) => {
                if (params.node.rowIndex % 2 === 0) {
                    return { background: "#EBEBEB" };
                }
                return { background: "#F7F7F7" };
            },
        },
        // onColumnVisible: onColumnVisible,
        //         onColumnMoved: (event:any) => {
        //             const columnState = event.api.getColumnState();
        //             columnState.forEach((state:any) => {
        //               if (state.pinned && (state.colId!=='remarks' && state.colId!=='rh')) {
        //                 // Reset the pin to null
        //                 state.pinned = null;
        //               }
        //             });
        //             event.api.applyColumnState({ state: columnState });
        //         },
        sideBar:defaultAgGridSideBarForBPR,
        getMainMenuItems: MainMenuItemsCustomization,
        pagination: true,
        suppressRowClickSelection: true,
        components: customCellRenderers,
        defaultColDef: {
            floatingFilter: true,
            filter: "agMultiColumnFilter",
            cellDataType: false,
            minWidth:140,
            cellStyle: {
              "text-align": "center",
              'text-overflow':'ellipsis',
              'white-space':'nowrap'
            },
            flex: 1,
        },
        onCellValueChanged:(params)=>onCellValueChanged(params.data),
        onGridReady:(params)=>setInternalRef(params)
      }
    },[])

    const onCellValueChanged = (newRow: any) => {
      setEditedRows((prev) => {
        let found = false; // Flag to track if the row has been updated
        const updatedRows = prev.map((row) => {
          if (row.id === newRow.id) {
            found = true;
            return { ...newRow }; // Return updated row
          }
          return row; // Return unchanged row
        });
    
        if (!found) {
          // If no existing row was found, add the new row
          return [...updatedRows, {...newRow}];
        }
        return updatedRows;
      });
    };

  
 

    
    const tempAgGridProps:AgGridReactProps = useMemo (()=> {
      return {
        onRowDataUpdated:(event)=>{
          const columnsToBeIncluded = ref.current?.api.getAllDisplayedColumns().map((c)=>c.getColId()).filter((key:string)=>!columnsNotToBeIncluded.includes(key));
          if(tempDownloadData){
              event.api.exportDataAsExcel({fileName:'OpenExpeditingReport',columnKeys:columnsToBeIncluded})
              setTempDownloadData(false)
          }
        }
      }
    },[ref,tempDownloadData])
      

    const onOpenSubmitRemark = (e: React.MouseEvent<HTMLElement>,data:any) => {
        setActiveRow(data)
        const { top, left } = e.currentTarget.getBoundingClientRect()
        setSubmitRemarkToolipPosition({
            top: top * gridZoom * screenZoom,
            left: left * gridZoom * screenZoom,
        })
        setIsSubmitRemarkToolTipOpen(true)

    }

    const onOpenRemarkHistory = async (e: React.MouseEvent<HTMLElement>,data:any) => {
        try {
            setIsRemarkHistoryToolTipOpen(false)
            const toastId = notifyLoader("Getting remark history")
            const { top, left } = e.currentTarget.getBoundingClientRect()
            const remarkData = await getRemark({ whcode: data.wc, skucode: data.sc})
           
            setRemarkHistoryToolipPosition({
                top: top * gridZoom * screenZoom,
                left: left * gridZoom * screenZoom,
                height: 360,
                width: 350
            })
            toast.dismiss(toastId)
            setRemarkHistory(remarkData.data)
            setIsRemarkHistoryToolTipOpen(true)
        } catch (err: any) {
            notifyError(err.message)
        }
    }

    const onSubmitRemark = async()=>{
        try{
            if(remark.length===0) throw new Error("Remark cannot be empty")
            const toastId = notifyLoader("Submitting Remark")
            await addRemark({
                SKUCode:activeRow.sc,
                WHCode:activeRow.wc,
                remark:remark,
            })
            toast.dismiss(toastId)
            
            notifySuccess('Remark Has Been submitted')
            setRemark('')
            setActiveRow({
              sc:'',
              wc:''
            })
            
            setIsSubmitRemarkToolTipOpen(false)
        }catch(err:any){
            notifyError(err.message)
        }
    }

    const updateRemark = (e:any)=>setRemark(e.currentTarget.value)

    const onCloseSubmitRemark =()=>setIsSubmitRemarkToolTipOpen(false)


    const onCloseRemarkHistory = ()=>setIsRemarkHistoryToolTipOpen(false)

    const onApplyFilter = async (filter: any) => {
      setCurrentFilter(filter);
      setEditedRows([]);
      notifyLoader("Loading Grid Data");
      try {
        const data = await getData(filter);
        if (
          data?.data?.data?.data &&
          Array.isArray(data.data.data.data) &&
          data.data.data.data.length > 0
        ) {
          setRowData(
            data.data.data.data.map((r: any, index: number) => ({
              ...r,
              id: index,
              action: "",
            }))
          );
        } else {
          setRowData([]);
        }
        toast.dismiss();
        notifySuccess("Data Loaded Successfully");
      } catch (err: any) {
        notifyError(err);
        setRowData([]);
      }
    };

    const onDeleteFilter = async(parentId:any, filterId:any, value:any)=>{
      const updatedFilter = onDelete(parentId,filterId,value)
      onApplyFilter(updatedFilter)
    }

  const onSubmitEditedRows = async () => {
    try {
      if (editedRows.length === 0) {
        notifyError("Please add remarks/remark to save");
        return;
      }

      const toastId = notifyLoader("Submitting Remark");

      const payload = editedRows.map((r) => ({
        SKUCode: r.sc,
        WHCode: r.wc,
        Remark: r.action || "",
        ETA: r.eta,
      }));

      await addRemark({ data: payload });
      toast.dismiss(toastId);
      notifySuccess("Remark saved successfully");

      const editedIds = new Set(editedRows.map((r) => `${r.sc}-${r.wc}`));
      const updatedRowDataForState: any[] = [];
      ref.current?.api.forEachNode((node: any) => {
        if (editedIds.has(node.id)) {
          const newData = { ...node.data, action: "" };
          node.setData(newData);             
          updatedRowDataForState.push(newData);
        }
      });
      setRowData((prev) => prev.map((r) =>
        editedIds.has(`${r.sc}-${r.wc}`) ? { ...r, action: "" } : r
      ));

      setEditedRows([]);

    } catch (err: any) {
      console.error(err);
      notifyError(err?.message || "Something went wrong");
    }
  };



    
  const onResetCallback = async () => {
    setGridState({
      charts: [],
      columns: masterUIConfig,
      pivot: false,
    })
  };

  const CustomHeader = {
    pic: {
      cellRenderer:'colorCellRenderer',
    },
    eta: {
      cellRenderer: 'etaCellRenderer',
      floatingFilter: false,
      editable: false,
      // cellDataType: 'date',
      // minWidth: 160,
      // maxWidth: 190,
      resizable: false,
    },
    action: {
      cellStyle: {
        backgroundColor: 'white',
        border: '1px solid #b9bdba',
        color: 'black',
        padding: '1px'
      },
      // cellRenderer: 'submitRemarkCellRenderer',
      floatingFilter: false,
      editable: true,
      pinned: 'right',
      minWidth: 100,
      maxWidth: 130,
      lockPosition: 'right',
      menuTabs: [],
      suppressMenu: true,
      resizable: false,
      headerTooltip: "Enter New Remark",
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
    rk: {
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
        agGridProps,
        rowData,
        OERColumns,
        isLoading :isUIConfigLoading || isRowDataLoading ,      
        remark,
        remarkHistory,
        isSubmitRemarkToolTipOpen,
        isRemarkHistoryToolTipOpen,
        submitRemarkToolTipPosition,
        remarkHistoryToolipPosition,
        updateRemark,
        onSubmitRemark,
        onCloseSubmitRemark,
        onCloseRemarkHistory,
        ref,
        onOpenSubmitRemark,
        // isSavedDataLoading,
        tempRef,
        tempDownloadData,
        setTempDownloadData,
        tempAgGridProps,
        exportExcelRowData,
        setExportExcelRowData,
        exportExcelColumns,
        setExportExcelColumns,
        currentFilter,
        setCurrentFilter,
        onDelete,
        onApplyFilter,
        onDeleteFilter,
        onSubmitEditedRows,
        editedRows,
        themeUi,
        onResetCallback,
        lastRunDate
    }
}

export default useOpenExpeditingRequests