import { useState, useMemo, useCallback, useEffect, useRef } from "react"
import { AgGridReact, AgGridReactProps } from "ag-grid-react"
import { useUserData } from "../../../../../../context"
import AvlCellRenderer from "../../../Common/AvlCellRenderer/AvlCellRenderer";
import AvailabilityToolTip from "../../../../../../VectorFlow/Pages/MTA/InsightsAndTrends/BTR/AvailabilityToolTip";
import { VFFloatingTabItemProps } from "../../../../../../components/VectorFLOW/commons/VFFloatingTab"
import VFTable from "../../../Common/VFTable";
import { useLocation } from 'react-router-dom';
import ColorCellRenderer from "../../../Common/ColorCellRenderer/ColorCellRenderer";
import { DownloadExcel, getBodyForExcelExport, getColumnDefinations } from '../../../../../../helpers/utils';
import DetailCellRenderer from "./DetailCellRenderer";
import { useGetProcAfterSimulationPlanningDataForExcelExport, userGetProcAfterSimulationPlanningData } from "../../../../../Services/MTO/Procurement/ProcPlanning/index";
import OverlayLoader from "../../../Common/Loader";
// import VFPagination from "../../../../../../components/VectorFLOW/commons/VFPagination";
import VFPagination from "../../../Common/VFPagination";
import { notifyError, notifySuccess } from "../../../../../../helpers/notify";
import { toast } from "react-toastify";
import { useGetUIConfigData } from '../../../../../../VectorFlow/Services/MTO/Common/UIConfig';
import { useGetUserUIConfigData, useUpdateUserUIConfigData } from "../../../../../../VectorFlow/Services/MTO/Common/UserUIConfig";
import { FilterPageName, UIGridCode } from "../../../Common/Enum";
import useColDef from "../../../../../../hooks/useColDef";
import ChildrenColor from "../../../Common/ChildrenColor/ChildrenColor";



