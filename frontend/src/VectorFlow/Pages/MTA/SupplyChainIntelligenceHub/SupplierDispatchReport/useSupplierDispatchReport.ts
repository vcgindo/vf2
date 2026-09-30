
import { useGetSDRUIConfiguration ,useGetSDRData,useGetSDRDataCount} from '../../../../Services/MTA/SupplyChainIntelligenceHub/SupplierDispatchReport/index';
import { convertUiConfigToOptions, getColumnDefinationsMTA, mapVDRFieldsToColDefs } from '../../../../../helpers/utils';
import { useEffect, useState,useRef,useMemo } from 'react';
import { notifyError,notifyLoader, notifySuccess} from '../../../../../helpers/notify';
import useBPRFilter from '../../../../../hooks/useBPRFilter';
import { toast } from 'react-toastify';
import { AgGridReactProps } from 'ag-grid-react';
import {SDRDispatchColorCellRenderer} from './SDRCellRenderers'
import { useGetState } from '../../../../../VectorFlow/Services/MTA/Common/UserUIConfig';
import { defaultAgGridSideBarForBPR } from '../../../../../helpers/BPRConstants';
import { GridRef } from '../../../../../VectorFlow/types/MDM';
import { useGetUIConfigData } from '../../../../Services/MTA/Common/UIConfig';
import { UIColumnConfigName, UserUIColumnConfigName } from '../../../../../helpers/Enum';
import { useSelector } from 'react-redux';
import { RootState } from '../../../../../redux/store/store';

