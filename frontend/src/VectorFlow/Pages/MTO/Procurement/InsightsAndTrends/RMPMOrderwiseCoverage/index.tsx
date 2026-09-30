import { useState, useEffect } from 'react'
import ActionToolBar from '../../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar'
import GridView from './GridView/GridView'
import GraphView from './GraphView/GraphView'
import { InsightsAndTrendsString } from '../../../Common/String'
import { Order } from '../../../../../../VectorFlow/types/MTO'
import { ColDef } from 'ag-grid-enterprise'
import columnData from './ColumnData'
import { AgGridReactProps } from 'ag-grid-react'
import { useGetOrderwiseCoverageData, useGetOrderwiseCoverageDataForExcelExport } from '../../../../../../VectorFlow/Services/MTO/Procurement/OrderwiseCoverage'
import { toast } from 'react-toastify'
import { notifyError, notifyLoader, notifySuccess } from '../../../../../../helpers/notify'
import { useGetUIConfigData } from '../../../../../../VectorFlow/Services/MTO/Common/UIConfig'
import { DownloadExcel, formatFilterJSON, getBodyForExcelExport, getColumnDefinations } from '../../../../../../helpers/utils'
import FullkitCellRenderer from '../../../Common/FullKitCellRenderer/FullkitCellRenderer'
import { FilterPageName, pagination, UIGridCode } from '../../../Common/Enum'
import { useGetUserUIConfigData, useUpdateUserUIConfigData } from '../../../../../../VectorFlow/Services/MTO/Common/UserUIConfig'
import { useUserData } from "../../../../../../context/index";
import OverlayLoader from '../../../Common/Loader'
import { useGetFilterData } from '../../../../../..//VectorFlow/Services/MTO/Common/CommonFilter';
import useFilter from '../../../../../../hooks/useFilter';
import useColDef from '../../../../../../hooks/useColDef'
import BPPRenderer from '../../../Common/BPRRenderer/BPPRenderer'

const APIFilterConfig = {
    filSecVisConfig: {
        "Proc_RM_PM_OrderWise" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
    }
};

