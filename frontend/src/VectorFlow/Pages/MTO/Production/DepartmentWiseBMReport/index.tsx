import React, { useEffect, useMemo, useRef, useState } from 'react';
import MTOActionToolBar from '../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar';
import {
    BMDepWrapper,
    BMDepHeaderWraper
} from './styles';
import { AgGridReactProps } from 'ag-grid-react';
//import { ColDef } from 'ag-grid-enterprise'

//import { /*deptwiseBMReportData*/ RemarkHistoryData } from './DeptWiseBMReportData';
import GridView from './GridView';
import { Allotment } from 'allotment';
import { BTRAllomentSection, BTRTableWrapper, HorizontalViewWrapper } from '../../Common/SplitGraphContainer/styles';
// import useViewPort from '../../../../../hooks/useViewPort';
import OrderElapsedGrid from './OrderElapsedGrid';
import AgeingCellRenderer from './AgeingIconCellRenderer';
// import customCellRenderer from './CustomCellRenderer';
// import RowGroupRenderer from './RowGroupRenderer';
import RemarkHistoryRenderer from './RemarkHistoryRenderer';
import BPRRemarkHistoryModal from './MTORemarkHistoryModal';
import Checkbox from '../../../../../components/VectorFLOW/commons/MTO/Checkbox';
import { useUserData } from '../../../../../context';
import { useAddBMReportRemark, useGetDeptWiseWipData, useGetFilteredDeptWiseBMReport, useGetHighAgeingData } from '../../../../../VectorFlow/Services/MTO/Production/DepartmentWiseBMReport/index'
import { notifyError, notifyLoader, notifySuccess } from '../../../../../helpers/notify';
import { toast } from 'react-toastify';
import OverlayLoader from '../../Common/Loader';
import { useGetPoogiRemarks } from '../../../../../VectorFlow/Services/MTO/Poogi/ReasonOrderChange/index';
import BPPRenderer from '../../Common/BPRRenderer/BPPRenderer';
import { IRowNode } from 'ag-grid-enterprise';
import { useGetBOMExplosionData } from '../../../../../VectorFlow/Services/MTO/Common/BOMExplosion';
import { ColorsMTO } from '../../Common/Colors';
import { useGetFilterData } from '../../../../../VectorFlow/Services/MTO/Common/CommonFilter';
import useFilter from '../../../../../hooks/useFilter';
import { formatFilterJSON, getColumnDefinations,DownloadExcel, getBodyForExcelExport } from "../../../../../helpers/utils";
import { useGetUIConfigData } from "../../../../../VectorFlow/Services/MTO/Common/UIConfig";
import { GridRef } from '../../../../../VectorFlow/types/MDM';
import { useGetOverAllBMReport } from '../../../../../VectorFlow/Services/MTO/Production/OverallBMReport';
import { BM_REPORT_ANALYTICS } from '../../../../../redux/actions/MTO';
import { modifyAnalyticsData } from './helper';
import { useDispatch } from 'react-redux';
import { useGetDBRsettingsData } from '../../../../Services/MTO/Common/DBRSettings';
import { useGetUserUIConfigData, useUpdateUserUIConfigData } from '../../../../../VectorFlow/Services/MTO/Common/UserUIConfig'
import { FilterPageName, UIGridCode } from '../../Common/Enum';
import _, { debounce } from 'lodash';
import moment from 'moment';
import { useGetDate } from '../../../../../VectorFlow/Services/MTO/Production/InsightsAndTrends/RMPMExpediting';
import BomExcelModal from '../../Common/BomExcelModal';
import useColDef from '../../../../../hooks/useColDef';
import { createDynamicColumnDefs } from '../../../../../helpers/gridUtils';


interface ApiResponse {
    cc: string;
    cp: number;
    hd: string;
    v: boolean;
    cla: string;
    scc: string;
    children?: ApiResponse[];
    cgs?: string
    pinned?: string;
    dt?: string;
}


interface ColDefChild {
    field: string;
    headerName: string;
    colId: string;
    cellRenderer?: string;
    initialWidth?: number;
    floatingFilter?: boolean;
    columnGroupShow?: string;
    pinned?: string;
    cellRendererParams?: {
        visible?: {
            flag: any;
        };
        onClick?: (data: string) => Promise<void>;
    };
}

type UpdateRemarkObj = {
    ok: string;
    dept: number;
    rm: string;
    user: string
};

type orderkeyObj = {
    ok: []
}