const useSupplierDispatchReport= ()=>{

    const ref = useRef<GridRef>();

    const [internalRef,setInternalRef] = useState<any>()
    const [gridState,setGridState] = useState<any>()
    const [SDRCount,setSDRCount]=useState<any>()
    const [RowData, setRowData]=useState<any[]>([])
    const [currentPage,setCurrentPage] = useState<any>(1);
    const [exportExcelColumns,setExportExcelColumns] = useState<Array<any>>([])
    const [tempDownloadData,setTempDownloadData] = useState<boolean>(false);
    const [exportExcelRowData,setExportExcelRowData] = useState<Array<any>>([])

    const tempRef = useRef()

    // const { data, isLoading: isSDRUILoading } = useGetSDRUIConfiguration();
    const { mutateAsync: getUiConfig, isLoading: isUIConfigLoading, isError } = useGetUIConfigData();
    const {mutateAsync:getSDRData, isLoading: isSDRDataLoading} =useGetSDRData();
    const {mutateAsync:getSDRDataCount,isLoading:isSDRDataCountLoading}=useGetSDRDataCount();
    const {state:currFilter,setState:setCurrFilter,onDelete} = useBPRFilter()

    const {mutateAsync:getState} = useGetState()
    const [generalFilterOptions,setGeneralFilterOptions] = useState();
    const [initialColumnState, setInitialColumnState] = useState<any>(undefined);
    const [masterUIConfig, setMasterUIConfig] = useState<any>([]);
    const [VDRColumns,setVDRColumns] = useState<any[]>([])
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const SUPPLIER_DISPATCH_REPORT_PER_PAGE = EnvConfig['SUPPLIER_DISPATCH_REPORT_PER_PAGE'];   
    const rowsPerPage = parseInt(SUPPLIER_DISPATCH_REPORT_PER_PAGE || '100');
    const [userPageSize , setUserPageSize]  = useState<number>(SUPPLIER_DISPATCH_REPORT_PER_PAGE?parseInt(SUPPLIER_DISPATCH_REPORT_PER_PAGE):100) 
     
 

    const customCellRenderers = useMemo(() => (
        {
            grapCellRenderer: '',
            colorDispatchRender: SDRDispatchColorCellRenderer
        
        }), []);

    useEffect(() => {
        getInitialSDRRowData();
        getBPRUiConfig();
    }, []);

    const getInitialSDRRowData = async () => {
        try {
            await GetDataCount()
            await GetSDRData(currentPage);
        } catch (err: any) {
            notifyError(err)
        }
    }
  
    const getBPRUiConfig = async () => {
        try {
            const response = await getUiConfig(UIColumnConfigName.SDR);
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
                    setVDRColumns(MappedColumns);
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
            if (VDRColumns.length) {
                if (internalRef?.api) {
                    setMasterUIConfig(internalRef.api.getColumnState());
                }
            }
        }, [internalRef, VDRColumns]);
        
    const getUserColumnConfig = async () => {
        const stateData = await getState({ "reportname": UserUIColumnConfigName.SDR })
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
            const result = internalRef?.api.applyColumnState({ state: gridState.columns, applyOrder: true });
            internalRef?.api.sizeColumnsToFit();
            if (!result) {
                console.error("Failed to apply column state", result);
            }
        }
    }, [internalRef, gridState]);
 
    const GetDataCount = async (filter?:any)=>{
        const DataCount= await getSDRDataCount({
            filters: filter || currFilter,
            paginationParameter:{
                pageNumber: 1,
                recordsPerPage:rowsPerPage
            }
        })
        setSDRCount(DataCount.data.data[0].count);

    }

    

    const GetSDRData= async (PageNo:any ,  pageSize?:number) =>{
        try{
            if(SDRCount===0){
                await GetDataCount(currFilter);
            }
            notifyLoader("Loading Grid Data")
            const VDRData= await getSDRData ( {
                filters:currFilter,
                paginationParameter:{
                    pageNumber:PageNo,
                    recordsPerPage:pageSize  || userPageSize || rowsPerPage
                }
            })
            setRowData(VDRData.data.data);
            setCurrentPage(PageNo);
            toast.dismiss()
            notifySuccess("Data Loaded Successfully")
        }
        catch(err:any){
            notifyError(err)
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
    }

    const agGridProps: AgGridReactProps = useMemo(() => {
        return {
            paginationPageSize: userPageSize,
    
            suppressRowTransform: true,
            tooltipShowDelay: 0.3,
            tooltipTrigger: "focus",
            tooltipInteraction: true,
            readOnlyEdit: true,
        
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
         if(tempDownloadData) event.api.exportDataAsExcel({fileName:'SupplierDispatchReport', columnKeys:ref.current?.api.getAllDisplayedColumns().map((c)=>c.getColId())});
        }
      };
    
    const onExportToExcelCallBack=async(pageNumber:number)=>{
    const data =  await getSDRData({
        filters:currFilter,
        paginationParameter:{
            pageNumber:pageNumber,
            recordsPerPage:5000
        }
    })
    
    return data.data.data
    }

    const onApplyFilter = async(filter:any)=>{
        try{
            const DataCount = await getSDRDataCount({
                filters:filter ,
                paginationParameter:{
                    pageNumber:1,
                    recordsPerPage:userPageSize || parseInt(SUPPLIER_DISPATCH_REPORT_PER_PAGE || '100')
                }
            })
            setSDRCount(DataCount.data.data[0].count);
        notifyLoader("Loading Grid Data")
            const rowData =await getSDRData({
                filters:filter ,
                paginationParameter:{
                    pageNumber:1,
                    recordsPerPage:userPageSize || parseInt(SUPPLIER_DISPATCH_REPORT_PER_PAGE || '100')
                }
            })
            
        
        // setRecordCount(rowData.data.recordCount)
            setCurrFilter(filter)
            setCurrentPage(1)
            setRowData(rowData?.data?.data)
            toast.dismiss()
            notifySuccess("Data Loaded Successfully")
        }catch(err:any){
            notifyError(err)
            setRowData([])
            setSDRCount(0)
        }
    }

    const onDeleteFilter = async(parentId:any, filterId:any, value:any)=>{
        const updatedFilter = onDelete(parentId,filterId,value)
        onApplyFilter(updatedFilter)
    }
       
    const savePageSize = async( pageSize:number)=>{
        setUserPageSize(pageSize)
      await GetSDRData(currentPage , pageSize)
    }

    return{
        VDRColumns,
        RowData,
        SDRCount,
        setCurrentPage,
        currentPage,
        exportExcelColumns,
        setExportExcelColumns,
        setTempDownloadData,
        tempDownloadData,
        exportExcelRowData,
        setExportExcelRowData,
        isLoading: isUIConfigLoading || isSDRDataLoading || isSDRDataCountLoading,
        isError,
        GetSDRData,
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
        savePageSize,
        userPageSize
    }
    

}

export default useSupplierDispatchReport;