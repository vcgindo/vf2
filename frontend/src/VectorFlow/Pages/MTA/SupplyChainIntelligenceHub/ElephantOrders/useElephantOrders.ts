
import { useGetEOData,useGetEODataCount, useSubmitDueDates} from '../../../../Services/MTA/SupplyChainIntelligenceHub/ElephantOrders/index';
import { convertUiConfigToOptions, getColumnDefinationsMTA } from '../../../../../helpers/utils';
import { useEffect, useState,useRef,useMemo } from 'react';
import { notifyError,notifyLoader, notifySuccess} from '../../../../../helpers/notify';
import useBPRFilter from '../../../../../hooks/useBPRFilter';
import { toast } from 'react-toastify';
import { AgGridReactProps } from 'ag-grid-react';
import { useGetState } from '../../../../Services/MTA/Common/UserUIConfig';
import { defaultAgGridSideBarForBPR } from '../../../../../helpers/BPRConstants';
import { GridRef } from '../../../../types/MDM';
import { useGetUIConfigData } from '../../../../Services/MTA/Common/UIConfig';
import { UIColumnConfigName, UserUIColumnConfigName } from '../../../../../helpers/Enum';
import DateCellRenderer from './DateCellRenderer';
import { useSelector } from 'react-redux';
import { RootState } from '../../../../../redux/store/store';

