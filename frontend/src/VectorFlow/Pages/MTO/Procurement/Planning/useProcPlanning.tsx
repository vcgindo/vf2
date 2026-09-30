import { useState, useMemo, useRef, useCallback, useEffect } from "react"
import { AgGridReactProps, } from "ag-grid-react"
import { useUserData } from "../../../../../context"
import ColoPriority from "../../Common/ColorPriority/index";
import AvailabilityToolTip from "../../../MTA/InsightsAndTrends/BTR/AvailabilityToolTip";
import { VFFloatingTabItemProps } from "../../../../../components/VectorFLOW/commons/VFFloatingTab"
import VFTable from "../../Common/VFTable";
import VFButton from '../../../../../components/VectorFLOW/commons/VFButton';
import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline";
import { useNavigate } from "react-router-dom";
import { ProcessRowGroupForExportParams, ExcelCell, ExcelRow, ExcelExportParams, ExcelStyle } from 'ag-grid-community';
import { DownloadExcel, formatFilterJSON, getBodyForExcelExport, getColumnDefinations } from '../../../../../helpers/utils';
import ChildrenProcPlanningCellRenderer from "../ChildrenProcPlanningCellRenderer";
import { putUpdateProcurementSimulationData, useGetProcurementPlanningDataForExcelExport, userGetProcPlanningData } from "../../../../Services/MTO/Procurement/ProcPlanning/index";
import { toast } from "react-toastify";
import { notifyError, notifyLoader, notifySuccess } from "../../../../../helpers/notify";
import { useGetUIConfigData } from "../../../../../VectorFlow/Services/MTO/Common/UIConfig";
import VFPagination from "../../Common/VFPagination";
import OverlayLoader from "../../Common/Loader";
import { INumberCellEditorParams } from "@ag-grid-community/core"
import { TableWrapper } from "./styles";
//import { pagination } from "../../Common/Enum";
import { useDispatch } from "react-redux";
import { APPLIED_FILTERS, PROCPLANNING_ANALYTICS } from "../../../../../redux/actions/MTO";
import { useGetUserUIConfigData, useUpdateUserUIConfigData } from "../../../../../VectorFlow/Services/MTO/Common/UserUIConfig";
import { FilterPageName, pagination, UIGridCode } from "../../Common/Enum";
import useColDef from "../../../../../hooks/useColDef";
import { useGetDBRsettingsData } from "../../../../../VectorFlow/Services/MTO/Common/DBRSettings";
import ChildrenColor from "../../Common/ChildrenColor/ChildrenColor";
import moment from "moment";
import _ from "lodash";


