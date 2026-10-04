import { loadDailyData } from '../../../../../components/VectorFLOW/commons/DailyDataGraphModal/loadDailyData';
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { type DailyDataGraph } from "../../../../types/MTA";


import { VFFloatingTabItemProps } from "../../../../../components/VectorFLOW/commons/VFFloatingTab"
import HorizontalSplitView from "./HorizontalSplitView"

import VerticalSplitView from "./VerticalSplitView"
import { getColumnsForExcelExport, mapBTRRowDataToColDefs, MainMenuItemsCustomization, getColumnDefinationsMTA, DownloadExcel, DownloadExcelMTA , CsvExportMTA} from "../../../../../helpers/utils"

import { useGetBTRDataCount, useGetBTRData } from "../../../../../VectorFlow/Services/MTA/InsightsAndTrends/BTR"


import { ColDef } from "ag-grid-enterprise"
import { BTRTableHeader } from "./styles"
import CategoryCellRenderer from "./CategoryCellRenderer"
import AvailabilityCellRenderer from "./AvailabilityCellRenderer"
import ColorCellRenderer from "./ColorCellRenderer"
import { AgGridReactProps } from "ag-grid-react"
import TagsCellRenderer from "./TagsCellRenderer"
import AvailabilityToolTip from "./AvailabilityToolTip"
import CategoryToolTip from "./CategoryToolTip"
import { SeasonalityGraphCellRenderer } from "../../../../../components/VectorFLOW/commons/SeasonalityCellRenderers"
import { VFPaginationProps } from "../../../../../components/VectorFLOW/commons/VFPagination"
import VFPagination from "../../../../../VectorFlow/Pages/MTO/Common/VFPagination"
import CustomVFTable from "./CustomVFTable"
import { notifyError, notifyLoader, notifySuccess } from "../../../../../helpers/notify"
import { toast } from "react-toastify"
import {TOGGLE_GRAPH_MODAL,UPDATE_DAILY_DATA} from '../../../../../redux/actions/MTA';
import useBPRFilter from "../../../../../hooks/useBPRFilter";
import { useUserData } from "../../../../../context"
import { BPRFilterState } from "../../../../../VectorFlow/types/BPR"
import { BTRCategoryTextToNumberMapper } from "../../../../../helpers/BPRConstants"
import useGetLastRunData from "../../../../../hooks/useGetLastRunData"

import _ from 'lodash'
import { useGetDailyData } from "../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR"
import { useSelector,useDispatch } from "react-redux";
import BPRGraphCellRenderer from "../../SupplyChainIntelligenceHub/BPR/BPRGraphCellRenderer";
import type { RootState } from '../../../../../redux/store/store';

import { useGetUIConfigData } from "../../../../Services/MTA/Common/UIConfig"
import { UIColumnConfigName, UserUIColumnConfigName } from "../../../../../helpers/Enum"
import { format } from "date-fns"
import { useGetState } from "../../../../Services/MTA/Common/UserUIConfig"
import { GridRef } from "../../../../../VectorFlow/types/MDM"
import BTRColorCellRenderer from "./BTRColorCellRenderer";
import { displayRows } from "./displayRows";