const RMPMOrderwiseCoverage = () => {

    const [isGridView, setIsGridView] = useState(false);
    const [convertedData, setConvertedData] = useState([{}]);
    const [GraphDatas, setGraphDatas] = useState([{}])
    const [apiGraphData, setApiGraphData] = useState([{}]);
    const [apiGridData, setApiGridData] = useState([{}]);
    const [currentGridRef, setCurrentGridRef] = useState<any>(null);
    const [columnState, setColumnState] = useState<any>([]);
    const [isReset, setIsReset] = useState(false);
    const [colDef, setColDef] = useState([{}]);
    const [filterData, setFilterData] = useState({});
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
    } = useFilter(filterData, APIFilterConfig.filSecVisConfig.Proc_RM_PM_OrderWise);
    const { mutateAsync: updateUserUIReportConfigData, isLoading: isUpdateUserConfig } = useUpdateUserUIConfigData();
    const { mutateAsync: getUserUIReportConfigData, isLoading: isGetUserConfig } = useGetUserUIConfigData();
    const { mutateAsync: getUIConfigData } = useGetUIConfigData()
    const { mutateAsync: getOrderwiseCoverageData } = useGetOrderwiseCoverageData();
    const { user } = useUserData();
    const { mutateAsync: getOrderwiseCoverageDataForExcelExport } = useGetOrderwiseCoverageDataForExcelExport();
    const { colDefMap, getColDef } = useColDef()
    const reportName = "RMPMOrderWiseCoverage";
    const [masterUIConfig, setMasterUIConfig] = useState([]);
    const [currentPage, setCurrentPage] = useState<number>(1);
    const [orderWiseRecordCount, setOrderWiseRecordCount] = useState<number>(0);

    const [userConfigFetched, setUserConfigFetched] = useState<any>(false);
    const [userPageSize, setUserPageSize] = useState<any>();

    const themeUi = user?.user?.theme_ui;

    const agGridProps: AgGridReactProps = {
        tooltipShowDelay: 0,
        tooltipTrigger: "focus",
        sideBar: {
            toolPanels: [
                {
                    id: 'columns',
                    labelDefault: 'Columns',
                    labelKey: 'columns',
                    iconKey: 'columns',
                    toolPanel: 'agColumnsToolPanel',
                    minWidth: 225,
                    maxWidth: 225,
                    width: 225
                }
            ],
        },

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

            pagination: true,
            paginationAutoPageSize: false,
            paginationPageSize: pagination.mtoPageSize,

            defaultColDef: {
                filter: "agTextColumnFilter",
                floatingFilter: true,
                suppressMenu: true,
                resizable: true,

                cellStyle: {
                    'text-align': 'center',
                    'height': '50px',
                    "font-style": "normal",
                    "font-variant": "normal",
                    "font-weight": "300",
                    "font-size": "20px",
                    "font-family": "Roboto",
                    'text-overflow': 'ellipsis',
                    'white-space': 'nowrap',
                    'resizable': 'true',
                },
                flex: 1,
                // floatingFilterComponentParams: { suppressFilterButton: true },
            },

        },
        masterDetail: true,

        paginationAutoPageSize: true,
        enterNavigatesVertically: true,
        enterNavigatesVerticallyAfterEdit: true,
        groupDefaultExpanded: 0,

        onCellEditingStopped(event: any) {
            const field = event.colDef.field;
            // const newValue = event.newValue;
            const rowIndex = event.rowIndex;

            if (!field || rowIndex == null) {
                return;
            }
        }
    };

    // const customColumnDefs = {
    //     BPP: {
    //         cellRenderer: ColorCellRenderer,
    //     }
    // }

    const customHeader = {
        BPP: {
            cellRenderer: BPPRenderer,
            autoHeaderHeight: true,
            wrapHeaderText: true,
            minWidth:100
        },
        FullKitAvailable: {
            cellRenderer: FullkitCellRenderer,
            cellStyle: {
                paddingRight: '20px'
            },
        },
        RMPMCoverage: {
            minWidth: 300,
        }
    }

    const setColumnDef = async () => {
        try {
            const response = await getUIConfigData(reportName);
            getColDef(response)
            setColDef(getColumnDefinations(response?.data?.data, customHeader, []));
        }
        catch (e) {
            console.log(e);
        }
    }

    const mapDataToColumns = (data: any, columns: ColDef[]) => {

        return data?.map((item: any) => {

            const rmpmColumnExist = columns.find((col) => col.field == "rmpm");

            if (rmpmColumnExist && rmpmColumnExist.field) {
                if (item['or'] > 0) {
                    item[rmpmColumnExist.field]=InsightsAndTrendsString.ordersWithRMPM;
                }
                else if (item['po'] > 0) {
                    item[rmpmColumnExist.field] = InsightsAndTrendsString.ordersWithFullkitOPO;
                }
                else if (item['sit'] > 0) {
                    item[rmpmColumnExist.field] = InsightsAndTrendsString.ordersWithFullkitSIT;
                }
                else {
                    item[rmpmColumnExist.field] = InsightsAndTrendsString.ordersWithFullkitOHS;
                }
            }

            return item;

        });
    };

    const GetData = async (graph: any, page: any, isExcelExport = false,pageSize?:any) => {
        if (isExcelExport) {
            try {
                const headersdata = currentGridRef?.current?.api.getColumnState();
                const formatedFilters = formatFilterJSON(appliedFilters)
                const body = getBodyForExcelExport({ headersdata, filterData: formatedFilters, colDefMap })
                const response = await getOrderwiseCoverageDataForExcelExport({ body, isExcelExport: 1, report_name: FilterPageName.Proc_RM_PM_OrderWise, graph });
                if (response.status === 200) {
                    DownloadExcel(response, FilterPageName.Proc_RM_PM_OrderWise,);
                } else {
                    notifyError("An error occurred while downloading")
                }
                
            } catch (error) {
                notifyError("An error occurred");
                console.log(error)

            }
        }
        else if (graph === 1) {
            try {
                notifyLoader("Loading Data...")
                const APIData = await getOrderwiseCoverageData({ graph });
                if (APIData.status.toString() === '200') {
                    toast.dismiss();
                    setApiGraphData(APIData?.data?.data);
                    notifySuccess("Data Fetched Successfully!")
                }
                else {
                    toast.dismiss();
                    notifyError("Failed to fetch Data");
                }
                
            } catch (e) {
               console.log(e)
            }
        }
        else {
            try {
                notifyLoader("Loading Data...")
                const formatedFilters = formatFilterJSON(appliedFilters);
                const APIData = await getOrderwiseCoverageData({ graph, page: page ? page : currentPage, appliedFilters: formatedFilters, page_size: pageSize || userPageSize });
                if (APIData.status.toString() === '200') {
                    toast.dismiss();
                    setApiGridData(APIData?.data?.data?.results || []);
                    setOrderWiseRecordCount(APIData.data?.data?.count || 0);
                    notifySuccess("Data Fetched Successfully!")
                }
               
            } catch (e) {
                toast.dismiss();
                notifyError("Failed to fetch Data");
            }

        }

    }

    const handlePageChangeDayWise = async (currPage: number) => {
        setCurrentPage(currPage);
        await GetData(0, currPage);
    }

    const getUserColumnConfig = async () => {
        try {
            const data = await getUserUIReportConfigData({
                un: user.user.name,
                rn_id: UIGridCode.ProcRMPMOrderCov
            });
            setUserConfigFetched(true)
            const newConfig = data?.data?.data[0]?.columns_settings ? JSON.parse(data?.data?.data[0]?.columns_settings) : [];
            setUserPageSize(newConfig.pageSize ? Number(newConfig.pageSize) : undefined);
            setColumnState(newConfig.cs);
    
            if (!data) {
                console.error('Failed to apply column state');
            }
        } catch (error) {
            console.error(error);
        }
    }

    const handleSaveClick = async (coldefs?: any,page_size?: any) => {
        try {
            if (coldefs) {
                const fullConfig = {cs: coldefs, pageSize: userPageSize };
              
                const payload = {
                    un: user.user.name,
                    rn_id: UIGridCode.ProcRMPMOrderCov,
                    cs: JSON.stringify(fullConfig),
                };
                await updateUserUIReportConfigData([payload]);
                setColumnState([...coldefs]);
        
            }
            else if(page_size){
                const config = columnState;
                const fullConfig = { cs: config, pageSize: page_size };        
                const payload = {
                  un: user.user.name,
                  rn_id: UIGridCode.ProcRMPMOrderCov,
                  cs: JSON.stringify(fullConfig),
                };
                await updateUserUIReportConfigData([payload]);
              }
             else {
                if (currentGridRef?.current?.api) {
                    const config = currentGridRef.current.api.getColumnState();
                    const fullConfig = {  cs: config, pageSize: userPageSize };
                    const payload = {
                        un: user.user.name,
                        rn_id: UIGridCode.ProcRMPMOrderCov,
                        cs: JSON.stringify(fullConfig)
                    }
                    await updateUserUIReportConfigData([payload]);
                    await getUserColumnConfig();
                }

            }
            
        } catch (error) {
            console.error(error);
        }
    }

    const savePageSize = (pageSize: any) => {
        if (pageSize) {
            setCurrentPage(1)
            setUserPageSize(pageSize);
            handleSaveClick(undefined, pageSize);
            GetData(0,1,false, pageSize);
        } else {
            notifyError("Invalide page size");
        }
        
    }

    const handleResetClick = () => {
        setIsReset(true);
    }
   
    const getFilterData = async () => {
        try {
            const response = await getPageWiseFilterData({ page_name: FilterPageName.Proc_RM_PM_OrderWise });
            setFilterData(response?.data?.data);
        } catch (error) {
            console.error(error);
        }
    }

    useEffect(() => {
        setColumnDef();
        GetData(1, 1);
        getFilterData()
    }, [])

    useEffect(() => {
        if (Object.entries(appliedFilters).length > 1 && userConfigFetched) {
            setCurrentPage(1);
            GetData(0, 1);
        }
    }, [appliedFilters,userConfigFetched]);

    useEffect(() => {
        setConvertedData(mapDataToColumns(apiGridData, columnData));
    }, [apiGridData])

    useEffect(() => {
        setGraphDatas(apiGraphData)
    }, [apiGraphData])

    useEffect(() => {
        if (isReset) {
            handleSaveClick(masterUIConfig);
            setIsReset(false);
        }
    }, [isReset]);

    useEffect(() => {
        if (currentGridRef?.current) {
            setMasterUIConfig(currentGridRef?.current.api.getColumnState());
            getUserColumnConfig();
        }
    }, [colDef, currentGridRef]);

    const ExcelExport = () => {
        GetData(0, 0, true)
    }

    return (
        <>
            {(isUpdateUserConfig || isGetUserConfig) && <OverlayLoader />}
            <div style={{ display: 'flex', flexDirection: 'column', height: "100%" }}>


                <ActionToolBar 
                    comp={"rmpm"} 
                    // isGoBackButton={isGridView} 
                    handleGoBack={() => { (setIsGridView(false)) }} 
                    isAddFilterButton={isGridView ? true : false}
                    isChartGridToggle
                    themeUi={themeUi}
                    isExcelExport = {isGridView ? true : false}
                    onExcelExportClick = {ExcelExport}
                    isGridView={isGridView} 
                    setIsGridView={setIsGridView} 
                    isFilterOpen={isFilterOpen}
                    onAddFilter={onAddFilter}
                    toggleFilter={toggleFilter}
                    onApplyFilter={onApplyFilter}
                    multiFilter={currFilter}
                    setMultiFilter={setCurrFilter}
                    onFilterRemove={onFilterRemove}
                    isMfgSelected={isMfgSelected}
                    handleSaveClick={handleSaveClick}
                    handleResetClick={handleResetClick}
                />

                <div style={{ flex: '1' }}>

                    {(isGridView) ?
                        <GridView
                            agGridProps={agGridProps}
                            colDef={colDef}
                            ShortageDatas={convertedData}
                            setCurrentGridRef={setCurrentGridRef}
                            currentGridRef={currentGridRef}
                            columnState={columnState}
                            orderWiseRecordCount={orderWiseRecordCount}
                            currentPage={currentPage}
                            handlePageChangeDayWise={handlePageChangeDayWise}
                            userPageSize={userPageSize}
                            savePageSize={savePageSize}
                        /> : <GraphView shortageData={GraphDatas} />}
                </div>
            </div>
        </>
    )
}
export default RMPMOrderwiseCoverage