const getRows = (params: ProcessRowGroupForExportParams) => {
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
        ...(params?.node?.data?.children ?? []).map((record: any) => [
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

const useProcPlanning = ( appliedFilters: any) => {
    
    const [HeaderData, setHeaderData] = useState<any>([]);
    const [childHeaderData, setChildHeaderData] = useState<any>([])
    const gridRef = useRef<any>(null);
    const [columnState, setColumnState] = useState<any>([]);
    const [isReset, setIsReset] = useState<boolean|undefined>(undefined);
    const [colDef, setColDef] = useState<any>([{}]);
    const [childColDef, setChildColDef] = useState<any>([{}])
    const { mutateAsync: getUIConfigData, isLoading: isUIConfigDataLoading } = useGetUIConfigData()
    const { mutateAsync: updateUserUIReportConfigData, isLoading: isUpdateUserConfig } = useUpdateUserUIConfigData();
    const { mutateAsync: getUserUIReportConfigData, isLoading: isGetUserConfig } = useGetUserUIConfigData();
    const { colDefMap , getColDef} = useColDef();
    const reportName = "ProcurementPlanningShortage";
    const [defaultColState,setDefaultColState] = useState<any>([])

    const [clearFilter, clearFilterDisabled]= useState<boolean>(true);
    const format2 = "YYYY-MM-DD"
    const d = new Date();
    const datetime = moment(d).format(format2);
    
    const [selectedDate, setSelectedDate] = useState<string>(datetime);

    

    
    const [userConfigFetched, setUserConfigFetched] = useState<any>(false);
    const [userPageSize, setUserPageSize] = useState<any>();
    const [isPivot, setIsPivot] = useState<any>(false);

    const setColumnDef = async () => {
        try {
            const response = await getUIConfigData(reportName);
            getColDef(response)
            const UIConfig = response.data.data;
            if (UIConfig && UIConfig.length > 0) {
                setHeaderData(UIConfig);
                setColDef(getColumnDefinations(UIConfig, customHeader, extras, ["ExpAdd.StockToday"]));
            }
        }
        catch (e) {
            console.log(e);
        }
        try{
            const reponse = await getUIConfigData("ProcPlanningReportChildren");
            setChildHeaderData(reponse.data.data);
        }
        catch(e){
            console.log(e);
        }
    }

    const onPivotModeChanged = (event: any) => {
        const isPivotOn = event.api.isPivotMode();
        setIsPivot(isPivotOn);
      };

    const getUserColumnConfig = async () => {
        try {
            const response = await getUserUIReportConfigData({
                un: user.user.name,
                rn_id: UIGridCode.ProcPlanning
            });
    
            const configData = response?.data?.data?.[0]?.columns_settings;
            if (configData) {
                const newConfig = JSON.parse(configData);
    
                setUserPageSize(Number(newConfig.pageSize) || undefined);
                setColumnState(newConfig.cs || []);
                setIsPivot(!!newConfig.pivot);
            } else {
                console.error('Failed to apply column state');
            }
    
            setUserConfigFetched(true);
        } catch (error) {
            console.error('Error fetching user column config:', error);
        }
    }

    const handleSaveClick = async (isReset = false, page_size?: any) => {
    
        try {
            if (page_size) {
                const config = columnState;
                const isPivot = gridRef?.current?.api.isPivotMode();
                const fullConfig = { pivot: isPivot, cs: config, pageSize: page_size };
                const payload = {
                    un: user.user.name,
                    rn_id: UIGridCode.ProcPlanning,
                    cs: JSON.stringify(fullConfig),
                };
                await updateUserUIReportConfigData([payload]);
        
            } else {
                const fullConfig = {
                    pivot: isReset ? false : gridRef?.current?.api.isPivotMode(),
                    cs: isReset ? defaultColState : gridRef?.current?.api?.getColumnState(),
                    pageSize: userPageSize
                };

                const payload = {
                    un: user.user.name,
                    rn_id: UIGridCode.ProcPlanning,
                    cs: JSON.stringify(fullConfig)
                };
    
                await updateUserUIReportConfigData([payload]);
                if (isReset) {
                    notifySuccess("Reset Layout Successfully");
                } else {
                    notifySuccess("Saved Layout Successfully");
                }
            }
        } catch (error) {
            console.error(error);
            notifyError("Error while saving");
        }
    };
    

    const handleResetClick = () => {
        setIsReset(true);
    }

    useEffect(() => {

        if (isReset) {
            handleSaveClick(undefined,true);
            setIsReset(false);
            setColumnState([...defaultColState]);
            setIsPivot(false);
        } 
    }, [isReset]);

    useEffect(() => {
        setColumnDef();
    }, [])

    const { isSideBarOpen } = useUserData()
    const navigate = useNavigate();
    const [datas, setData] = useState<any>([]);
    const [ShortageDatas, SetShortageData] = useState<any[]>([]);
    const [CompleteAvailableDatas, setCompleteAvailableData] = useState<any[]>([]);
    const [currentPage, setCurrentPage] = useState<number>(1);
    const [totalRows, setTotalRows] = useState(0);
    const [isOverlayLoading, setIsOverlayLoading] = useState(false);
    const { user } = useUserData();


    const dispatch = useDispatch()

    dispatch(PROCPLANNING_ANALYTICS({ date:selectedDate }));
    dispatch(APPLIED_FILTERS( {...formatFilterJSON(appliedFilters)} ));

    const [currentTab, setCurrentTab] = useState<VFFloatingTabItemProps | undefined>({
        id: 'ca',
        label: 'Completely Available',
        value: 'ca'
    });
    const { mutateAsync: getProcPlanningData, isLoading: isGetProcPlanningData } = userGetProcPlanningData()
    const { mutateAsync: UpdateProcurementSimulationData } = putUpdateProcurementSimulationData()
    const { mutateAsync : GetProcPlanningDataForExcelData, isLoading: isProcurementPlanningDataForExcelExport} = useGetProcurementPlanningDataForExcelExport()
    const { mutateAsync: getDBRsettingsData, isLoading: isGetDBRsettingsData } = useGetDBRsettingsData();
    const [simulationEnable, setSimulationEnable] = useState<any>();
    const [showExcelModal, setShowExcelModal] = useState(false);
    const tempGridRef = useRef<any>(null);
    const [tempGridData, setTempGridData] = useState<any>(undefined);
    const [gridData, setGridData] = useState<any>();
    
    
    
     const getTempGridData = async () => {
        
        try {
          const formatedFilters = formatFilterJSON(appliedFilters);
            const response = await getProcPlanningData({
            ca: '1',
            date: selectedDate,
            pageNum: '1',
            appliedFilters: formatedFilters,
            page_size: totalRows,
          });
          setTempGridData(response?.data?.data?.results || []);
        } catch (e) {
          console.log(e);
        }
    };
    
     useEffect(() => {
        if (tempGridData) {
          const colState = gridRef?.current?.api?.getColumnState();
          tempGridRef.current?.api?.applyColumnState({
            state: colState,
            applyOrder: true,
          });
    
          const isPivotMode = gridRef?.current?.api?.isPivotMode();
          if (isPivotMode) {
            gridRef?.current?.api?.exportDataAsExcel({
              fileName: "Proc_Planning",
            });
          } else {
            tempGridRef.current?.api?.exportDataAsExcel({
              fileName: "Proc_Planning",
            });
          }
        }
      }, [tempGridData]);
    
    
    const fetchData = useCallback(async (date: string, pageNumber = 1, currentTab = '1', isExcelExport = false, pageSize?:any, isChildren?:any,excel_scope?:string) => {
        if(isExcelExport){
            try {
                const headersdata = gridRef?.current?.api.getColumnState();
                const formattedFilters = formatFilterJSON(appliedFilters)
                const body = getBodyForExcelExport({ headersdata, filterData: formattedFilters, colDefMap })
                const reportName = `${FilterPageName.Proc_Procurement_Planning + "_" + (excel_scope == "all" ? excel_scope : currentTab == "1" ? "Completely_Available" : "Shortage")}`;
                const response = await GetProcPlanningDataForExcelData({ body, ca: currentTab, isExcelExport: 1, date, report_name: reportName, isChildren, excel_scope: excel_scope });
                if (response.status === 200) {
                    DownloadExcel(response, reportName);
                    notifySuccess('Excel Export Successfully')
                }else{
                    notifyError('Failed to export Excel')
                }
            } catch (error) {
                notifyError("Failed to export")
            }
        }else{

        try {
            const formatedFilters = formatFilterJSON(appliedFilters);
            const response = await getProcPlanningData({ date, pageNum: pageNumber.toString(), ca: currentTab, appliedFilters: formatedFilters, page_size: pageSize || userPageSize });
            if (response.status === 200) {
                setCurrentPage(pageNumber)
                notifySuccess("Data fetched Successfully!");
            }
            if (!gridData?.data?.data || gridData?.data?.data?.length === 0) {
                setGridData([]);
                // return;
              }
              
            else {
                notifyError("Failed to fetch data!");
            }
            setTotalRows(response?.data?.data?.count)
            setData(response?.data?.data?.results || []);


        } catch (error) {
            notifyError("Failed to fetch data!");
        }
    }
    }, [getProcPlanningData,appliedFilters,userPageSize]);

    useEffect(() => {
        if (datas && HeaderData.length) {
            const initializeData = (data: any, headerData: any) => {
                const calculateData = data.map((item: any) => ({
                    ...item,
                    gap: item.req - item.soh - item.siqc - item.sit,
                    tsfs: item.soh,
                    children: item.children || []
                }));
                const ShortageData = calculateData.filter((item: any) => item.gap > 0);
                const CompleteAvailableData = calculateData.filter((item: any) => item.gap === 0);

                const CompleteHeaderData = headerData.map((header: any) => {
                    if (header.jf === 'eas') {
                        return { ...header, vs: false };
                    }
                    return header;
                });

                const ShortageHeaderData = headerData.map((header: any) => {
                    if (header.jf === 'eas') {
                        return { ...header, vs: true };
                    }
                    return header;
                });
                SetShortageData(ShortageData);
                setCompleteAvailableData(CompleteAvailableData);

                return { ShortageData, CompleteAvailableData, CompleteHeaderData, ShortageHeaderData };

            };
            initializeData(datas, HeaderData);

        }
    }, [datas, HeaderData]);

    const customHeader = {
        ColorPriority: {
            cellRenderer: 'coloPriority',
            floatingFilter: false,
            suppressHeaderFilterButton: true,
            valueGetter: (params: any) => {
                let cpData: any;
                if (!_.isEmpty(params.data)) {
                    cpData = params.data?.cp[0];
                }

                if (!cpData) return '';
            
                // Sort keys to ensure consistent ordering
                const sortedKeys: any = Object.keys(cpData).sort();
                const sortedObj: any = {};
                sortedKeys.forEach((key: any) => {
                    sortedObj[key] = cpData[key];
                });
            
                return JSON.stringify(sortedObj);
            },
            tooltipValueGetter: (params: any) => {
                let tooltipText = '';
                let cpData: any;
                if (!_.isEmpty(params.data)) {
                    cpData = params.data?.cp[0];
                }
                
                if (!cpData) return tooltipText;

                const keysToPrint = ["B", "R", "Y", "G", "W", "Bl"];
                keysToPrint.forEach((key) => {
                    if (Object.prototype.hasOwnProperty.call(cpData, key)) {
                        if (tooltipText !== '') {
                            tooltipText += ' | ';
                        }
                        tooltipText += `${key}: ${cpData[key]}`;
                    }
                });
                return tooltipText;
            },
            // tooltipComponent: "availabilityToolTip",
            initialWidth: 200, //160
            // autoHeaderHeight: true,
            // wrapHeaderText: true,

        },

        'ExpAdd.StockToday': {
            // cellRenderer: "inputbox",
            editable: true,
            cellEditor: 'agNumberCellEditor',
            cellEditorParams: {
                min: 0
            } as INumberCellEditorParams,
            // autoHeaderHeight: true,
            // wrapHeaderText: true,
            initialWidth: 200, //160
            filter: 'agMultiColumnFilter',
            floatingFilter: true,
            cellStyle: {
                backgroundColor: 'white',
                border: '1px solid #b9bdba',
                color: 'black',
                padding: '1px',
            },
        }

    }
    const extras = [
        {
            field: "",
            position: 0,
            suppressHeaderFilterButton: true,
            suppressMenu: true,
            filter: false,
            maxWidth: 35,
            minWidth: 35,
            cellRenderer: 'agGroupCellRenderer',
            pinned:"left"
        }
    ]

 
    useEffect(() => {
        const feature_permission = user?.feature_permission || [];
        setSimulationEnable(feature_permission.includes("Simulation_Enable"));
      }, [user]);

    const childCustomHeaders = {
        clr:{
            cellRenderer : ChildrenColor
          }
    }

    useEffect(()=>{
        if(childHeaderData && childHeaderData.length>0){
            setChildColDef(getColumnDefinations(childHeaderData,childCustomHeaders))
        }
    },[childHeaderData])

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
        if (currentTab && userConfigFetched) {
          if (currentTab.label === 'Shortage') {
            if (simulationEnable) {
              setColDef(getColumnDefinations(HeaderData, customHeader, extras));
            } else {
              setColDef(getColumnDefinations(HeaderData, customHeader, extras, ["ExpAdd.StockToday"]));
            }
            setCurrentPage(1);
            fetchData(selectedDate, 1, '0', false, userPageSize);
          } else {
            setColDef(getColumnDefinations(HeaderData, customHeader, extras, ["ExpAdd.StockToday"]));
            setCurrentPage(1);
            fetchData(selectedDate, 1, '1', false, userPageSize);
          }
        }
      }, [currentTab]);


    const toggleCurrentTab = useCallback((tab: VFFloatingTabItemProps) => setCurrentTab(tab), []);

    const [isDisabled, setIsDisabled] = useState(true);
    useEffect(() => {
        let isDis = true;
        ShortageDatas.forEach((e) => {
            if (e.eas && e.eas !== 0) {
                isDis = false;
                setIsDisabled(false);
            }
        })
        if (isDis) {
            setIsDisabled(true);
        }
    }, [ShortageDatas])
    const navigateToSimulateScreen = useCallback(async () => {


        const inputJson: any = {
            "username": user?.user.name,
            "stock": [

            ]
        }
        ShortageDatas.forEach((e, index) => {

            const val = gridRef.current?.api.getRowNode(index.toString())?.data;
            if (val.eas !== 0) {
                inputJson.stock.push(
                    {
                        'ic': val.rm,
                        'as': val.eas
                    }
                )
            }

        })
        setIsOverlayLoading(true);
        UpdateProcurementSimulationData(inputJson)
            .then(response => {
                // Handle the response and perform subsequent actions
                setIsOverlayLoading(false);
                if (response.status === 200) {
                    notifySuccess("Simulation updated successfully!")
                    navigate("/mto/planning/simulative-fullkit", { state: { ShortageDatas, date: selectedDate } });

                }
                else {
                    notifyError("Failed to update Simulation!")

                }


            })
            .catch(error => {
                // Handle any errors that occur during the API call
                console.error("API call failed:", error);

                //         // Add your error handling code here
            });


    }, [navigate, ShortageDatas, selectedDate]);

   
    const excelDownload = useCallback(() => {
        gridRef.current?.api.exportDataAsExcel();
    }, []);
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
            "coloPriority": ColoPriority,
        }), []);
    const sideBar = useMemo(() => {
        return {
            toolPanels: ['columns'],
        };
    }, []);

    useEffect(() => {
        if (selectedDate && Object.keys(appliedFilters).length > 0 && userConfigFetched) {
            setCurrentPage(1);
            fetchData(selectedDate, 1, currentTab?.label === "Shortage" ? '0' : '1');
        }
    }, [appliedFilters, userConfigFetched])

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
        if (currentTab?.id === 'ca') {
            fetchData(selectedDate, pageNumber, '1', false, userPageSize);
        }
        else {
            fetchData(selectedDate, pageNumber, '0', false, userPageSize);
        }
        // (refGraph1.current?.api.getRowNode) && refGraph1.current?.api.set
    };

    const savePageSize = (pageSize: any) => {
        if (pageSize) {
            setCurrentPage(1)
            setUserPageSize(pageSize);
            handleSaveClick(undefined, pageSize);
            fetchData(selectedDate,1,currentTab?.label === "Shortage" ? '0':'1', false,pageSize);
        } else {
            notifyError("Invalide page size");
        }
        
    }

    useEffect(() => {
        if (gridRef?.current && columnState?.length) {
            const result = gridRef?.current?.api?.applyColumnState({
                state: columnState,
                applyOrder: true
            });
            const applyPivot = gridRef?.current?.api.setGridOption(
                "pivotMode",
                isPivot
            );
            if (!result || !applyPivot) {
                console.error('Failed to apply column state');
            }
        }
    },[gridRef, columnState]);

    useEffect(() => {
        if (gridRef?.current?.api && colDef) {
            setDefaultColState(gridRef?.current?.api?.getColumnState());
            getUserColumnConfig();
        }
    }, [colDef])

    const renderView = () => {
        switch (currentTab?.id) {
            case "ca":
                return (
                    <TableWrapper>
                        <VFTable
                            {...agGridProps}
                            
                            columnDefs={colDef}
                            rowData={CompleteAvailableDatas}
                            tooltipHideDelay={100000}
                            tooltipShowDelay={0}
                            tooltipMouseTrack={true}
                            ref={gridRef}
                            onGridReady={(params: any) => {
                                params.api.autoSizeAllColumns();
                                // setDefaultColState(params?.api?.getColumnState())
                            }}
                            maintainColumnOrder={true}        
                    onFilterChanged={()=>{Object.keys((gridRef?.current?.api?.getFilterModel()))?.length>0 ? clearFilterDisabled(false) : clearFilterDisabled(true)}}

                        />
                        <VFPagination
                            key={1}
                            resetGridRef={gridRef}
                            isDisabled={clearFilter}
                            selectedRows={0}
                            rowsPerPage={userPageSize || pagination.mtoPageSize}
                            totalRows={totalRows}
                            currentPage={currentPage}
                            handleChangePage={handlePageChangeCumulative}
                            customPageSizeEnabled={true}
                            savePageSize={savePageSize}
                            userPageSize = {userPageSize}

                        />
                    </TableWrapper>
                );
            case "short":
                return (

                    <TableWrapper>
                        {isOverlayLoading && <OverlayLoader message={"Updating the simulated data..."} />}
                        <VFTable
                            key={2}
                            {...agGridProps}
                            columnDefs={colDef}
                            rowData={ShortageDatas}
                            tooltipHideDelay={100000}
                            tooltipShowDelay={0}
                            tooltipMouseTrack={true}
                            ref={gridRef}
                            onGridReady={(params: any) => {
                                params.api.autoSizeAllColumns();
                            }}
                            maintainColumnOrder={true}
                        onFilterChanged={()=>{Object.keys((gridRef?.current?.api?.getFilterModel()))?.length>0 ? clearFilterDisabled(false) : clearFilterDisabled(true)}}

                        />
                        <VFPagination
                            selectedRows={0}
                            resetGridRef={gridRef}
                            isDisabled={clearFilter}
                            rowsPerPage={userPageSize || pagination.mtoPageSize}
                            totalRows={totalRows}
                            currentPage={currentPage}
                            handleChangePage={handlePageChangeCumulative}
                            customPageSizeEnabled={true}
                            savePageSize={savePageSize}
                            userPageSize={userPageSize}


                        />
                   { simulationEnable && (
                    <div style={{ width: "100%",display: 'flex', alignItems: 'center', justifyContent: 'right', textAlign: 'right', marginRight: '14px', flexDirection: 'row', marginTop: '15px' }}>

                            <VFButtonOutline
                                    onClick={() => { (!isDisabled) && fetchData(selectedDate, 1, '0',false,userPageSize) }}
                                themeUi=""
                                disabled={isDisabled}
                                width={135}
                                
                                style={{
                                    opacity: isDisabled ? '0.4' : '1',
                                    height: 'max-content',
                                    marginRight: 20,
                                    borderColor: '#BC3D81',
                                    color: '#BC3D81',
                                    background: 'transparent',
                                    alignItems: 'center',
                                    fontWeight: 'bold',
                                    padding: "1rem",
                                    paddingRight: "2rem",
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', }}>
                                    <img src="/assets/img/VectorFLOW/reset.svg" alt="Reset Icon" height={15} width={15} style={{ margin: '0 12px' }} />
                                    <p style={{ fontSize: '12px' }}>
                                        Reset Data
                                    </p>
                                </div>
                            </VFButtonOutline>
                            <VFButton
                                onClick={navigateToSimulateScreen}
                                themeUi=""
                                disabled={isDisabled}
                                width={250}
                                style={{
                                    padding: "1rem",
                                    height: "max-content",
                                    width: "max-content",
                                    fontSize: "12px",
                                }}
                                >
                                Simulate improvement in Full Kits
                            </VFButton>
                        </div>

        )
                            
                            }

                    </TableWrapper>
                );
            
            default:
                return(
                    <TableWrapper>
                        <VFTable
                            {...agGridProps}
                            
                            columnDefs={colDef}
                            rowData={CompleteAvailableDatas}
                            tooltipHideDelay={100000}
                            tooltipShowDelay={0}
                            tooltipMouseTrack={true}
                            ref={gridRef}
                            onGridReady={(params: any) => {
                                params.api.autoSizeAllColumns();
                                // setDefaultColState(params?.api?.getColumnState())
                                
                            }}
                            maintainColumnOrder={true}
                    onFilterChanged={()=>{Object.keys((gridRef?.current?.api?.getFilterModel()))?.length>0 ? clearFilterDisabled(false) : clearFilterDisabled(true)}}

                        />
                        <VFPagination
                            key={1}
                            resetGridRef={gridRef}
                            isDisabled={clearFilter}
                            selectedRows={0}
                            rowsPerPage={userPageSize || pagination.mtoPageSize}
                            totalRows={totalRows}
                            currentPage={currentPage}
                            handleChangePage={handlePageChangeCumulative}
                            customPageSizeEnabled={true}
                            savePageSize={savePageSize}
                            userPageSize = {userPageSize}
                        />
                    </TableWrapper>
                );
        }
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
            components: customCellRenderers,
            rowSelection: 'multiple',
            suppressRowClickSelection: true,
            enableBrowserTooltips: true,
            enableRangeSelection: true,
            icons: icons,
            defaultColDef: {
                enableRowGroup: true,
                resizable: true,
                floatingFilter: true,
                filter: "agMultiColumnFilter",
                // minWidth: 140,
                // wrapHeaderText: true,
                // autoHeaderHeight: true,
                cellStyle: {
                    'text-align': 'center',
                    'height': '50px',
                    "fontStyle": "normal",
                    "fontVariant": "normal",
                    "fontWeight": "300",
                    "fontSize": "20px",
                    "fontFamily": "Roboto",
                    'textOverflow': 'ellipsis',
                    'whiteSpace': 'nowrap',
                    'resizable': 'true',
                },
                flex: 1,
                initialFlex: 1,
            },


        },
        masterDetail: true,
        detailCellRenderer: ChildrenProcPlanningCellRenderer,
        onColumnPivotModeChanged: onPivotModeChanged,
        detailCellRendererParams: {
            colDef: childColDef
        },
          isRowMaster: (data: any) => {
                return data.children && Array.isArray(data.children) && data.children.length > 0;
            },
        detailRowHeight: 225,
        autoGroupColumnDef: autoGroupColumnDef,
        enterNavigatesVertically: true,
        enterNavigatesVerticallyAfterEdit: true,
        groupDefaultExpanded: 0,
        excelStyles: excelStyles,
        sideBar: sideBar,
        onCellEditingStopped(event: any) {
            const field = event.colDef.field;
            const newValue = +event.newValue;

            if (!field || !event.node || event.node.group) {
                console.warn("Invalid editing event or it's a group node, skipping update.");
                return;
            }
    
            const nodeId = event.node.data.rm;  // Assuming 'rm' is a unique identifier in your data
            SetShortageData((prevData: any) => {
                const newData = prevData.map((row: any) => {
                    if (row.id !== nodeId) return row;
                    return {
                        ...row,
                        [field]: newValue,
                        tsfs: row.soh + newValue
                    };
                });
                return newData;
            });
            gridRef.current?.api.refreshCells({ force: true });
        }
    };

    const GetCount = {
        "short": ShortageDatas.length,
        "complete": CompleteAvailableDatas.length,
        "total": ShortageDatas.length + CompleteAvailableDatas.length
    };

    return {
        isSideBarOpen,
        agGridProps,
        currentPage,
        toggleCurrentTab,
        renderView,
        excelDownload,
        GetCount,
        fetchData,
        selectedDate,
        setSelectedDate,
        isLoading : isProcurementPlanningDataForExcelExport || isUpdateUserConfig || isGetUserConfig || isUIConfigDataLoading || isGetProcPlanningData || isGetDBRsettingsData,
        handleResetClick,
        handleSaveClick,
        currentTab,
        setShowExcelModal,
        showExcelModal,
        isPivot,
        getTempGridData,
        gridRef
    }
}

export default useProcPlanning;