const useBTR = () => {

     const showDailyDataGraphModal = useSelector((state:RootState) => state.mta.showDailyDataGraphModal);
        const showNormChangeHistoryTable = useSelector((state:RootState) => state.mta.showNormChangeHistoryTable);
        const dailyData = useSelector((state:RootState) => state.mta.dailyData);

    const {mutateAsync:getDailyData} = useGetDailyData();

    const ecoRef = useRef<GridRef>();
    const techRef = useRef<GridRef>();
    const tempRef = useRef()
    const [techInternalRef,setTechInternalRef] = useState<any>()
    const [ecoInternalRef,setEcoInternalRef] = useState<any>()
    const tabs: Array<VFFloatingTabItemProps> = [
        {
            id: "1",
              value: 'on-hand',
            label: "On-Hand Inv. View"
          
        },
        {
            id: "2",
             value: 'pipeline',
            label: "Pipeline Inv. View"
           
        },
        {
            id: "3",
             value: 'both',
            label: "Both On-Hand & Pipeline View"
        }
    ]

    const { user } = useUserData()
     const dispatch = useDispatch();


    const themeUi = user.user.theme_ui

    const [currentPageTech, setCurrentPageTech] = useState<number>(1);
    const [currentPageEco, setCurrentPageEco] = useState<number>(1);
    const [currentPageTechForBoth, setCurrentPageTechForBoth] = useState<number>(1);
    const [currentPageEcoForBoth, setCurrentPageEcoForBoth] = useState<number>(1);

    const [isLockMode, toggleLockMode] = useState<boolean>(false)

    const [horizon, setHorizon] = useState<number>(90)

    const { state: currFilter, setState: setCurrFilter, onDelete } = useBPRFilter()

    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const BTR_ROWS_PER_PAGE = EnvConfig['BTR_ROWS_PER_PAGE'];  
    const rowsPerPage = parseInt(BTR_ROWS_PER_PAGE || '50');

    const [userPageSizeTech , setUserPageSizeTech]  = useState<number>(BTR_ROWS_PER_PAGE?parseInt(BTR_ROWS_PER_PAGE):50) 
    const [userPageSizeEco , setUserPageSizeEco]  = useState<number>(BTR_ROWS_PER_PAGE?parseInt(BTR_ROWS_PER_PAGE):50) 
    const [userPageSizeTechForBoth , setuserPageSizeTechForBoth]  = useState<number>(BTR_ROWS_PER_PAGE?parseInt(BTR_ROWS_PER_PAGE):50) 
    const [userPageSizeEcoForBoth , setUserPageSizeEcoBoth]  = useState<number>(BTR_ROWS_PER_PAGE?parseInt(BTR_ROWS_PER_PAGE):50) 

    const { mutateAsync: getBTRData } = useGetBTRData()

    const { mutateAsync: fetchBTRDataCount } = useGetBTRDataCount()

    const { mutateAsync: getUiConfig, isLoading: isUIConfigLoading, isError } = useGetUIConfigData();

    const { mutateAsync: getState, isLoading: isSavedDataLoading } = useGetState();

    const [countData, setCountData] = useState<any>();
    const ecoTotalRows = countData?.EcoCount;
    const techTotalRows = countData?.TechCount;
    const requestVersion = useRef({ tech: 0, eco: 0, count: 0, layout: 0, config: 0 });
    const [pending, setPending] = useState({ tech: false, eco: false, count: false });
    const mounted = useRef(true);
    useEffect(() => {
        mounted.current = true;
        return () => { mounted.current = false; };
    }, []);
    const getBTRDataCount = async (payload: any) => {
        const version = ++requestVersion.current.count;
        setPending(value => ({ ...value, count: true }));
        try {
            const response = await fetchBTRDataCount(payload);
            if (mounted.current && version === requestVersion.current.count) setCountData(response.data.data);
        } catch (error) {
            if (mounted.current && version === requestVersion.current.count) {
                setCountData(undefined);
                notifyError(error instanceof Error ? error.message : String(error));
            }
        } finally {
            if (mounted.current && version === requestVersion.current.count)
                setPending(value => ({ ...value, count: false }));
        }
    };

    const [dateLabels, setDateLabels] = useState<any>()

    const [tempDownloadData, setTempDownloadData] = useState<boolean>(false);

    const [exportExcelColumns, setExportExcelColumns] = useState<Array<any>>([])

    const [exportExcelRowData, setExportExcelRowData] = useState<Array<any>>([])

    const [currentTab, setCurrentTab] = useState<VFFloatingTabItemProps>(tabs[0])
    const [verticalView, setVerticalView] = useState<boolean>(true)
    const [techRowData, setTechRowData] = useState<Array<any>>([])
    const [ecoRowData, setEcoRowData] = useState<Array<any>>([])
    const {date:lastRunDate} = useGetLastRunData()
    const [initialColumnState, setInitialColumnState] = useState<any>(undefined);
    const [techGridState, setTechGridState] = useState<any>();
    const [ecoGridState, setEcoGridState] = useState<any>();
    const [techMasterUIConfig, setTechMasterUIConfig] = useState<any>([]);
    const [ecoMasterUIConfig, setEcoMasterUIConfig] = useState<any>([]);
    const [isDisabled, setIsDisabled]= useState<boolean>(true)

    const actorPublication = `${user.user.id}:${user.user.email}:${lastRunDate || ''}`;
    const previousActorPublication = useRef(actorPublication);
    const hasAppliedFilter = useRef(false);
    useEffect(() => {
        if (previousActorPublication.current === actorPublication) return;
        previousActorPublication.current = actorPublication;
        Object.keys(requestVersion.current).forEach(key => { requestVersion.current[key as keyof typeof requestVersion.current]++; });
        configRequest.current = null;
        setInitialColumnState(undefined);
        setTechGridState(undefined);
        setEcoGridState(undefined);
        setTechRowData([]);
        setEcoRowData([]);
        setCountData(undefined);
        setPending({ tech: false, eco: false, count: false });
        if (hasAppliedFilter.current) onApplyFilter(currFilter, true);
    }, [actorPublication]);

    const RowsPerPageCurrTab = currentTab?.value === "on-hand"?userPageSizeTech:currentTab?.value === "pipeline"?userPageSizeEco:rowsPerPage 
    const savePageSizeTech = async( pageSize:number)=>{
        setUserPageSizeTech(pageSize)
        await getDataTech(currFilter , currentPageTech,pageSize)
    }

    const savePageSizeEco = async( pageSize:number)=>{
        setUserPageSizeEco(pageSize)
        await getDataEco(currFilter , currentPageEco,pageSize)
    }


    const techPaginationProps: VFPaginationProps = {
        selectedRows: 0,
        totalRows: techTotalRows,
        rowsPerPage: userPageSizeTech,
        currentPage: currentPageTech,
        handleChangePage: (currPage: number) => {
            getDataTech(getPreparedFilter(currFilter), currPage)
            setCurrentPageTech(currPage)
        },
        customPageSizeEnabled:true,
        userPageSize:userPageSizeTech,
        savePageSize:savePageSizeTech

    }

    const ecoPaginationProps: VFPaginationProps = {
        selectedRows: 0,
        totalRows: ecoTotalRows,
        rowsPerPage: userPageSizeEco,
        currentPage: currentPageEco,
        handleChangePage: (currPage: number) => {
            getDataEco(getPreparedFilter(currFilter), currPage);
            setCurrentPageEco(currPage)
        },
        customPageSizeEnabled:true,
        userPageSize:userPageSizeEco,
        savePageSize:savePageSizeEco

    }
    const techPaginationPropsForBoth: VFPaginationProps = {
        selectedRows: 0,
        totalRows: techTotalRows,
        rowsPerPage: userPageSizeTechForBoth,
        currentPage: currentPageTechForBoth,
        handleChangePage: (currPage: number) => {
            getDataTech(getPreparedFilter(currFilter), currPage , userPageSizeTechForBoth)
            setCurrentPageTechForBoth(currPage)
        },

    }
    const ecoPaginationPropsForBoth: VFPaginationProps = {
        selectedRows: 0,
        totalRows: ecoTotalRows,
        rowsPerPage: userPageSizeEcoForBoth,
        currentPage: currentPageEcoForBoth,
        handleChangePage: (currPage: number) => {
            getDataEco(getPreparedFilter(currFilter), currPage,userPageSizeEcoForBoth);
            setCurrentPageEcoForBoth(currPage)
        },
        customPageSizeEnabled:true,
        userPageSize:userPageSizeEco,
        savePageSize:savePageSizeEco
    }

    const defaultColDef = {
        floatingFilter: true,
        filter: 'agMultiColumnFilter',
        sortable: true,
        cellStyle: {
            "textAlign": "center",
            'textOverflow': 'ellipsis',
            'whiteSpace': 'nowrap'
        },
        flex: 1,
        width: 50,
        minWidth: 80,
        cellClass:'btr_cell_style'

    }

    const gridProps = useMemo(():AgGridReactProps=>{
        return {
            getMainMenuItems: MainMenuItemsCustomization,
            gridOptions: {
                components: {
                    grapCellRenderer: BPRGraphCellRenderer,
                    graphCellRenderer: SeasonalityGraphCellRenderer,
                    categoryCellRenderer: CategoryCellRenderer,
                    categoryToolTip: CategoryToolTip,
                    availabilityCellRenderer: AvailabilityCellRenderer,
                    colorCellRenderer: BTRColorCellRenderer,
                    tagsCellRenderer: TagsCellRenderer,
                    availabilityToolTip: AvailabilityToolTip,
                    // paginationPageSize:parseInt(process.env.REACT_APP_BTR_ROWS_PER_PAGE || '100'),


                },
                suppressDragLeaveHidesColumns: true,
                getRowStyle: (params: any) => {
                    if (params.node.rowIndex % 2 === 0) {
                        return { background: "#EBEBEB" };
                    }
                    return { background: "#F7F7F7" };
                },
            },
            rowHeight: 25,
            defaultColDef: defaultColDef,
        }
    }, [])


    const tempAgGridProps: AgGridReactProps = {
        onRowDataUpdated: (event) => {
            if (tempDownloadData) event.api.exportDataAsExcel({ fileName: currentTab.value === 'on-hand' ? "OnHandInv" : "PipelineInv", columnKeys: getColumnsForExcelExport(currentTab.value === 'on-hand' ? techColDefs : ecoColDefs) });
        }
    };

    // Report definitions are reused only within this mounted actor/publication.
    // Saved layouts still refresh on tab entry so external saves remain visible.
    const configRequest = useRef<Promise<void> | null>(null);
    const getBPRUiConfig = (force = false) => {
        if (!force && initialColumnState) return Promise.resolve();
        if (configRequest.current) return configRequest.current;
        const version = ++requestVersion.current.config;
        const request = (async () => {
            try {
                const response = await getUiConfig(UIColumnConfigName.BuffertrendReport);
                if (mounted.current && version === requestVersion.current.config)
                    setInitialColumnState(response.data.data);
            } catch (error) {
                if (mounted.current && version === requestVersion.current.config) notifyError("Something Went Wrong");
            } finally {
                if (version === requestVersion.current.config) configRequest.current = null;
            }
        })();
        configRequest.current = request;
        return request;
    };

    const getUserColumnConfig = async () => {
        const tab = currentTab.id;
        if (tab !== "1" && tab !== "2") return;
        const version = ++requestVersion.current.layout;
        try {
            const response = await getState({ reportname: tab === "1" ? UserUIColumnConfigName.BTROnHand : UserUIColumnConfigName.BTRPipeline });
            if (!mounted.current || version !== requestVersion.current.layout) return;
            const state = response.data.data.length ? JSON.parse(response.data.data) : undefined;
            if (tab === "1") setTechGridState(state);
            else setEcoGridState(state);
        } catch (error) {
            if (mounted.current && version === requestVersion.current.layout) notifyError(error instanceof Error ? error.message : String(error));
        }
    };

    const onResetCallback = async () => {
        await getBPRUiConfig(true);
        if (currentTab.id === "1") {

            setTechGridState({
                charts: [],
                columns: techMasterUIConfig,
                pivot: false,
            })
        } else if (currentTab.id === "2") {

            setEcoGridState({
                charts: [],
                columns: ecoMasterUIConfig,
                pivot: false,
            })
        }
        
    }

    const fetchRows = async (name: 'tech' | 'eco' | 'both', filter: any, pageNumber: number, pageSize: number) => {
        const branches: Array<'tech' | 'eco'> = name === 'both' ? ['tech', 'eco'] : [name];
        const versions = { ...requestVersion.current };
        branches.forEach(branch => { versions[branch] = ++requestVersion.current[branch]; });
        setPending(value => ({ ...value, ...Object.fromEntries(branches.map(branch => [branch, true])) }));
        const current = (branch: 'tech' | 'eco') => mounted.current && versions[branch] === requestVersion.current[branch];
        const loaderId = notifyLoader("Loading data");
        try {
            const response = await getBTRData({ id: 0, name, fields: [], filters: filter,
                paginationParameter: { pageNumber, recordsPerPage: pageSize }, ISExport: "0",
                displayPrepared: true, displayHorizon: horizon });
            const data = response.data.data;
            branches.forEach(branch => {
                if (current(branch)) {
                    const rows = displayRows(data, branch, horizon);
                    if (branch === 'tech') setTechRowData(rows);
                    else setEcoRowData(rows);
                }
            });
            if (branches.some(current)) setDateLabels((previous: any) => _.isEqual(previous, data.labels[0]) ? previous : data.labels[0]);
        } catch (error) {
            if (branches.some(current)) notifyError(error instanceof Error ? error.message : String(error));
            branches.forEach(branch => {
                if (current(branch)) {
                    if (branch === 'tech') setTechRowData([]);
                    else setEcoRowData([]);
                }
            });
        } finally {
            if (mounted.current) setPending(value => ({ ...value,
                ...Object.fromEntries(branches.filter(current).map(branch => [branch, false])) }));
            toast.dismiss(loaderId);
        }
    };
    const getDataTech = (filter: any, page: number, size?: number) => fetchRows('tech', filter, page, size || userPageSizeTech);
    const getDataEco = (filter: any, page: number, size?: number) => fetchRows('eco', filter, page, size || userPageSizeEco);
    const getData = (filter: any, page: number) => fetchRows('both', filter, page, RowsPerPageCurrTab);

    // useEffect(() => {
    //     const payload = {
    //         id: 0,
    //         name: 'tech',
    //         fields: [],
    //         filters: currFilter,
    //         paginationParameter: {
    //             pageNumber: 1,
    //             recordsPerPage: rowsPerPage
    //         },
    //     }
    //     getBTRDataCount(payload)
    //     getDataTech(currFilter, 1)
    //     getBPRUiConfig();
    // }, [])

    const getPreparedFilter = (filter: BPRFilterState): BPRFilterState => {
        const doesCategoryExist = (filter.availabilityFilter.filters.length > 0 && filter.availabilityFilter.filters.some((f) => f.name === "AF8"))
        const tempFilter = _.cloneDeep(filter)
        if (doesCategoryExist) {

            tempFilter.availabilityFilter.filters = tempFilter.availabilityFilter.filters.map((f) => {
                if (f.name === "AF8") {
                    return {
                        ...f,
                        value: BTRCategoryTextToNumberMapper[f.value] ?? f.value
                    };
                }
                return f; 
            })
        }
        return tempFilter
    }

    const onApplyFilter = async (filter: BPRFilterState, refreshConfig = false) => {
        hasAppliedFilter.current = true;
        requestVersion.current.tech++;
        requestVersion.current.eco++;
        setPending(value => ({ ...value, tech: false, eco: false }));
        setCurrFilter(filter)
        setCurrentPageTech(1)
        setCurrentPageEco(1)
        setCurrentPageTechForBoth(1)
        setCurrentPageEcoForBoth(1)
        const tempFilter = getPreparedFilter(filter)
        const payload = {
            id: 0,
            name: '',
            fields: [],
            filters: tempFilter,
            paginationParameter: {
                pageNumber: 1,
                recordsPerPage: RowsPerPageCurrTab
            },
        }
        getBTRDataCount(payload)
        if(currentTab?.value === "on-hand") getDataTech(tempFilter, 1)
        else if(currentTab?.value === "pipeline") getDataEco(tempFilter, 1)
        else getData(tempFilter, 1)
        getBPRUiConfig(refreshConfig)
    }


    const onDeleteFilter = async (parentId: any, filterId: any, value: any) => {
        const updatedFilter = onDelete(parentId, filterId, value)
        onApplyFilter(updatedFilter)
    }

    const toggleVerticalView = (isVertical: boolean) => setVerticalView(isVertical)

    const toggleCurrentTab = (tab: VFFloatingTabItemProps) => {
        if (tab.id === currentTab.id) return;
        requestVersion.current.tech++;
        requestVersion.current.eco++;
        requestVersion.current.layout++;
        setPending(value => ({ ...value, tech: false, eco: false }));
        setCurrentTab(tab);
    }

    const Extras = () => {
        if (dateLabels) {
            return Object.entries(dateLabels).map((item: any, index: any) => {
                return {
                    field: item[0],
                    colId: item[0],
                    headerName: format(item[1], 'PP'),
                    cellRenderer: 'colorCellRenderer',
                    cellRendererParams: (params: any) => {
                        return {
                            colorValue: params.data[item[0]]
                        }
                    },
                    minWidth: 100,
                    position: (index + initialColumnState.length),  //column should be at position onwards main columns
                    ...(item[0].startsWith('D') && parseInt(item[0].slice(1)) >= 1 && parseInt(item[0].slice(1)) <= 90 ? { filter: 'agNumberColumnFilter' } : {}),
                }
            })
        } else {
            return [];
        }
    };

    const onOpenDailyDataGraph = useCallback((params:any) => loadDailyData(dispatch, getDailyData, params.data, 'WhCode'), [dispatch, getDailyData]);

    const CustomHeader = useMemo(() => ({
        dailydatagraph: {
            width: 45,
            minWidth: 45,
            filter: false,
            cellRenderer: 'grapCellRenderer',
            cellRendererParams: { onOpenDailyDataGraph: onOpenDailyDataGraph },
            lockPosition: true,
            resizable: false,
            floatingFilter: false,
            suppressColumnsToolPanel: false,
            pinned: 'left',
            headerTooltip: "Daily Data Graph",
            sortable:false,
            headerName:"Daily Data Graph",
            suppressMenu:true,
        },
        Category: {
            cellRenderer: 'categoryCellRenderer',
            tooltipField: "Category",
            tooltipComponent: 'categoryToolTip',
            pinned: 'left',
        },
        Availability: {
            cellRenderer: 'availabilityCellRenderer',
            tooltipField: "Availability",
            tooltipComponent: 'availabilityToolTip',
            pinned: 'left',
        },
        Tags: {
            cellRenderer: 'tagsCellRenderer',
            pinned: 'left',
        },
        SKUCode: {
            pinned: 'left',
        },
        SKUDescription: {
            pinned: 'left',
        },
        WhCode: {
            pinned: 'left',
        },
        LocationName: {
            pinned: 'left',
        },
        Norm: {
            pinned: 'left',
        },
        VirtualNorm: {
            pinned: 'left',
        },
    }), [onOpenDailyDataGraph]);
    const techColDefs = useMemo((): Array<ColDef> => {
        if (initialColumnState) {
            const colDefs = getColumnDefinationsMTA(initialColumnState, CustomHeader, Extras());
            colDefs.map((colDef: any) => {
                if (initialColumnState.find((initialColumnState: any) => initialColumnState.Col_Code === colDef.colId)) {
                    colDef.minWidth = 80;
                }
                return colDef
            })
            const result = colDefs.filter((r: any) => (!r.colId?.startsWith('D') || r.colId === 'DailyDataGraph') || (r.colId.startsWith('D') && parseInt(r.colId.slice(1)) > 90 - horizon))
            return result;
        } else return [];
    }, [initialColumnState, CustomHeader, horizon, dateLabels]);

    const ecoColDefs = useMemo((): Array<ColDef> => {
        if (initialColumnState) {
            let colDefs;
            if (verticalView && currentTab.id === "1") {
                const removeCols = ['Category', "LocationName", "Norm", "SKUCode", "SKUDescription", "Tags", "VirtualNorm", "RN", "pc", "pn","WhCode"];
                colDefs = getColumnDefinationsMTA(initialColumnState, CustomHeader, Extras(), removeCols);
            } else {
                colDefs = getColumnDefinationsMTA(initialColumnState, CustomHeader, Extras());
            }

            // Set column width for all columns except date columns
            colDefs.map((colDef: any) => {
                if (initialColumnState.find((initialColumnState: any) => initialColumnState.Col_Code === colDef.colId)) {
                    colDef.minWidth = 80;
                }
                return colDef
            })
            const result = colDefs.filter((r: any) => (!r.colId?.startsWith('D')) || (r.colId.startsWith('D') && parseInt(r.colId.slice(1)) > 90 - horizon))
            return result;
        } else return [];
    }, [initialColumnState, CustomHeader, horizon, dateLabels, verticalView, currentTab.id]);


    const configReady = Boolean(initialColumnState);
    useEffect(() => {
        if (initialColumnState) getUserColumnConfig();
        // Refresh on tab entry/initial readiness; Reset must not reload a saved layout.
    }, [currentTab.id, configReady]);

    // Readiness, not row replacement or an arbitrary delay, restores each layout.
    const restoredLayout = useRef<{ tech?: any, eco?: any }>({});
    const defaultLayoutApi = useRef<{ tech?: any, eco?: any }>({});
    const restoreLayout = (branch: 'tech' | 'eco', api: any, columns: any[], state: any) => {
        if (!api || api.isDestroyed?.() || !columns.length) return;
        // Capture defaults before saved state is applied, including on grid-ready
        // races. Row refreshes must not turn a saved layout into the Reset target.
        if (defaultLayoutApi.current[branch] !== api) {
            defaultLayoutApi.current[branch] = api;
            if (branch === 'tech') setTechMasterUIConfig(api.getColumnState());
            else setEcoMasterUIConfig(api.getColumnState());
        }
        if (!state?.columns) return;
        const previous = restoredLayout.current[branch];
        if (previous?.api === api && previous?.columns === columns && previous?.state === state) return;
        if (api.applyColumnState({ state: state.columns, applyOrder: true })) {
            api.sizeColumnsToFit();
            restoredLayout.current[branch] = { api, columns, state };
        }
    };
    useEffect(() => {
        if (currentTab.id === "1") restoreLayout('tech', techInternalRef?.api, techColDefs, techGridState);
    }, [techInternalRef, techColDefs, techGridState, currentTab.id]);
    useEffect(() => {
        if (currentTab.id === "2") restoreLayout('eco', ecoInternalRef?.api, ecoColDefs, ecoGridState);
    }, [ecoInternalRef, ecoColDefs, ecoGridState, currentTab.id]);

    useEffect(() => {
        if (!initialColumnState) return;
        if (currentTab.id === "1") getDataTech(currFilter, 1);
        else if (currentTab.id === "2") getDataEco(currFilter, 1);
        else getData(currFilter, 1);
        // A tab change fetches rows; receiving configuration/rows must not refetch.
    }, [currentTab.id]);

    const renderView = () => {
        switch (currentTab.id) {
            case "1":
                return (
                    <>
                        <BTRTableHeader>
                            On-Hand Inventory View Trend Report
                        </BTRTableHeader>
                        <div style={{height: '100%'}}>
                        <CustomVFTable
                            height={"90%"}
                            tooltipHideDelay={100000}
                            tooltipShowDelay={0}
                            tooltipMouseTrack={true}
                            ref={techRef}
                            disableZoomScaling
                            columnDefs={techColDefs}
                            rowData={techRowData}
                            {...gridProps}
                            pagination={false}
                            paginationPageSize={parseInt(BTR_ROWS_PER_PAGE || '100')}
                            maintainColumnOrder
                            onGridReady={(params) => setTechInternalRef(params)}
                            onNewColumnsLoaded={(params) => restoreLayout('tech', params.api, techColDefs, techGridState)}
                            onFilterChanged={() => {
                                const filterModel = techRef?.current?.api?.getFilterModel();
                                if (filterModel && Object.keys(filterModel).length > 0) {
                                  setIsDisabled(false);
                                } else {
                                  setIsDisabled(true);
                                }
                            }}                        />
                        {
                        initialColumnState &&
                            <VFPagination 
                            {...techPaginationProps} 
                            resetGridRef={techRef} 
                            isDisabled={isDisabled}/>
                        }
                        </div>
                    </>
                )
            case "2":
                return (
                    <>
                        <BTRTableHeader>
                            Pipeline Inventory Trend Report
                        </BTRTableHeader>
                        
                        <div style={{height:'100%'}}>
                        <CustomVFTable
                            height={"90%"}
                            tooltipHideDelay={100000}
                            tooltipShowDelay={0}
                            tooltipMouseTrack={true}
                            ref={ecoRef}
                            disableZoomScaling
                            columnDefs={ecoColDefs}
                            rowData={ecoRowData}
                            {...gridProps}
                            pagination={false}
                            paginationPageSize={parseInt(BTR_ROWS_PER_PAGE || '100')}
                            maintainColumnOrder
                            onGridReady={(params) => setEcoInternalRef(params)}
                            onNewColumnsLoaded={(params) => restoreLayout('eco', params.api, ecoColDefs, ecoGridState)}
                            onFilterChanged={() => {
                                const filterModel = ecoRef?.current?.api?.getFilterModel();
                                if (filterModel && Object.keys(filterModel).length > 0) {
                                  setIsDisabled(false);
                                } else {
                                  setIsDisabled(true);
                                }
                            }}  

                        />
                        {
                        initialColumnState &&
                        <VFPagination
                            {...ecoPaginationProps} 
                            resetGridRef={ecoRef} 
                            isDisabled={isDisabled}/>
                             }
                        </div>   
                    </>
                )

            case "3":
                    if (verticalView) return (
                        <VerticalSplitView
                            themeUi={themeUi}
                            techTable={{
                                columnDefs: techColDefs,
                                rowData: techRowData,
                                header: "On-Hand Inventory View Trend Report",
                                paginationProps: techPaginationPropsForBoth,
                                ...gridProps
                            }}
                            ecoTable={{
                                columnDefs: ecoColDefs,
                                paginationProps: ecoPaginationPropsForBoth,
                                rowData: ecoRowData,
                                header: "Pipeline Inventory Trend Report",
                                ...gridProps
                            }}
                            isLocked={isLockMode}
                            toggleLockMode={toggleLockMode}
                            initialColumnState={initialColumnState}
                        />
                    )
    
                    return (
                        <HorizontalSplitView
                            themeUi={themeUi}
                            techTable={{
                                columnDefs: techColDefs,
                                rowData: techRowData,
                                header: "On-Hand Inventory View Trend Report",
                                paginationProps: techPaginationPropsForBoth,
                                ...gridProps
                            }}
                            ecoTable={{
                                columnDefs: ecoColDefs,
                                rowData: ecoRowData,
                                header: "Pipeline Inventory Trend Report",
                                paginationProps: ecoPaginationPropsForBoth,
                                ...gridProps
                            }}
                            isLocked={isLockMode}
                            toggleLockMode={toggleLockMode}
                            initialColumnState={initialColumnState}
                        />
                    )
            default:
                return <CustomVFTable columnDefs={[]} rowData={[]} {...gridProps} />
        }
    }

    // const onExportToExcelCallBack = async (pageNumber: number, page: string) => {
    //     const tempFilter = getPreparedFilter(currFilter)
    //     const payload = {
    //         id: 0,
    //         name: page==='on-hand'?'tech':'eco',
    //         fields: [],
    //         filters: tempFilter,
    //         paginationParameter: {
    //             pageNumber: pageNumber,
    //             recordsPerPage: 5000
    //         },
    //     }
    //     const data = await getBTRData(payload)
    //     if (page == 'on-hand') return data.data.data.tech
    //     return data.data.data.eco

    // }

    const onExportToExcelCallBack = async (pageNumber: number, page: string) => {
        if (pending.tech || pending.eco || pending.count) return;
        const tempFilter = getPreparedFilter(currFilter)
        const headersData = (page === 'on-hand') ? (techRef?.current?.api?.getColumnState() || []) : (ecoRef?.current?.api?.getColumnState() || []);
        const colDefs = (page === 'on-hand') ? techColDefs : ecoColDefs;
        const colMap = new Map(colDefs.map((col: any) => [col.colId, col.headerName]));
        const resultArray = headersData
        .filter((col: any) => colMap.has(col.colId) && col.colId !== "dailydatagraph")
        .map((col: any) => ({ Field: col.colId, HeaderName: colMap.get(col.colId) }));
      
        const payload = {
            Headers: resultArray,
            id: 0,
            name: page==='on-hand'?'tech':'eco',
            fields: [],
            filters: tempFilter,
            paginationParameter: {
                pageNumber: pageNumber
            },
            ISExport:"1",
            reportName:"BTR",
            stream:1,
            responseType: `arraybuffer`
        }
        notifyLoader("Downloading Data...")
        try {
            // const data = await getBTRData(payload)
            let filename = "";
            if (page === "on-hand") {
                filename = "On_Hand_Inventory";
              } else {
                filename = "Pipeline_Inventory";
              }
            await CsvExportMTA(payload, filename);
            notifySuccess(`Data Exported Successfully`);
        }
        catch(error) {
            console.log(error);
            notifyError("Error Exporting Excel")
        }
        
        

    }
 
    

    return {
        ecoRef,
        techRef,
        tempRef,
        currentTab,
        verticalView,
        isLoading: pending.tech || pending.eco || pending.count || isUIConfigLoading || isSavedDataLoading,
        isError,
        techColDefs,
        techTotalRows,
        toggleVerticalView,
        toggleCurrentTab,
        renderView,
        onExportToExcelCallBack,
        tempDownloadData,
        isLockMode,
        toggleLockMode,
        setTempDownloadData,
        tempAgGridProps,
        exportExcelRowData,
        setExportExcelRowData,
        exportExcelColumns,
        setExportExcelColumns,
        currFilter,
        themeUi,
        setCurrFilter,
        onDeleteFilter,
        onApplyFilter,
        horizon,
        ecoColDefs,
        setHorizon,
        lastRunDate,
        dailyData,
        showDailyDataGraphModal,
        showNormChangeHistoryTable,
        onResetCallback
    }
}

export default useBTR