interface DepartmentData {
    woh: number;
    mfg: number;
    int: number | null;
    out: number;
}
// Define the structure for each order item
interface OrderItem {
    tq: number;
    li: string;
    [key: string]: number | string | DepartmentData; // Allow additional properties like departments
}

// Define the structure of the input data
interface Orders {
    [key: string]: OrderItem; // Order ID as the key
}

interface ApiResponseItem {
    cc: string;       // Main category code
    v: boolean;       // Visibility flag
    cp?: number;      // Main category property (optional since it will be added)
    hd: string;       // Header description (will be set to the name of cc)
    cla: string;      // Class alignment (fixed value)
    scc: string;      // Sub-channel code (will be set to the name of cc)
    ch?: ApiResponse[]; // Array of channel items
    pinned?:string;
    
}


const APIFilterConfig = {
    filSecVisConfig: {
        "Prod_Dept_Wise_BM_Report": {
            mjr: false,
            or: true,
            res: true,
            cus: true
        },
    }
};


const DptWiseBMReport = () => {
    const { mutateAsync: getFilteredDeptWiseBMReportData, isLoading: isFilteredDataLoaded } = useGetFilteredDeptWiseBMReport();
    const { mutateAsync: getOverallBMReportData } = useGetOverAllBMReport();
    const { mutateAsync: getDBRsettingsData} = useGetDBRsettingsData();
    const { mutateAsync: getPoogIRemarks } = useGetPoogiRemarks();
    const { mutateAsync: addBMReportRemark } = useAddBMReportRemark();
    const { mutateAsync: getDeptWiseWipData } = useGetDeptWiseWipData();
    const { mutateAsync: getHighAgeingData } = useGetHighAgeingData();
    const { mutateAsync: getBOMExplosionData, /*isLoading :BombDataLoading*/ } = useGetBOMExplosionData();
    const { mutateAsync: getUIConfigData} = useGetUIConfigData()
    const [coldefs, setColdef] = useState<any>();
    const [tempColdef, setTempColdef] = useState<any>([{}]);
    const [areRowsSelected, setAreRowsSelected] = useState(false);
    const [isRemarkHistoryOpen, setIsRemarkHistoryOpen] = useState<boolean>(false);
    const [gridData, setGridData] = useState<any>();
    const [isWIPChecked, setWIPCheck] = useState<boolean>(false);
    const [isOrderElapsedGrid, setIsOrderElapsedGrid] = useState<boolean>(false);
    const [remarkHistory, setRemarkHistory] = useState<any>();
    const [editedRows, setEditedRows] = useState<Set<number>>(new Set());
    const [deptWiseWipData, setDeptWiseWipData] = useState<any>();
    const [highAgeing, sethighAgeing] = useState<any>();
    // const { screenHeight } = useViewPort();
    const { user } = useUserData();
    const UserAllRoles = user?.roles?.permission;
    const themeUi = user?.user?.theme_ui;
    const refGraph1 = useRef<any>(null);
    const [deptName, setDeptName] = useState<any>([]);
    const [currentPage, setCurrentPage] = useState<number>(1);
    const [gridDataCount, setGridDataCount] = useState<number>(0);
    const [masterSelectedRowData, setMasterSelectedRowData] = useState<any>([]);
    const [filterData, setFilterData] = useState({});
    const [isReset, setIsReset] = useState<any>();
    const [columnState, setColumnState] = useState<any>();
    const [masterUIConfig, setMasterUIConfig] = useState([]);
    const [isPivot, setIsPivot] = useState<any>(false);
    const [userPageSize, setUserPageSize] = useState<any>();
    const [userConfigFetched, setUserConfigFetched] = useState<any>(false);
    
    const { mutateAsync: getUserUIConfigData, isLoading: isGetStateLoading } = useGetUserUIConfigData();
    const { mutateAsync: updateUserUIConfigData } = useUpdateUserUIConfigData();

    const [bomHeader, setBomHeader]= useState([])
    const [bomActive, setBomActive] = useState<any>(undefined);
    const { getGroupedColDef, groupedColDefsRef } = useColDef();
    const [showExcelModal, setShowExcelModal] = useState(false);

  const excelColorArr = ["Black", "Red", "White", "Green", "Yellow", "Blue"]

    const excelStyles = useMemo(() => 
        excelColorArr.map((color) => ({
          id: color,
          font: { color: color === "White" ? "000000" : "#ffffff" },
          interior: {
            color: color === "White"  ? "#A8A8A8" : ColorsMTO[color as keyof typeof ColorsMTO]?.code,
            pattern: 'Solid'
          }
        }))
      , []);

      const ReportName='BomExplosion'


    const { mutateAsync: getPageWiseFilterData, /*isLoading*/ } = useGetFilterData()
    const {
        state: currFilter,
        setState: setCurrFilter,
        onFilterRemove,
        isFilterOpen,
        isMfgSelected,
        onAddFilter,
        onApplyFilter,
        toggleFilter,
        appliedFilters
    } = useFilter(filterData, APIFilterConfig.filSecVisConfig.Prod_Dept_Wise_BM_Report);
    const [tempGridData, setTempGridData] = useState<any>(undefined);
    const tempGraph = useRef<GridRef>(null);
    const [isExcelLoading, setIsExcelLoading] = useState<boolean>(false);
    
    const customCellRenderers = useMemo(() => (
        {
            "colorCellRenderer": BPPRenderer,
            "AgeingCellRenderer": AgeingCellRenderer,
            RemarkHistoryRenderer: RemarkHistoryRenderer,
        }), []);

    const sideBar = useMemo(() => {
        return {
            toolPanels: ['columns'],
        };
    }, []);

    const dispatch = useDispatch();

    useEffect(() => {
        
        
        try {
            getOverallBMReportData({ page: 1, appliedFilters, analytics: 1 }).then((data) => {
                const response: any = data?.data?.data;
                const analytics = modifyAnalyticsData(response);
                dispatch(BM_REPORT_ANALYTICS(analytics))
            })
        }
        catch (e) {
            dispatch(BM_REPORT_ANALYTICS([]))
        }

    }, [])

  
    
   
    const onOpenRemarkHistory = async (data: any) => {
        // Function implementation for remark history
        try {
            //console.log('data.rm', data.rm.length)
            // if (data.rm.length === 0) {
            const RemarkHistory = await getPoogIRemarks(data.ok)
            //console.log('RemarkHistory', RemarkHistory?.data?.data)
            if (RemarkHistory.data?.data === 'No remarks are present for the order') {
                data.rm = []
            }
            else {
                data.rm = RemarkHistory.data?.data;
            }
            // }
            setRemarkHistory(data.rm)
            setIsRemarkHistoryOpen(true)
        }
        catch (e) {
            console.log(e);
        }
        setIsRemarkHistoryOpen(true)
    };

    const getSystemType = async () => {
        const DBRSettingsData: any = await getDBRsettingsData();
        const DBRSettings = DBRSettingsData.data?.data;
        const BomFlag = DBRSettings?.find((data: any) => data.flag === "BOMActive" && data.value==1);
        if(BomFlag){
            setBomActive(true)
        } else {
            setBomActive(false)
        }
        for(const setting of DBRSettings){
            if(setting.flag === "DeptwiseDefaultWIP"){
                setWIPCheck(setting.value == 1 ? true : false)
            }
        }  
        
    }

    useEffect(()=>{
        if(bomActive != undefined){
            setColumnDef();
        }
    },[bomActive])

   
     useEffect(()=>{
       if(coldefs && bomActive){
         getBOMUIConfigData()
       }
     }, [coldefs, bomActive])
   

      const getBOMUIConfigData = async () => {
        try {
          const response = await getUIConfigData(ReportName);
          setBomHeader(response?.data?.data)
        } catch (err) {
          console.error(err);
          notifyError("Something Went Wrong!");
        }
      };
    
       const columnBomDefs = useMemo(() => {
          return getColumnDefinations(bomHeader);
        }, [bomHeader]);


        const setColumnDef = async () => {
            try {
                const reportName = "DeptWiseReport";
                const response = await getUIConfigData(reportName);
                getGroupedColDef(response);
        
                const feature_permission = user?.feature_permission || [];
                const canAddComments = feature_permission.includes("Add_Comments");
        
                const gridOptions = {
                    bomActive: bomActive,
                    canAddComments: canAddComments,
                    onOpenRemarkHistory: onOpenRemarkHistory,
                    pinRemarkColumns: true,
                };
        
                const colDefsData = createDynamicColumnDefs(response?.data?.data || [], gridOptions, user);
                setColdef(colDefsData);
            } catch (e) {
                console.log(e);
                notifyError("Failed to build grid columns.");
            }
        };

    const getFilterData = async () => {
        try {
            const response = await getPageWiseFilterData({page_name: FilterPageName.Prod_Dept_Wise_BM_Report});
            setFilterData(response?.data.data);
        } catch (error) {
            console.error(error);
        }
    }

    useEffect(() => {
        getSystemType()
        // setColumnDef();
        // const colDefs = mapApiResponseToColDefs(apiResponse);
        // setColdef(colDefs)
        getFilterData();
    }, [])

    useEffect(() => {
        if (isFilteredDataLoaded) {
            toast.dismiss();
            notifyLoader("Loading Data ...")
        }
        else {
            toast.dismiss();
        }
    }, [isFilteredDataLoaded])

    const extractDepartmentNames = (orders: Orders): string[] => {
        const departmentNames: Set<string> = new Set();

        // Iterate over each order
        Object.values(orders).forEach(orderItem => {
            // Iterate over each property in the order item
            Object.keys(orderItem).forEach(key => {
                // Check if the property is a department (i.e., not 'tq' or 'li')
                if (key !== 'tq' && key !== 'li') {
                    departmentNames.add(key);
                }
            });
        });

        // Convert Set to Array and return
        return Array.from(departmentNames);
    };

    const allotementRef = useRef<any>();

    const fetcDeptWiseWiphData = async (selectedOrderKeys: any) => {
        try {
            notifyLoader("Loading")
            const DeptWiseWipData = await getDeptWiseWipData(selectedOrderKeys);
            const highAgeingData = await getHighAgeingData(selectedOrderKeys);
            sethighAgeing(highAgeingData?.data?.data);
            //console.log('HighAgeingData',highAgeingData)
            //console.log('DeptWiseWipData', DeptWiseWipData?.data?.data);
            setDeptWiseWipData(DeptWiseWipData?.data?.data);
            const departmentNames = extractDepartmentNames(DeptWiseWipData?.data?.data);
            //console.log('DeptWiseWipData===',departmentNames);
            departmentNames.sort()
            setDeptName(departmentNames);
            notifySuccess("Fetched");
        } catch (error) {
            notifyError('Failed to fetch data');
        }

    };

    const getSelectedRow = () => {
        const selectedData = refGraph1.current?.api.getSelectedRows();
        // To persist the state
        if (selectedData.length == 0) {
            setAreRowsSelected(false)
        } else {
            setAreRowsSelected(true);
        }
        if (selectedData) {
            let mergedData: any = [...masterSelectedRowData]; // Start with the existing selected data
            selectedData.forEach((newItem: any) => {
                const index = mergedData.findIndex((item: any) => item.ok === newItem.ok);
                if (index !== -1) {
                    // If the item exists, replace it
                    mergedData[index] = newItem;
                } else {
                    // Otherwise, add the new item
                    mergedData.push(newItem);
                }
            });

            gridData?.forEach((item: any) => {
                let isThere = 0;
                selectedData.forEach((selectedD: any) => {
                    if (selectedD.ok === item.ok) {
                        isThere = 1;
                    }
                })
                if (isThere == 0) {
                    mergedData = mergedData.filter((e: any) => e.ok !== item.ok)
                }
            })

            if (!_.isEqual(mergedData, masterSelectedRowData)) {
                setMasterSelectedRowData(mergedData);
            }
            //console.log("masterDataaa", mergedData)
            /*Persist state code end here*/
        }
    }

    useEffect(()=>{
        if (masterSelectedRowData.length > 0) {
            const selectedOrderKeys: orderkeyObj[] = []
            masterSelectedRowData.map((ele: any) => {
                selectedOrderKeys.push(ele.ok)
            })
            
            fetcDeptWiseWiphData(selectedOrderKeys);
            setIsOrderElapsedGrid(true)
        } else {
            setDeptWiseWipData('');
            setIsOrderElapsedGrid(false)
        }
    }, [masterSelectedRowData])

    // Handle cell value changes
    const onCellValueChanged = (event: any) => {
        if (event.data) {
            // const updatedSet = new Set(editedRows);
            // updatedSet.add(event.data.ok); // Assuming "ok" is the unique ID of the row
            // setEditedRows(updatedSet);
            setEditedRows(prev => new Set(prev.add(event.data.ok)));
        }
    };

    const handleUpdateReason = async () => {
        try {
            if (refGraph1.current) {
                // Get the grid API reference
                const api = refGraph1.current.api;

                // Ensure that any ongoing editing is stopped and values are committed
                api.stopEditing();
                const updatedRow = gridData.filter((row: any) => editedRows.has(row.ok))
                if (updatedRow.length > 0) {
                    const putData: UpdateRemarkObj[] = [];
                    updatedRow.forEach((e: any) => {
                        const singleData: any = {
                            "ok": e.ok,
                            "dept": e.did,
                            "rm": e.r,
                            "user": user?.user?.name
                        }
                        putData.push(singleData);
                        
                    })
                    const RemarkHistory = await addBMReportRemark(putData);
                    // }
                    if (RemarkHistory.status === 200) {
                        const newGridData = [...gridData].map((row) => {
                            const currentRemark = row.r || ""
                            if (editedRows.has(row.ok)) {
                                return {
                                    ...row,
                                    r: "",
                                    lr: currentRemark,  
                                }; 
                            }
                            return row;
                        });                
                        setGridData(newGridData);
                        setEditedRows(new Set());
                        notifySuccess('Remark saved successfully');
                    }
                    else {
                        notifyError('Failed to save the remark(s)')
                    }
                }
                else {
                    notifyError('Please add remarks/remark to save')
                }
            }
            return [];
        }
        catch (e) {
            console.log(e)
        }
    }

    const existsInSelected = (reqOk: string): boolean => {
        for (let index = 0; index < masterSelectedRowData.length; index++) {
            const element: any = masterSelectedRowData[index];
            if (element.ok === reqOk) {
                return true;
            }

        }
        return false;
    }

    const onFirstDataRendered = (params: any) => {
        const nodesToSelect: IRowNode[] = [];

        params.api.forEachNode((node: any) => {
            if (node.data && node.data.ok && existsInSelected(node.data.ok)) {
                node.data.Remark = masterSelectedRowData[0].Remark;
                for (let index = 0; index < masterSelectedRowData.length; index++) {
                    const element = masterSelectedRowData[index];
                    if (element.ok === node.data.ok) {
                        node.data.Remark = element.Remark;

                    }
                }
                nodesToSelect.push(node);
            }

        });
        params.api.setNodesSelected({ nodes: nodesToSelect, newValue: true });
    }


    const handlePageChange = async (currPage: number) => {
        //console.log('first,', currPage)
        setCurrentPage(currPage)
    }

    const savePageSize = (pageSize: any) => {
        if (pageSize) {
            setCurrentPage(1)
            setUserPageSize(pageSize);
            handleSaveClick(undefined, pageSize);
            getUpdatedFilteredData(1, pageSize);
        } else {
            notifyError("Invalide page size");
        }
        
    }


    const cache = useRef<any>({});

    const cellRendererParamsConfig =useMemo(() => {
    if(columnBomDefs){
    const itemNameColumnDef = columnBomDefs.find((a: any) => a.colId === "ItemName");

    const config = {
        masterDetail: bomActive ? true : false,
        detailCellRendererParams: {
        suppressMenu: true,
        detailGridOptions: {
            rowHeight: 28,
            headerHeight:30,
            domLayout: "autoHeight",
            autoGroupColumnDef: {
            headerName: itemNameColumnDef?.headerName,
            cellRendererParams: {
                suppressCount: true,
            },
            },
            columnDefs: columnBomDefs.filter((col: any) => col.colId !== "ItemName"),
            defaultColDef: {
            flex: 1,
            suppressMenu: true,
            cellStyle: {
                fontSize: "16px",
                display: "flex",
                alignItems: "center",
            },
            },
            treeData: true,
            getDataPath: (data: any) => {
            return data.path;
            },
        },
        getDetailRowData: async (params: any) => {
            if (!_.isEmpty(params.data)) {
                const cacheKey = `${params.data.ok}`;
                if (cache.current[cacheKey]) {
                    params.successCallback(cache.current[cacheKey]);
                    return;
                }
                const data = await getBOMExplosionData({
                    orderId: params.data.oid,
                    lineId: params.data.lid,
                });
                cache.current[cacheKey] = data?.data?.data;
                params.successCallback(data?.data?.data);
            }
        },
        },
    };

    return config
    }
    }, [columnBomDefs]);

    const onPivotModeChanged = (event: any) => {
        const isPivotOn = event.api.isPivotMode();
        setIsPivot(isPivotOn);
      };


    const agGridProps: AgGridReactProps = useMemo(()=>{
        return {
            tooltipShowDelay: 0,
            tooltipTrigger: "focus",
            gridOptions: {
                rowHeight: 50,
                getRowStyle: (params: any) => {
                    return {
                        background: params.node.rowIndex % 2 === 0 ? "#EBEBEB" : "#F7F7F7"
                    };
                },
                rowSelection: 'multiple',
                suppressRowClickSelection: true,
                enableBrowserTooltips: true,
                enableRangeSelection: true,
                enableFillHandle: true,
                components: customCellRenderers,
                pagination: true,
                defaultColDef: {
                    enablePivot: true,

                    filter: 'agTextColumnFilter',
                    floatingFilter: true,
                    //suppressFiltersToolPanel:true,
                    cellStyle: {
                        'text-align': 'center',
                        //'height': '50px',
                        //"font-style": "Roboto",
                        //"font-variant": "normal",
                        "font-size": "18px",
                        "font-family": "Roboto",
                        'white-space': 'nowrap',
                        'resizable': 'true',
                        'color': '#000'
                    },
                    // floatingFilterComponentParams: {
                    //     suppressFilterButton: true
                    // }
                },
            },
            sideBar: sideBar,
            //detailCellRenderer: RowGroupRenderer,
            //detailCellRendererParams:RowGroupRenderer,
            paginationAutoPageSize: true,
            enterNavigatesVertically: true,
            enterNavigatesVerticallyAfterEdit: true,
            groupDefaultExpanded: 0,
            // pivotMode: false,
            onSelectionChanged: debounce(getSelectedRow, 1000),
            onCellValueChanged: onCellValueChanged,
            stopEditingWhenCellsLoseFocus: true,
            onRowDataUpdated: onFirstDataRendered,
            onColumnPivotModeChanged: onPivotModeChanged,

        };
    }, [masterSelectedRowData, gridData])

    const getUpdatedFilteredData = async (page: any, pageSize?: any, isExcelExport=false, isBomExplosion=0) => {
        if (isExcelExport) {
            notifyLoader("Preparing data for export...");    
            const headersdata = refGraph1?.current?.api?.getColumnState();
            const formatedFilters = formatFilterJSON(appliedFilters);
            const body = getBodyForExcelExport({ headersdata, filterData: formatedFilters, groupedColDefsRef })
            try {
                const response = await getFilteredDeptWiseBMReportData({
                    "wip": isWIPChecked ? 1 : 0,
                    body,
                    appliedFilters: formatedFilters,
                    report_name: FilterPageName.Prod_Dept_Wise_BM_Report,
                    isExcelExport: 1,
                    isBomExplosion
                });
                if (response.status == 200) {
                    DownloadExcel(response, FilterPageName.Prod_Dept_Wise_BM_Report)
                    notifySuccess("Excel exported successfully!");
                } else {
                    notifyError("Error exporting Excel!");
                }
            } catch (e) {
                console.error("Error exporting Excel", e);
                notifyError("Error exporting Excel!");
            }
           
        } else {
            try {
                const formatedFilters = formatFilterJSON(appliedFilters);
                const gridData:any = await getFilteredDeptWiseBMReportData({
                    'wip': isWIPChecked ? 1 : 0,
                    'curr': page,
                    appliedFilters: formatedFilters,
                    page_size: pageSize || userPageSize
                });
               
                if (!gridData?.data?.data || gridData?.data?.data.length === 0 || gridData?.response?.data?.length === 0) {
                    setGridDataCount(0);
                    setGridData([])
                    return;
                }
                setGridData(gridData?.data?.data?.results)
                setGridDataCount(gridData?.data?.data?.count)
            }
            catch (e) {
                console.log(e);                
            }
        }
    }
    
    
    
    

        
        

    useEffect(() => {
        if (Object.keys(appliedFilters).length) {
            getUpdatedFilteredData(currentPage)
        }
    }, [isWIPChecked, currentPage]);


    useEffect(()=>{
        if (Object.keys(appliedFilters).length && userConfigFetched ) {
            if(currentPage != 1){
                setCurrentPage(1)
            }else{
                getUpdatedFilteredData(currentPage)
            }
        }
    }, [appliedFilters, userConfigFetched])


    const onExcelExport = () => {
        
      const gridApi = refGraph1?.current?.api;

      if(!gridApi){
        notifyError("Grid API not available for export.");
      }
      
        const isValue = gridApi.getValueColumns().length > 0;
        const isRowGroup = gridApi.getRowGroupColumns().length > 0;
        if (isPivot|| isValue || isRowGroup) {
             refGraph1.current?.api?.exportDataAsExcel({
                fileName: "DepartmentWiseBMReport",
                sheetName: "DepartmentWiseBMReport",
              });

        } else {
          if (bomActive) {
            setShowExcelModal(true)
          } else {
            getUpdatedFilteredData(1, userPageSize, true, 0);
          }
        }
      }


    useEffect(() => {
        if (coldefs) {
            const tempcoldeflatest = _.cloneDeep(coldefs);
            tempcoldeflatest.shift();
            tempcoldeflatest.shift();
            setTempColdef(tempcoldeflatest);
        }
    }, [coldefs])

    const getUserColumnConfig = async () => {
        try {
            const data = await getUserUIConfigData({
                un: user.user.name,
                rn_id: UIGridCode.ProdDeptWiseBMReport
            });

            const newConfig = data?.data?.data?.length? JSON.parse(data?.data?.data?.[0]?.columns_settings) || [] : [];
            setUserPageSize(newConfig.pageSize ? Number(newConfig.pageSize) : undefined);
            setColumnState(newConfig.cs);
            setIsPivot(newConfig.pivot);
            setUserConfigFetched(true);

            if (!data) {
                console.error('Failed to apply column state');
            }
        } catch (error) {
            console.error(error);
        }
    }

    const handleSaveClick = async (coldefs?: any,page_size?:any) => {
        try {
            if (coldefs) {
                const fullConfig = { pivot: false, cs: coldefs, pageSize: userPageSize };
                const payload = {
                    un: user.user.name,
                    rn_id: UIGridCode.ProdDeptWiseBMReport,
                    cs: JSON.stringify(fullConfig),
                };
    
                await updateUserUIConfigData([payload]);
                setColumnState([...coldefs]);
                setIsPivot(false);
              
            } else if (page_size) {
                const config = columnState;
                const isPivot = refGraph1.current?.api.isPivotMode();
                const fullConfig = { pivot: isPivot, cs: config, pageSize: page_size };
            
                const payload = {
                    un: user.user.name,
                    rn_id: UIGridCode.ProdDeptWiseBMReport,
                    cs: JSON.stringify(fullConfig),
                };
                await updateUserUIConfigData([payload]);
            
            } else {
                if (refGraph1?.current?.api) {
                    const config = refGraph1.current.api.getColumnState();
                    const isPivot = refGraph1.current?.api.isPivotMode();
                    const fullConfig = { pivot: isPivot, cs: config, pageSize: userPageSize };
                    // setColumnState(config)
                    const payload = {
                        un: user.user.name,
                        rn_id: UIGridCode.ProdDeptWiseBMReport,
                        cs: JSON.stringify(fullConfig),
                    };
                    await updateUserUIConfigData([payload]);
                    await getUserColumnConfig();
                }
            }
            notifySuccess("Changes saved successfully");
        } catch (error) {
            console.error(error);
            notifyError("Error saving changes");
        }
    };

   const handleResetClick = () => {
      setIsReset(true);
    };
  
    useEffect(() => {          
      if (isReset) {
        handleSaveClick(masterUIConfig);
        setIsReset(false);
      }
    }, [isReset]);
  
     useEffect(() => {
      if (refGraph1?.current?.api) {
        setMasterUIConfig(refGraph1?.current?.api.getColumnState());
        getUserColumnConfig();
      }
    }, [coldefs]);

    useEffect(() => {
        if (refGraph1?.current && columnState?.length) {
            const result = refGraph1.current.api.applyColumnState({
                state: columnState,
                applyOrder: true
            });
            const applyPivot = refGraph1.current?.api.setGridOption('pivotMode', isPivot);
            refGraph1.current.api.autoSizeAllColumns()
            if (!result || !applyPivot) {
                console.error('Failed to apply column state');
            }
        }
    }, [columnState,refGraph1,refGraph1.current]);
  
    const { data: apiResponseData, /*isLoading, refetch*/ } = useGetDate();

    const date = apiResponseData?.data?.data;

    const handleExcelConfirm = () => {
        setShowExcelModal(false);   
        getUpdatedFilteredData(1,userPageSize, true, 1)
    }

    const handleExcelCancel = () => {
        setShowExcelModal(false);   
        getUpdatedFilteredData(1,userPageSize, true,0)
    }

    return (
        <BMDepWrapper>
            <BMDepHeaderWraper>
                <MTOActionToolBar
                    comp={'DeptWiseBMReport'}
                    isAddFilterButton
                    themeUi={themeUi}
                    isExcelExport
                    onExcelExportClick={onExcelExport}
                    quickFilter={<div style={{ background: "#EFEFEF", borderRadius: "4px", padding: "1rem", display: "flex", alignItems: "center" }}>
                        <Checkbox
                            checked={isWIPChecked}
                            onChange={(e) => {
                                setCurrentPage(1)
                                setWIPCheck(e.target.checked)
                            }}
                            theme={themeUi}
                        />
                        &nbsp;&nbsp; <strong>Show order with available WIP Only</strong></div>}
                    isFilterOpen={isFilterOpen}
                    onAddFilter={onAddFilter}
                    toggleFilter={toggleFilter}
                    onApplyFilter={onApplyFilter}
                    multiFilter={currFilter}
                    setMultiFilter={setCurrFilter}
                    handleSaveClick={handleSaveClick}
                    handleResetClick={handleResetClick}
                    onFilterRemove={onFilterRemove}
                    isMfgSelected={isMfgSelected}
                />
            </BMDepHeaderWraper>
            <div style={{display: 'flex', justifyContent: 'center', alignItems: 'center', fontSize: '14px', fontWeight: 'bold', fontFamily: 'Roboto', marginTop: "10px",}}>
            <p>{(date && date.length)? moment(date).format('D MMM YYYY'): ""}</p>
            </div>

            <BomExcelModal
            open={showExcelModal}
            onClose={() => setShowExcelModal(false)}
            onConfirm={handleExcelConfirm}
            onCancel={handleExcelCancel}
            themeUi={themeUi}
            headerText={"Excel Export"}
            messageText={"Do you want to download Excel with BOM Data?"}
            />
            <>
                {
                    (isFilteredDataLoaded || isExcelLoading || isGetStateLoading) && <OverlayLoader /> }

                        <HorizontalViewWrapper style={{ marginTop: '0px', paddingLeft:"25px" }}>
                            <BTRTableWrapper style={{  height: areRowsSelected ? "120vh" : "75vh", margin: '0' }}>
                                <Allotment vertical={true} separator={true} ref={allotementRef}>
                                    <Allotment.Pane preferredSize={areRowsSelected ? "60%" : '70%'}>
                                        <BTRAllomentSection>
                                            <GridView
                                            // key={isReset? 1: 2}
                                            reference={refGraph1}
                                            agGridProps={agGridProps}
                                            detailCellRendererParamsConfig={cellRendererParamsConfig}
                                            columDef={coldefs}
                                            convercolumnDef={gridData}
                                            updateReason={handleUpdateReason}
                                            handlePageChange={handlePageChange}
                                            currentPage={currentPage}
                                            totalRow={gridDataCount}
                                            savePageSize={savePageSize}
                                            customPageSize={true}
                                            userPageSize={userPageSize}
                                                // onGridReady={() => {applyColumnState()}}
                                                />
                                        
                                        </BTRAllomentSection>
                                    </Allotment.Pane>

                                    <Allotment.Pane preferredSize={areRowsSelected ? "40%" : '30%'}>
                                        <BTRAllomentSection>
                                            <OrderElapsedGrid
                                                isTrue={isOrderElapsedGrid}
                                                data={deptWiseWipData}
                                                deptName={deptName}
                                                selectedOrderCount={masterSelectedRowData.length}
                                                highAgeingdata={highAgeing}
                                            />
                                        </BTRAllomentSection>
                                    </Allotment.Pane>
                                </Allotment>
                            </BTRTableWrapper>
                        </HorizontalViewWrapper>

                <div style={{ display: 'none' }}>
                    <GridView
                        reference={tempGraph}
                        agGridProps={agGridProps}
                        columDef={tempColdef}
                        convercolumnDef={tempGridData}
                        updateReason={() => handleUpdateReason()}
                        handlePageChange={(cp) => handlePageChange(cp)}
                        totalRow={gridDataCount}
                        currentPage={currentPage}
                        excelStyles={excelStyles}
                        detailCellRendererParamsConfig={cellRendererParamsConfig}                        
                    />
                </div>
            </>

            <BPRRemarkHistoryModal
                data={remarkHistory}
                isOpen={isRemarkHistoryOpen}
                onClose={() => setIsRemarkHistoryOpen(false)}
            />

        </BMDepWrapper>

    )
}

export default DptWiseBMReport;