import { useState, useMemo, useRef, useEffect /*useCallback*/ } from "react"
import { AgGridReactProps } from "ag-grid-react"
// import { useUserData } from "../../../../../context"
import ColorPriority from '../../Common/ColorPriority/index';
import AvailabilityToolTip from "../../../MTA/InsightsAndTrends/BTR/AvailabilityToolTip";
import { VFFloatingTabItemProps } from "../../../../../components/VectorFLOW/commons/VFFloatingTab"
import VFTable from "../../Common/VFTable";
//import { useNavigate } from "react-router-dom";
import { ProcessRowGroupForExportParams, ExcelCell, ExcelRow, ExcelExportParams, ExcelStyle } from 'ag-grid-community';
// import GetProcPlanningData from '../Planning/GetProcPlanningData.json';
// import GetProcPlanningDataColumn from '../Planning/GetProcPlanningDataColumn.json';
import { DownloadExcel, formatFilterJSON, getBodyForExcelExport, getColumnDefinations } from '../../../../../helpers/utils';
import ChildrenProcPlanningCellRenderer from "../ChildrenProcPlanningCellRenderer";
import { useGetMaterialRequirementDetails, useGetMaterialRequirementDetailsDatewise, useGetMaterialRequirementDetailsForExcelExport } from "../../../../../VectorFlow/Services/MTO/Procurement/MaterialRequirement";
import moment from "moment";
import { useGetUIConfigData } from "../../../../../VectorFlow/Services/MTO/Common/UIConfig";
import VFPagination from "../../Common/VFPagination";
import { TableWrapper } from "./styles";
import { FilterPageName, pagination,UIGridCode } from "../../Common/Enum";
import { useGetUserUIConfigData, useUpdateUserUIConfigData } from "../../../../../VectorFlow/Services/MTO/Common/UserUIConfig";
import { useUserData } from "../../../../../context"
import useColDef from "../../../../../hooks/useColDef";
import { notifyError, notifySuccess } from "../../../../../helpers/notify";
import _ from "lodash";

const getRows = (params: ProcessRowGroupForExportParams) => {
    
    const children = params.node.data?.children;

    if (!children || !Array.isArray(children)) {
        return [];
    }

    const rows: ExcelRow[] = [
        {
            outlineLevel: 1,
            cells: [
                cell(""),
                cell(""),
                cell("Order No", "header"),
                cell("Order Qty", "header"),
                cell("Cust Name", "header"),
                cell("Cust Code", "header"),
                cell("Order Due Date", "header"),
                cell("Order Release Date", "header"),
            ],
        },
    ].concat(
        ...params.node.data.children.map((record: any) => [
            {
                outlineLevel: 1,
                cells: [
                    cell(""),
                    cell(""),
                    cell(record.on, "body"),
                    cell(record.oq, "body"),
                    cell(record.cn, "body"),
                    cell(record.cc, "body"),
                    cell(record.odd, "body"),
                    cell(record.ord, "body"),
                ],
            },
        ]),
    );
    return rows;
};
const cell: (text: string, styleId?: string) => ExcelCell = (
    text: string,
    styleId?: string,
) => {
    return {
        styleId: styleId,
        data: {
            type: /^\d+$/.test(text) ? "Number" : "String",
            value: String(text),
        },
    };
};