const useSimFullKit = () => {
    const [HeaderData, setHeaderData] = useState([]);
    const { isSideBarOpen } = useUserData()
    const [currentPage, setCurrentPage] = useState<any>(1);
    const location = useLocation();
    const date = location.state?.date;
    const [currentGridRef, setCurrentGridRef] = useState<any>(null);
    const [columnState, setColumnState] = useState<any>([]);
    const [isReset, setIsReset] = useState(false);
    const [colDef, setColDef] = useState([{}]);
    const { mutateAsync: updateUserUIReportConfigData, isLoading: isUpdateUserConfig } = useUpdateUserUIConfigData();
    const { mutateAsync: getUserUIReportConfigData, isLoading: isGetUserConfig } = useGetUserUIConfigData();
    const [data, setData] = useState([]);
    const [incOrderFullkitData, setIncOrderFullKitData] = useState<any[]>([]);
    const [cumulativeFullKitData, setCumulativeFullKitDara] = useState<any[]>([]);
    const { mutateAsync: getUIConfigData } = useGetUIConfigData()
    const reportName = "SimulateFullkit";
    const childReportName = "ProcPlanningReport_Child"
    const gridRef = useRef<AgGridReact>(null);
    const { user } = useUserData();
    const [masterUIConfig, setMasterUIConfig] = useState([]);
    const { colDefMap, getColDef } = useColDef();
    const [totalRows, setTotalRows] = useState(0);
    const [HeaderDataChild, setHeaderDataChild] = useState([]);
    const [childColDef,setChildColDef] = useState<any>();
    const [isDisabled, setIsDisabled]= useState<boolean>(true)
    



    const { mutateAsync: userGetProcAfterSimulationData, isLoading, isSuccess, isError } = userGetProcAfterSimulationPlanningData();
    const { mutateAsync: userGetProcAfterSimulationDataForExcelExport } = useGetProcAfterSimulationPlanningDataForExcelExport();
    const toggleCurrentTab = (tab: VFFloatingTabItemProps) => setCurrentTab(tab);
    const tabs: Array<VFFloatingTabItemProps> = [
        {
            id: 'iof',
            label: 'Incremental Order In Full Kit',
            value: 'iof'
        },
        {
            id: 'cf',
            label: 'Cumulative Full Kit',
            value: 'cf'
        }
    ];
    const [currentTab, setCurrentTab] = useState<VFFloatingTabItemProps>(tabs[0]);


    const setColumnDef = async () => {
        try {
            const response = await getUIConfigData(reportName);
            const childResponse = await getUIConfigData(childReportName)
            getColDef(response)
            setHeaderData(response.data.data);
            setHeaderDataChild(childResponse.data.data)
        }
        catch (e) {
            console.log(e);
        }
    }

    const getUserColumnConfig = async () => {
        try {
            const data = await getUserUIReportConfigData({
                un: user.user.name,
                rn_id: UIGridCode.ProcPlanningSimulation
            });
    
            const newConfig = data?.data?.data[0]?.columns_settings ? JSON.parse(data?.data?.data[0]?.columns_settings) : [];
            setColumnState(newConfig);
    
            if (!data) {
                console.error('Failed to apply column state');
            }
        } catch (error) {
            console.error(error);
        }
    }

    const handleSaveClick = async (coldefs?: any) => {
        try {
            if (coldefs) {
                const payload = {
                    un: user.user.name,
                    rn_id: UIGridCode.ProcMaterialRequirement,
                    cs: JSON.stringify(coldefs),
                };
                await updateUserUIReportConfigData([payload]);
                setColumnState([...coldefs]);
                
            } else {
                if (currentGridRef?.current?.api) {
                    const config = currentGridRef.current.api.getColumnState();
                    const payload = {
                        un: user.user.name,
                        rn_id: UIGridCode.ProcPlanningSimulation,
                        cs: JSON.stringify(config)
                    }
                    await updateUserUIReportConfigData([payload]);
                    await getUserColumnConfig();
                }
            }
    
        } catch (error) {
            console.error(error);
        }
    }

    const handleResetClick = () => {
        setIsReset(true);
    }

    useEffect(() => {
        if (isReset) {
            handleSaveClick(masterUIConfig);
            setIsReset(false);
        }
    }, [isReset]);
    
    useEffect(() => {
        if (colDef.length > 1 && currentGridRef?.current) {
            setMasterUIConfig(currentGridRef?.current.api.getColumnState());
            getUserColumnConfig();
        }
    }, [colDef]);

    useEffect(() => {
        setColumnDef();
    }, [])

    const fetchData = useCallback(async (date: string, eas: string, pageNumber = '1', isExcelExport = false) => {
        if (isExcelExport) {
            try {
                const headersdata = gridRef?.current?.api.getColumnState();
                const body = getBodyForExcelExport({ headersdata:headersdata, colDefMap })
                const response = await userGetProcAfterSimulationDataForExcelExport({ date, body, eas, report_name: FilterPageName.Proc_Procurement_Planning, isExcelExport: 1 });
                if (response.status === 200) {
                    DownloadExcel(response);
                    notifySuccess('Excel Export Successfully')
                } else {
                    notifyError('Failed to export Excel')
                }
            } catch (error) {
                notifyError("Failed to export")
            }
        } else {
            try {
                const response = await userGetProcAfterSimulationData({ date, eas, pageNumber });
                setData(response?.data?.data?.results);
                setTotalRows(response?.data?.data.count);
                setCurrentPage(pageNumber)

            } catch (error) {
                console.log("error ", error);
            }
        }
    }, [userGetProcAfterSimulationData]);

    const ExcelExportData = () => {
        fetchData(date, currentTab.id === 'iof' ? '0' : '1', '1', true);
    }

    useEffect(() => {
        if (data && data.length !== undefined && HeaderData.length !== undefined) {
            const initilizeData = (data: any) => {
                const calculateData = data.map((item: any) => ({
                    ...item,
                    fkapr: ((item.fka / item.oq) * 100).toFixed(2)
                }));
                const WithZeroEas = calculateData.filter((item: any) => item.children.every((child: any) => child.eas === 0));
                const WithoutZeroEas = calculateData.filter((item: any) => item.children.every((child: any) => child.eas !== 0));


                const BothEasData = calculateData.filter((item: any) => {
                    return item.children.some((child: any) => child.eas === 0) && item.children.some((child: any) => child.eas !== 0);
                });
                // setIncOrderFullKitData([...WithoutZeroEas, ...BothEasData]);
                // setCumulativeFullKitDara([...WithZeroEas, ...BothEasData]);
                setIncOrderFullKitData(calculateData);
                setCumulativeFullKitDara(calculateData);
                return { WithZeroEas, WithoutZeroEas, BothEasData };
            };
            initilizeData(data);
        }
    }, [data]);

    const CustomDef = {
        ic: {
            headerName: '',
            cellRenderer: 'agGroupCellRenderer',
            cellStyle: {
                width: 50,
                maxWidth: 50,
            },
            initialWidth: 40,
        },
        ColorPriority: {
            cellRenderer: "colorCellRenderer",
            initialWidth: 200,//160
            autoHeaderHeight: true,
            wrapHeaderText: true,
        },
        FullKitsAvail: {
            cellRenderer: "avlCellRenderer",
            tooltipComponent: 'availabilityToolTip',
            tooltipValueGetter: (params: any) => {
                const oq = params.data.oq;
                const fka = params.data.fka;
                return `${fka}/${oq} kits can be manufactured`;
            },
            initialWidth: 200,//160
            autoHeaderHeight: true,
            wrapHeaderText: true,
            filter: 'agMultiColumnFilter',
            floatingFilter: true,

        }
    }

    useEffect(() => {
        setColDef(getColumnDefinations(HeaderData, CustomDef, []))
        const childColDefs = getColumnDefinations(HeaderDataChild,childCustomheader)
        setChildColDef(childColDefs)

    }, [HeaderData,HeaderDataChild])

    const icons = useMemo(() => {
        return {
            groupExpanded: `<img src="${'/assets/img/mto/dayWiseCoverage/collapse.svg'}" style="height: 100%; width: 80%;"/>`,
            groupContracted: `<img src="${'/assets/img/mto/dayWiseCoverage/expand.svg'}" style="height: 100%; width: 80%;"/>`,
        };
    }, []);

    const autoGroupColumnDef = useMemo(() => {
        return {
            minWidth: 250,
        };
    }, []);

    useEffect(() => {

        if (isError) {
            toast.dismiss();
            notifyError("Failed to fetch data!")
        }
        if (isSuccess) {
            notifySuccess("Fetched Data Successfully!")
        }

    }, [isError, isSuccess])

    const handlePageChangeCumulative = async (pageNumber: number) => {
        // setIsLoading(true);
        // setCurrentPage(pageNumber);
        // const APIData = await getProcPlanningData({ date, pageNum: currentPage.toString() });
        // // setData(APIData)
        // const newDat = APIData.data.data.results
        // setTotalRows(APIData?.data?.data?.count)
        // // setData(APIData?.data?.data?.results || []);
        // setData(newDat);
        // setIsLoading(false);

        if (currentTab.id === 'iof') {

            fetchData(date, '0', pageNumber.toString());

        }
        else {
            fetchData(date, '1', pageNumber.toString());
        }

        // (refGraph1.current?.api.getRowNode) && refGraph1.current?.api.set
    };

    const customCellRenderers = useMemo(() => (
        {
            "colorCellRenderer": ColorCellRenderer,
            "avlCellRenderer": AvlCellRenderer,
            "availabilityToolTip": AvailabilityToolTip
        }), []);


    useEffect(() => {
        if (currentTab.id === 'iof') {
            fetchData(date, '0');
        }
        else {
            fetchData(date, '1');
        }
    }, [currentTab])
    
    useEffect(() => {
        if (currentGridRef?.current && columnState?.length && colDef.length > 0) {
            const result = currentGridRef?.current?.api?.applyColumnState({
                state: columnState,
                applyOrder: true
            });
            if (!result) {
                console.error('Failed to apply column state');
            }
        }
    });

    const renderView = () => {
        switch (currentTab.id) {
            case "iof":
                return (
                    <>
                        {(isLoading || isUpdateUserConfig || isGetUserConfig) && <OverlayLoader />}
                        <VFTable
                            {...agGridProps}
                            columnDefs={colDef}
                            rowData={incOrderFullkitData}
                            tooltipHideDelay={100000}
                            tooltipShowDelay={0}
                            tooltipMouseTrack={true}
                            // height={'750px'}
                            ref={gridRef}
                            onGridReady={(params: any) => {
                                params.api.autoSizeAllColumns();
            
                                setCurrentGridRef(gridRef);
                            }}
                            onFilterChanged={()=>{Object.keys((currentGridRef?.current?.api?.getFilterModel()))?.length>0 ? setIsDisabled(false) : setIsDisabled(true)}}
                        />
                        <VFPagination
                            key={1}
                            selectedRows={0}
                            rowsPerPage={Math.min(500, totalRows)}
                            totalRows={totalRows}
                            currentPage={currentPage}
                            handleChangePage={handlePageChangeCumulative}
                            isDisabled={isDisabled}
                            resetGridRef={gridRef}
                        />

                    </>
                );
            case "cf":
                return (
                    <>
                        {(isLoading || isUpdateUserConfig || isGetUserConfig) && <OverlayLoader />}
                        <VFTable
                            {...agGridProps}
                            columnDefs={colDef}
                            rowData={cumulativeFullKitData}
                            tooltipHideDelay={100000}
                            tooltipShowDelay={0}
                            tooltipMouseTrack={true}
                            // height={'750px'}
                            ref={gridRef}
                            onGridReady={(params: any) => {
                                params.api.autoSizeAllColumns();
            
                                setCurrentGridRef(gridRef);
                            }}
                            onFilterChanged={()=>{Object.keys((currentGridRef?.current?.api?.getFilterModel()))?.length>0 ? setIsDisabled(false) : setIsDisabled(true)}}
                        />
                        <VFPagination
                            key={1}
                            selectedRows={0}
                            rowsPerPage={Math.min(500, totalRows)}
                            totalRows={totalRows}
                            currentPage={currentPage}
                            handleChangePage={handlePageChangeCumulative}
                            isDisabled={isDisabled}
                            resetGridRef={gridRef}
                        />
                    </>
                );
            default:
                return <VFTable columnDefs={[]} rowData={[]} {...agGridProps} />
        }
    }
    const childCustomheader = {
        clr:{
          cellRenderer : ChildrenColor
        },
      }

    const agGridProps: AgGridReactProps = {
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
            components: customCellRenderers,
            icons: icons,
            defaultColDef: {
                suppressMenu: true,
                resizable: true,
                filter: "agMultiColumnFilter",
                cellStyle: {
                    'textAlign': 'center',
                    'height': '50px',
                    "fontStyle": "normal",
                    "fontVariant": "normal",
                    "fontWeight": "300",
                    "fontSize": "20px",
                    "fontFamily": "Roboto",
                    'textOverflow': 'ellipsis',
                    'whiteSpace': 'nowrap',
                    'resizable': 'true',
                    'width': '200px'
                },

            },
        },
        masterDetail: true,
        detailCellRenderer: DetailCellRenderer,
        detailCellRendererParams:{
            colDef : childColDef
        },
   
        autoGroupColumnDef: autoGroupColumnDef,
        paginationAutoPageSize: true,
        enterNavigatesVertically: true,
        enterNavigatesVerticallyAfterEdit: true,
    };

    return {
        isSideBarOpen,
        agGridProps,
        currentPage,
        toggleCurrentTab,
        renderView,
        currentTab,
        handleSaveClick,
        handleResetClick,
        ExcelExportData,
        childColDef
    }
}

export default useSimFullKit;