const useElephantOrders= ()=>{

    const ref = useRef<GridRef>();
    const [editedRows,setEditedRows] = useState<Array<any>>([])
    const [internalRef,setInternalRef] = useState<any>()
    const [gridState,setGridState] = useState<any>()
    const [EOCount,setEOCount]=useState<any>()
    const [RowData, setRowData]=useState<any[]>([])
    const [currentPage,setCurrentPage] = useState<any>(1);
    const [exportExcelColumns,setExportExcelColumns] = useState<Array<any>>([])
    const [tempDownloadData,setTempDownloadData] = useState<boolean>(false);
    const [exportExcelRowData,setExportExcelRowData] = useState<Array<any>>([])

    const tempRef = useRef()

    const { mutateAsync: getUiConfig, isLoading: isUIConfigLoading, isError } = useGetUIConfigData();
    const {mutateAsync:getEOData, isLoading: isEODataLoading} =useGetEOData();
    const {mutateAsync:getEODataCount,isLoading:isEODataCountLoading}=useGetEODataCount();
    const {state:currFilter,setState:setCurrFilter,onDelete} = useBPRFilter()
    const {mutateAsync:getState,isLoading: isSavedDataLoading} = useGetState()
    const [generalFilterOptions,setGeneralFilterOptions] = useState();
    const [initialColumnState, setInitialColumnState] = useState<any>(undefined);
    const [masterUIConfig, setMasterUIConfig] = useState<any>([]);
    const [VDRColumns,setVDRColumns] = useState<any[]>([])
 
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const ELEPHANT_ORDER_ROWS_PER_PAGE = EnvConfig['ELEPHANT_ORDER_ROWS_PER_PAGE'];   
    const rowsPerPage = parseInt(ELEPHANT_ORDER_ROWS_PER_PAGE|| '100');
    const [userPageSize , setUserPageSize]  = useState<number>(ELEPHANT_ORDER_ROWS_PER_PAGE?parseInt(ELEPHANT_ORDER_ROWS_PER_PAGE):50)  
    const {mutateAsync:submitDueDates} = useSubmitDueDates();
    const [editedDueDateRows, setEditedDueDateRows] = useState<any[]>([]);



    const handleDueDateChange = (
        newDate: string,
        rowData: any,
        skuKey: string,
        whKey: string,
        orderIdKey: string
      ) => {
        if (!newDate || !rowData) return;
      
        const skucode = rowData[skuKey];
        const whcode = rowData[whKey];
        const orderid = rowData[orderIdKey];
      
        if (!skucode || !whcode || !orderid) {
          return;
        }
        const updated = {
          skucode,
          whcode,
          orderid,
          duedate: newDate,
        };
      
        setEditedDueDateRows((prev) => {
          const index = prev.findIndex(
            (row) =>
              row.skucode === skucode &&
              row.whcode === whcode &&
              row.orderid === orderid
          );
      
          if (index > -1) {
            const updatedList = [...prev];
            updatedList[index] = updated;
            return updatedList;
          } else {
            return [...prev, updated];
          }
        });
      };
    
      const handleClearDueDate = (rowData: any) => {
        const skucode = rowData['SKUCode'];
        const whcode = rowData['WhCode'];
        const orderid = rowData['CustomerOrderID'];
      
        if (!skucode || !whcode || !orderid) {
          return;
        }
      
        const cleared = {
          skucode,
          whcode,
          orderid,
          duedate: null,  // Explicit null for backend
        };
      
        setEditedDueDateRows((prev) => {
          const index = prev.findIndex(
            (row) =>
              row.skucode === skucode &&
              row.whcode === whcode &&
              row.orderid === orderid
          );
      
          if (index > -1) {
            const updatedList = [...prev];
            updatedList[index] = cleared;
            return updatedList;
          } else {
            return [...prev, cleared];
          }
        });
      
        // Reflect removal in UI immediately
        setRowData((prev) =>
          prev.map((row) => {
            if (
              row.SKUCode === skucode &&
              row.WhCode === whcode &&
              row.CustomerOrderID === orderid
            ) {
              return {
                ...row,
                DueDate: null,
                dueDateAction: null,
              };
            }
            return row;
          })
        );
      };
      
    const customCellRenderers = useMemo(() => (
        {
            grapCellRenderer: '',
        }), []);

    useEffect(() => {
        getInitialEORowData();
        getEOUiConfig();
    }, []);

    const getInitialEORowData = async () => {
        try {
            await GetDataCount()
            await GetEOData(currentPage);
        } catch (err: any) {
            notifyError(err)
        }
    }

    const onSubmitDueDate = async () => {
        try {
          if (editedDueDateRows.length === 0) {
            notifyError("Please select due date(s) to save");
            return;
          }
      
          const toastId = notifyLoader("Submitting Due Dates");
      
          const payload = editedDueDateRows.map((e) => ({
            skucode: e.skucode,
            whcode: e.whcode,
            orderid: e.orderid,
            duedate: e.duedate,
          }));
      
          const { data } = await submitDueDates({ data: payload });
      
          const updatedRowData = RowData.map((row) => {
            const match = editedDueDateRows.find(
              (e) =>
                e.skucode === row.SKUCode &&
                e.whcode === row.WhCode &&
                e.orderid === row.CustomerOrderID
            );
            if (match) {
              return {
                ...row,
                DueDate: match.duedate, 
                dueDateAction: null,
              };
            }
            return row;
          });
      
          setRowData(updatedRowData); 
      
          toast.dismiss(toastId);
          notifySuccess(data.msg || "Due dates updated successfully");
          setEditedDueDateRows([]);
        } catch (err: any) {
          notifyError(err.message || "Something went wrong");
        }
      };
      
    const getEOUiConfig = async () => {
        try {
            const response = await getUiConfig(UIColumnConfigName.EO);
            setInitialColumnState(response.data.data);
        } catch (err: any) {
            console.error("Something Went Wrong")
        }
    }

    useEffect(() => {
            const getTableState = async () => {
                try {
                    const MappedColumns = getColumnDefinationsMTA(initialColumnState, CustomHeader);
        
                    if (!MappedColumns.some((col: any) => col.field === 'Due Date')) {
                        MappedColumns.push({
                            headerName: "Action",
                            field: "dueDateAction",
                            cellRenderer: DateCellRenderer ,
                            editable: false,
                            width: 200,
                            suppressMenu: true,
                            cellRendererParams: {
                                onDateChange: (newDate: string, rowData: any) => {
                                  handleDueDateChange(newDate, rowData, 'SKUCode', 'WhCode', 'CustomerOrderID');

                                },

                                onClearDate: (rowData: any) => {
                                    handleClearDueDate(rowData);
                                },
                            },
                            
                        });
                    }
                   
                    setGridState({
                        charts: [],
                        columns: MappedColumns,
                        pivot: false
                    })
                    setVDRColumns(MappedColumns);
                    getUserColumnConfig();
                    
                } catch (err: any) {
                    console.error("Something Went Wrong")
                }
            }
            if (initialColumnState !== undefined) {
                getTableState();
                setGeneralFilterOptions(convertUiConfigToOptions(initialColumnState));
            }
        }, [initialColumnState]);
    
        useEffect(() => {
            if (VDRColumns.length) {
                if (internalRef?.api) {
                    setMasterUIConfig(internalRef.api.getColumnState());
                }
            }
        }, [internalRef, VDRColumns]);
        
    const getUserColumnConfig = async () => {
        const stateData = await getState({ "reportname": UserUIColumnConfigName.EO })
        if (stateData.data.data.length !== 0) {
            const parsedContent = JSON.parse(stateData.data.data)
              
            setGridState({
                charts: parsedContent.charts,
                columns: parsedContent.columns,
                pivot: parsedContent.pivot,
            })
        
        } else {
            console.error("Data not available");
        }
    }
    
    useEffect(() => {
        if (internalRef && gridState && gridState.columns) {
            const result = internalRef?.api.applyColumnState({ state: gridState.columns, applyOrder: true });
            internalRef?.api.sizeColumnsToFit();
            if (!result) {
                console.error("Failed to apply column state");
            }
        }
    }, [internalRef, gridState]);
 
    const GetDataCount = async (filter?:any)=>{
        const DataCount= await getEODataCount({
            filters: filter || currFilter,
            paginationParameter:{
                pageNumber: 1,
                recordsPerPage:rowsPerPage
            }
        })    
        setEOCount(DataCount.data["recordCount"]);

    }

    

    const GetEOData= async (PageNo:any , pageSize?:any )=>{
        try{
            if(EOCount===0){
                await GetDataCount(currFilter);
            }
            notifyLoader("Loading Grid Data")
            const VDRData= await getEOData ( {
                filters:currFilter,
                paginationParameter:{
                    pageNumber:PageNo,
                    recordsPerPage:pageSize || userPageSize
                }
            })
            setRowData(VDRData.data.data);
            setCurrentPage(PageNo);
            toast.dismiss()
            notifySuccess("Data Loaded Successfully")
        }
        catch(err:any){
            console.error("Error")
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
        DispatchPen: {
            cellRenderer: 'colorDispatchRender',    
        },
        WHDescription: {
            rowGroup: false,
        },
        EPD:{
            headerTooltip: "Earliest Possible Due Date"
        },
        RLTUptoSuppOrPlant:{
            headerTooltip: "RLT Upto Supplier/Plant"
        },
        TopmostWhCode:{
            headerTooltip: "Topmost Location Code"
        },
        TopmostWhNorm:{
            headerTooltip:"Topmost Location Norm"
        },
        CustomerExpectedDate:{
            headerTooltip: "Customer Expected Date"
        }
    }

    const agGridProps: AgGridReactProps = useMemo(() => {
        return {
            paginationPageSize: parseInt(
                ELEPHANT_ORDER_ROWS_PER_PAGE || "50"
            ),
    
            suppressRowTransform: true,
            tooltipShowDelay: 0,
            tooltipTrigger: "focus",
            tooltipInteraction: true,
            readOnlyEdit: false,
            enableBrowserTooltips:true,
            gridOptions: {
                sideBar: defaultAgGridSideBarForBPR,
                rowHeight: 50,
                getRowStyle: (params: any) => {
                    if (params.node.rowIndex % 2 === 0) {
                        return { background: "#EBEBEB" };
                    }
                    return { background: "#F7F7F7" };
                },
            },
            enableRangeSelection: true,
            components: customCellRenderers,
            rowSelection: "multiple",
            statusBar: {
                statusPanels: [
                    { statusPanel: "agTotalAndFilteredRowCountComponent", align: "left" },
                    { statusPanel: "agTotalRowCountComponent", align: "left" },
                    { statusPanel: "agFilteredRowCountComponent", align: "left" },
                    { statusPanel: "agSelectedRowCountComponent", align: "left" },
                    { statusPanel: "agAggregationComponent", align: "left" },
                ],
            },
            pagination: false,
            suppressRowClickSelection: true,
          
            defaultColDef: {
                floatingFilter: true,
                resizable: true,
                cellStyle: {
                    flex: 1,
                    "text-align": "center",
                    height: "50px",
                    "font-style": "normal",
                    " font-variant": "normal",
                    " font-weight": "300",
                    " font-size": "20px",
                    " font-family": "Roboto",
                    display: "block",
                    "text-overflow": "ellipsis",
                    "white-space": "nowrap",
                },
            },
            onGridReady: (params) => setInternalRef(params)
        }
    }, []);
    
    const tempAgGridProps:AgGridReactProps = {
        onRowDataUpdated:(event)=>{
         if(tempDownloadData) event.api.exportDataAsExcel({fileName:'ElephantOrders', columnKeys:ref.current?.api.getAllDisplayedColumns().map((c)=>c.getColId())});
        }
      };
    
    const onExportToExcelCallBack=async(pageNumber:number)=>{
    const data =  await getEOData({
        filters:currFilter,
        paginationParameter:{
            pageNumber:pageNumber,
            recordsPerPage:5000
        }
    })
    
    return data.data.data
    }

    const onApplyFilter = async(filter:any)=>{
         
      const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
      const ELEPHANT_ORDER_ROWS_PER_PAGE = EnvConfig['ELEPHANT_ORDER_ROWS_PER_PAGE'];   
        try{
            const DataCount = await getEODataCount({
                filters:filter ,
                paginationParameter:{
                    pageNumber:1,
                    recordsPerPage:userPageSize || parseInt(ELEPHANT_ORDER_ROWS_PER_PAGE|| '100')
                }
            })
            setEOCount(DataCount.data.data[0].count);
        notifyLoader("Loading Grid Data")
            const rowData =await getEOData({
                filters:filter ,
                paginationParameter:{
                    pageNumber:1,
                    recordsPerPage:userPageSize || parseInt(ELEPHANT_ORDER_ROWS_PER_PAGE || '100')
                }
            })
            
        
            setCurrFilter(filter)
            setCurrentPage(1)
            setRowData(rowData?.data?.data)
            toast.dismiss()
            notifySuccess("Data Loaded Successfully")
        }catch(err:any){
            notifyError(err)
            setRowData([])
            setEOCount(0)
        }
    }

    const onDeleteFilter = async(parentId:any, filterId:any, value:any)=>{
        const updatedFilter = onDelete(parentId,filterId,value)
        onApplyFilter(updatedFilter)
    }
        
    const savePageSize = async( pageSize:number)=>{
        setUserPageSize(pageSize)
        await GetEOData(currentPage, pageSize);
    }

    return{
        isSavedDataLoading,
        VDRColumns,
        RowData,
        EOCount,
        setCurrentPage,
        currentPage,
        exportExcelColumns,
        setExportExcelColumns,
        setTempDownloadData,
        tempDownloadData,
        exportExcelRowData,
        setExportExcelRowData,
        isLoading: isUIConfigLoading || isEODataLoading || isEODataCountLoading,
        isError,
        GetEOData,
        tempRef,
        tempAgGridProps,
        customCellRenderers,
        currFilter,
        setCurrFilter,
        onDeleteFilter,
        onExportToExcelCallBack,
        onApplyFilter,
        agGridProps,
        ref,
        generalFilterOptions,
        onResetCallback,
        onSubmitDueDate,
        savePageSize,
        userPageSize
    }
    

}

export default useElephantOrders;