const useMaterialReq = (appliedFilters: any, forDate?: string) => {
    
    const format2 = "YYYY-MM-DD"
    const d = forDate ? new Date(forDate) : new Date();
    const datetime = moment(d).format(format2);
    const [HeaderData, setHeaderData] = useState([{}]);
    const [currentGridRef, setCurrentGridRef] = useState<any>(null);
    const [columnState, setColumnState] = useState<any>([]);
    const [isReset, setIsReset] = useState(false);
    const [colDef, setColDef] = useState([{}]);
    const { mutateAsync: updateUserUIReportConfigData, isLoading: isUpdateUserConfig } = useUpdateUserUIConfigData();
    const { mutateAsync: getUserUIReportConfigData, isLoading: isGetUserConfig } = useGetUserUIConfigData();
    const { mutateAsync: getUIConfigData } = useGetUIConfigData()
    const { user } = useUserData();
    const { colDefMap, getColDef } = useColDef()
    const { mutateAsync: getMaterialRequirementDataExcelExport } = useGetMaterialRequirementDetailsForExcelExport();
    const [masterUIConfig, setMasterUIConfig] = useState([]);
    const [isDisabled, setIsDisabled]= useState<boolean>(true);

    const [userConfigFetched, setUserConfigFetched] = useState<any>(false);
    const [userPageSize, setUserPageSize] = useState<any>();

    const reportName = "MaterialRequirement";

    const setColumnDef = async () => {
        try {
            const response = await getUIConfigData(reportName);
            getColDef(response)
            setHeaderData(response?.data?.data);
        }
        catch (e) {
            console.log(e);
        }
    }

    const getUserColumnConfig = async () => {
        try {
            const data = await getUserUIReportConfigData({
                un: user.user.name,
                rn_id: UIGridCode.ProcMaterialRequirement
            });
            const newConfig = data?.data?.data[0]?.columns_settings ? JSON.parse(data?.data?.data[0]?.columns_settings) : [];
            setUserPageSize(newConfig.pageSize ? Number(newConfig.pageSize) : undefined);
            setColumnState(newConfig.cs);
            setUserConfigFetched(true)
    
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
                    rn_id: UIGridCode.ProcMaterialRequirement,
                    cs: JSON.stringify(fullConfig),
                };
                await updateUserUIReportConfigData([payload]);
                setColumnState([...coldefs]);
                
            }
            else if(page_size){
                const config = currentGridRef.current.api.getColumnState(); 
                const fullConfig = { cs: config, pageSize: page_size };        
                const payload = {
                  un: user.user.name,
                  rn_id: UIGridCode.ProcMaterialRequirement,
                  cs: JSON.stringify(fullConfig),
                };
                await updateUserUIReportConfigData([payload]);
              }
            
            else {
                if (currentGridRef?.current?.api) {
                    const config = currentGridRef.current.api.getColumnState(); 
                    const fullConfig = { cs: config, pageSize:  userPageSize };
                    const payload = {
                        un: user.user.name,
                        rn_id: UIGridCode.ProcMaterialRequirement,
                        cs: JSON.stringify(fullConfig),
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
    }, [colDef,currentGridRef]);

    useEffect(() => {
        setColumnDef();
    }, [])

    const gridRef = useRef<any>(null);
    // const { isSideBarOpen } = useUserData()
    const tabs: Array<VFFloatingTabItemProps> = [
        {
            id: 'sdv',
            label: 'Selected Day View',
            value: 'sdv'
        },
        {
            id: 'cv',
            label: 'Cummulative View',
            value: 'cv'
        }
    ];

    const customHeader = {
        ColorPriority: {
            cellRenderer: 'coloPriority',
            tooltipValueGetter: (params: any) => {
                if (!_.isEmpty(params.data)) {
                    const cpData = params.data.cp[0];
                    const keysToPrint = ["B", "R", "Y", "G", "W", "Bl"];
                    let tooltipText = '';
                    keysToPrint.forEach((key) => {
                        if (Object.prototype.hasOwnProperty.call(cpData, key)) {
                            if (tooltipText !== '') {
                                tooltipText += ' | ';
                            }
                            tooltipText += `${key}: ${cpData[key]}`;
                        }
                    });
                    return tooltipText;
                }
            },
            tooltipComponent: "availabilityToolTip",
            initialWidth: 200, //160
            autoHeaderHeight: true,
            wrapHeaderText: true,

        },
        "net_r": {
            valueFormatter: (params: any) => !_.isEmpty(params.data) ? Math.max(0, Number(params.data.net_r)) : undefined
        }

    }
    const [currentTab, setCurrentTab] = useState<VFFloatingTabItemProps>(tabs[0]);
    const [CumulativeData, SetCumulativeData] = useState<any[]>([]);
    const [DayWiseData, setDayWiseData] = useState<any[]>([]);
    const { mutateAsync: getMaterialRequirementData, isLoading: isMatReqLoading } = useGetMaterialRequirementDetails();
    const { mutateAsync: getMaterialRequirementDataDayWise, isLoading: isMatReqDayWiseLoading } = useGetMaterialRequirementDetailsDatewise();
    const [currentPage, setCurrentPage] = useState<number>(1);
    const [currentCumPage, setcurrentCumPage] = useState<number>(1);
    const [dayWiseRecordCount, setDayWiseRecordCount] = useState<number>(0);
    const [cumulativeRecordCount, setcumulativeRecordCount] = useState<number>(0);
    const [date, setDate] = useState<string>(datetime);
    

    useEffect(() => {
        setColDef(getColumnDefinations(HeaderData, customHeader));
    }, [HeaderData]);


    useEffect(() => {
        if (appliedFilters !== null && Object.entries(appliedFilters).length) {
            if (currentTab.id === 'sdv') {
                setCurrentPage(1);
            } else if (currentTab.id === 'cv') {
                setcurrentCumPage(1);
            }
        }
        if(userConfigFetched){
            getInitialData();
        }
    }, [currentTab, appliedFilters, userConfigFetched])

    useEffect(() => {
        if (forDate) {
            const d = new Date(forDate);
            const datetime = moment(d).format(format2);
            onDateChangeReq(datetime);
            // getInitialData(currentPage, forDate);
        }
    }, [forDate])


    const onDateChangeReq = (date: string) => {
        setDate(date);
    }

    const onDateSubmitReq = () => {
        // getInitialData()
    }

    const onExcelExportClickReq = () => {
        getInitialData(0, date, true)
    }

    const getInitialData = async (currPage?: number, releaseDate?: string, isExcelExport = false, pageSize?:any ) => {
         currentTab.id === 'sdv' ? getSelectedDateWise(currPage, releaseDate, isExcelExport, pageSize ) : getCumulativeDateWise(currPage, releaseDate, isExcelExport, pageSize );
    }

    const getSelectedDateWise = async (currPage?: number, releaseDate: string = date, isExcelExport = false, pageSize?:any ) => {

        const formatedFilters = formatFilterJSON(appliedFilters);
        if (isExcelExport) {

            const gridApi = currentGridRef?.current?.api;

            if(!gridApi){
                notifyError("The grid is not ready");
                return;
            }

            const isPivotMode = gridApi.isPivotMode();
            const isRowGroupingActive = gridApi.getRowGroupColumns().length > 0;
            const isValueActive =  gridApi.getValueColumns().length > 0;

            if (isPivotMode || isRowGroupingActive || isValueActive) {
                                
                 const exportName = `${FilterPageName.Proc_Material_Requirement}_${moment().format("DD-MM-YYYY")}`;
                 gridApi.exportDataAsExcel({
                 fileName: exportName,
                 sheetName: exportName
                 });
            }
            else{
                const headersdata = currentGridRef?.current?.api.getColumnState();
                const body = getBodyForExcelExport({ headersdata: headersdata, filterData: formatedFilters, colDefMap })
                
                const response = await getMaterialRequirementDataDayWise({ releaseDate: releaseDate, body, isExcelExport: 1, report_name: FilterPageName.Proc_Material_Requirement })
                if (response.status === 200) {
                    DownloadExcel(response, FilterPageName.Proc_Material_Requirement)
                    notifySuccess("Excel exported successfully")
                } else {
                    notifyError("Failed to export excel")
                }
            }
        } else {

            const datWiseData = await getMaterialRequirementDataDayWise({ releaseDate: releaseDate, currPage: currPage ? currPage : currentPage, appliedFilters: formatedFilters,page_size: pageSize || userPageSize });
            const dayWiseOutput = datWiseData.data?.data?.results ?? [];
            setDayWiseRecordCount(datWiseData.data?.data?.count ?? 0)
            setDayWiseData(dayWiseOutput)
        }
    }

    const getCumulativeDateWise = async (currPage = 1, releaseDate: string = date, isExcelExport = false,pageSize?:any) => {        
        const formatedFilters = formatFilterJSON(appliedFilters);
        if (isExcelExport) {
            const headersdata = currentGridRef?.current?.api.getColumnState();
            const body = getBodyForExcelExport({ headersdata: headersdata, filterData: formatedFilters, colDefMap })
            const response = await getMaterialRequirementDataExcelExport({ releaseDate: releaseDate, body, isExcelExport: 1, report_name: FilterPageName.Proc_Material_Requirement })
            if (response.status === 200) {
                DownloadExcel(response, FilterPageName.Proc_Material_Requirement)
                notifySuccess("Excel exported successfully")
            } else {
                notifyError("Failed to export excel")
            }
        }
        else {

            const cumulativeData = await getMaterialRequirementData({ releaseDate: releaseDate, currPage: currPage ? currPage : currentCumPage, appliedFilters: formatedFilters ,page_size: pageSize || userPageSize});            
            const cumulativeOutput = cumulativeData.data?.data?.results ?? [];
            setcumulativeRecordCount(cumulativeData.data?.data?.count ?? 0);
            SetCumulativeData(cumulativeOutput)
        }
    }

    const savePageSize = (pageSize: any) => {
        if (pageSize) {
            setCurrentPage(1)
            setUserPageSize(pageSize);
            handleSaveClick(undefined, pageSize);
            getInitialData(1,date,false, pageSize);
        } else {
            notifyError("Invalide page size");
        }
        
    }

    const autoGroupColumnDef = useMemo(() => {
        return {
            minWidth: 250,
        };
    }, []);

    const toggleCurrentTab = (tab: VFFloatingTabItemProps) => setCurrentTab(tab);

    const defaultExcelExportParams = useMemo<ExcelExportParams>(() => {
        return {
            getCustomContentBelowRow: (params) => getRows(params) as ExcelRow[],
            columnWidth: 120,
            fileName: "ag-grid.xlsx",
        };
    }, []);

    // const excelDownload = useCallback(() => {
    //     gridRef.current!.api.exportDataAsExcel();
    // }, []);

    const excelStyles = useMemo<ExcelStyle[]>(() => {
        return [
            {
                id: "header",
                interior: {
                    color: "#aaaaaa",
                    pattern: "Solid",
                },
            },
            {
                id: "body",
                interior: {
                    color: "#dddddd",
                    pattern: "Solid",
                },
            },
        ];
    }, []);
    const customCellRenderers = useMemo(() => (
        {
            "availabilityToolTip": AvailabilityToolTip,
            "coloPriority": ColorPriority,
        }), []);
    const sideBar = useMemo(() => {
        return {
            toolPanels: ['columns'],
        };
    }, []);

    const handlePageChangeDayWise = async (currPage: number) => {
        setCurrentPage(currPage)
        await getInitialData(currPage)
    }

    const handlePageChangeCumulative = async (currPage: number) => {
        setcurrentCumPage(currPage)
        await getInitialData(currPage)
    }

    const renderView = () => {
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
                components: customCellRenderers,
                rowSelection: 'multiple',
                suppressRowClickSelection: true,
                enableBrowserTooltips: true,
                enableRangeSelection: true,
                pagination: true,
                defaultColDef: {
                    floatingFilter: true,
                    suppressMenu: true,
                    filter: "agMultiColumnFilter",
                    cellDataType: false,
                    resizable: true,
                    // minWidth: 140,
                    wrapHeaderText: true,
                    autoHeaderHeight: true,
                    cellStyle: {
                        'text-align': 'center',
                        "font-style": "normal",
                        "font-variant": "normal",
                        "font-weight": "300",
                        "font-size": "20px",
                        "font-family": "Roboto",
                        'text-overflow': 'ellipsis',
                        'white-space': 'nowrap',
                        'resizable': 'true',
                    },
                    initialFlex: 1,
                    flex: 1
                },

            },
            masterDetail: true,
            detailCellRenderer: ChildrenProcPlanningCellRenderer,
            autoGroupColumnDef: autoGroupColumnDef,
            paginationAutoPageSize: true,
            enterNavigatesVertically: true,
            enterNavigatesVerticallyAfterEdit: true,
            groupDefaultExpanded: 0,
            defaultExcelExportParams: defaultExcelExportParams,
            excelStyles: excelStyles,
            sideBar: sideBar,

            onCellEditingStopped(event: any) {
                const field = event.colDef.field;
                const newValue = event.newValue;
                const rowIndex = event.rowIndex;

                if (!field || rowIndex == null) {
                    return;
                }

                SetCumulativeData((prevData: any) => {
                    const newData = [...prevData];
                    const updatedRow = {
                        ...newData[rowIndex],
                        [field]: newValue,
                        tsfs: newData[rowIndex].soh + newValue
                    };
                    newData[rowIndex] = updatedRow;
                    return newData;
                });
                gridRef.current?.api.refreshCells({ force: true });
            }

        };

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
        }, [currentGridRef, columnState, colDef]);

        switch (currentTab.id) {
            case "sdv":
                return (
                    <>
                        {/* {(isMatReqDayWiseLoading || isMatReqLoading) && <VFLoader/>} */}
                        <TableWrapper>
                            <VFTable
                                paginationPageSize={10}
                                {...agGridProps}
                                columnDefs={colDef}

                                rowData={DayWiseData}
                                tooltipHideDelay={100000}
                                tooltipShowDelay={0}
                                tooltipMouseTrack={true}
                                ref={gridRef}
                                onGridReady={(params: any) => {
                                    params.api.autoSizeAllColumns();
                
                                    setCurrentGridRef(gridRef);
                                }}
                                pagination={false}
                                maintainColumnOrder
                               onFilterChanged={()=>{Object.keys((gridRef?.current?.api?.getFilterModel()))?.length>0 ? setIsDisabled(false) : setIsDisabled(true)}}


                            />
                            <VFPagination
                                selectedRows={0}
                                rowsPerPage={userPageSize || pagination.mtoPageSize}
                                isDisabled={isDisabled}
                                resetGridRef={gridRef}
                                totalRows={dayWiseRecordCount}
                                currentPage={currentPage}
                                handleChangePage={handlePageChangeDayWise}
                                customPageSizeEnabled={true}
                                savePageSize={savePageSize}
                                userPageSize = {userPageSize}
                            />
                        </TableWrapper>
                    </>
                );
            case "cv":
                return (
                    <>
                        {/* {(isMatReqDayWiseLoading || isMatReqLoading) && <VFLoader/>} */}
                        <TableWrapper>      
                            <VFTable
                                paginationPageSize={10}
                                {...agGridProps}
                                columnDefs={colDef}
                                rowData={CumulativeData}
                                tooltipHideDelay={100000}
                                tooltipShowDelay={0}
                                tooltipMouseTrack={true}
                                height={'550px'}
                                ref={gridRef}
                                onGridReady={(params: any) => {
                                    params.api.autoSizeAllColumns();
                
                                    setCurrentGridRef(gridRef);
                                }}

                                maintainColumnOrder
                               onFilterChanged={()=>{Object.keys((gridRef?.current?.api?.getFilterModel()))?.length>0 ? setIsDisabled(false) : setIsDisabled(true)}}

                            />
                            <VFPagination
                                selectedRows={0}
                                rowsPerPage={userPageSize || pagination.mtoPageSize}
                                isDisabled={isDisabled}
                                resetGridRef={gridRef}
                                totalRows={cumulativeRecordCount}
                                currentPage={currentCumPage}
                                handleChangePage={handlePageChangeCumulative}
                                customPageSizeEnabled={true}
                                savePageSize={savePageSize}
                                userPageSize = {userPageSize}
                            />
                        </TableWrapper>

                    </>
                );
            default:
                return <VFTable columnDefs={[]} rowData={[]} {...agGridProps} />
        }
    }


    return {
        // isSideBarOpen,
        // agGridProps,
        // currentPage,
        toggleCurrentTab,
        renderView,
        onDateChangeReq,
        onDateSubmitReq,
        date,
        currentTab,
        isMatReqLoading,
        isMatReqDayWiseLoading,
        isUpdateUserConfig,
        isGetUserConfig,
        handleResetClick,
        handleSaveClick,
        onExcelExportClickReq
        //excelDownload,
        //GetCount
    }
}

export default useMaterialReq;