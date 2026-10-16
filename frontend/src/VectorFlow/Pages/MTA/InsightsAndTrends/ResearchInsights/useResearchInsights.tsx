import { beginScreen, screenRendered, useScreenProbe } from '../../../../../performance/screenProbe';
import { settleRequestPair } from "../../requestPair"
import { useEffect, useState, useMemo, useRef } from 'react'
import { AgGridReactProps } from 'ag-grid-react'
import { GridRef } from '../../../../../VectorFlow/types/MDM'
import { convertUiConfigToOptions, MainMenuItemsCustomization, getColumnDefinationsMTA } from '../../../../../helpers/utils'

import { BPRTagsCellRenderer, BPRTechColorCellRenderer, BPREcoColorCellRenderer } from '../../SupplyChainIntelligenceHub/BPR/BPRCellRenderers'
import BPRGraphCellRenderer from '../../SupplyChainIntelligenceHub/BPR/BPRGraphCellRenderer'

import { useGetBPRData, useGetBPRDataCount, useGetDailyData } from "./../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR"
import { useGetState } from "./../../../../../VectorFlow/Services/MTA/Common/UserUIConfig";
import { isSameDay } from 'date-fns'
import { researchHistoryPositions } from './historyPositions'
import { startResearchLayoutReads, applyResearchSavedLayout } from './layoutReads'
import { ReseachInsightsGraphState } from '../../../../../VectorFlow/types/BPR'
import { useGetUpdatedGraphData, useGetHistroricalAvailabilityData } from '../../../../../VectorFlow/Services/MTA/InsightsAndTrends/ResearchInsights'
import { notifyError, notifyLoader,notifySuccess } from '../../../../../helpers/notify'
import { toast } from 'react-toastify'


import { useSelector, useDispatch } from 'react-redux'

import { RootState } from '../../../../../redux/store/store'
import { loadDailyData } from '../../../../../components/VectorFLOW/commons/DailyDataGraphModal/loadDailyData';
import useBPRFilter from '../../../../../hooks/useBPRFilter'
import { defaultAgGridSideBarForBPR } from '../../../../../helpers/BPRConstants'
import { ColDef } from 'ag-grid-enterprise'
import useGetLastRunData from "../../../../../hooks/useGetLastRunData"
import { useGetUIConfigData } from '../../../../Services/MTA/Common/UIConfig'
import { UIColumnConfigName, UserUIColumnConfigName } from '../../../../../helpers/Enum'

const useResearchInsights = () => {
    useScreenProbe('Research');

    const { mutateAsync: getUiConfig, isLoading: isUIConfigLoading } = useGetUIConfigData();

    const dispatch = useDispatch();

    const ref = useRef<GridRef>();
    const tempRef = useRef()

    const [internalRef,setInternalRef] = useState<any>()

    const {mutateAsync:getState,isLoading:isSavedDataLoading} = useGetState()
    const [gridState,setGridState] = useState<any>()

    const { state: currentFilter, setState: setCurrentFilter, onDelete } = useBPRFilter()

    const [tempDownloadData, setTempDownloadData] = useState<boolean>(false);

    const [exportExcelColumns, setExportExcelColumns] = useState<Array<any>>([])

    const [exportExcelRowData, setExportExcelRowData] = useState<Array<any>>([])

    const { mutateAsync: getDailyData } = useGetDailyData();

    const { mutateAsync: getUpdatedGraphData, isLoading: isUpdatedGraphDataLoading } = useGetUpdatedGraphData()

    const [ResearchInsightsData, setResearchInsightsRowData] = useState<Array<any>>([])
    const { mutateAsync: getBPRData , isLoading: isBPRLoading} = useGetBPRData()

    const { mutateAsync: getBPRDataCount, isLoading: isBPRDataCountLoading } = useGetBPRDataCount()

    const { data: historicalAvailabilityResponse ,isLoading:isHistoricalAvailabilityLoading } = useGetHistroricalAvailabilityData()

    const [currGridPage,setCurrGridPage] = useState<number>(1)
    const [recordCount,setRecordCount] = useState<number>()

    const [isGraphOneOpen,setIsGraphOneOpen] = useState<boolean>(false)
    const [horizon,setHorizon] = useState<number>(10)
    const [graphState,setGraphState] = useState<'default' | 'calender' | 'graph'>('default')
    const [calenderType,setCalenderType] = useState<'Tech' | 'Eco'>('Tech')
    const [expandedGraphId,setExpandedGraphId] = useState<1 | 2>(1)
    const [generalFilterOptions,setGeneralFilterOptions] = useState();
    const [ResearchInsightsColumns,setResearchInsightsColumns] = useState<ColDef[]>([])


    const showDailyDataGraphModal = useSelector((state:RootState) => state.mta.showDailyDataGraphModal);
    const showNormChangeHistoryTable = useSelector((state:RootState) => state.mta.showNormChangeHistoryTable);
    const dailyData = useSelector((state:RootState) => state.mta.dailyData);
    const [initialColumnState, setInitialColumnState] = useState<any>(undefined);
    const savedLayoutRead = useRef<ReturnType<typeof startResearchLayoutReads>['saved']>();
    const [masterUIConfig, setMasterUIConfig] = useState<any>([]);
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const RESEARCHINSIGHT_ROWS_PER_PAGE = EnvConfig['RESEARCHINSIGHT_ROWS_PER_PAGE'];
    const [userPageSize, setUserPageSize] = useState<number>(
        RESEARCHINSIGHT_ROWS_PER_PAGE ? parseInt(RESEARCHINSIGHT_ROWS_PER_PAGE) : 50
    )
    const [graphs, setGraphs] = useState<Array<ReseachInsightsGraphState>>([
        {
            type: { label: 'Self', value: 'Self' },
            pen: { label: 'Tech', value: 'Tech' },
            filters: [],
            id: 1
        },
        {
            type: { label: 'Parent', value: 'Parent' },
            pen: { label: 'Tech', value: 'Tech' },
            filters: [],
            id: 2
        }
    ])


    const [selectedRowsDates, setSelectedRowsDates] = useState<Array<any>>([])
    useEffect(() => {
        if (selectedRowsDates.length && graphState !== 'default' && !isUpdatedGraphDataLoading) {
            screenRendered('Research');
        }
    }, [selectedRowsDates, graphState, isUpdatedGraphDataLoading]);
    const {date:lastRunDate} = useGetLastRunData()

              
    const getRIUiConfig = async () => {
        try {
            const reads = startResearchLayoutReads(
                () => getUiConfig(UIColumnConfigName.Research_Insights),
                () => getState({ "reportname": UserUIColumnConfigName.Research_Insights })
            );
            savedLayoutRead.current = reads.saved;
            const response = await reads.configuration;
            setInitialColumnState(response.data.data);
        } catch (err: any) {
            notifyError("Something Went Wrong")
        }
    }

    useEffect(() => {
        const getTableState = async () => {
            try {
                const MappedColumns = getColumnDefinationsMTA(initialColumnState, CustomHeader, extras);
                  
                setGridState({
                    charts: [],
                    columns: MappedColumns,
                    pivot: false
                })
                setResearchInsightsColumns(MappedColumns);
                await getUserColumnConfig();
            
            } catch (err: any) {
                console.log(err)
            }
        }
        if (initialColumnState !== undefined) {
            getTableState();
            setGeneralFilterOptions(convertUiConfigToOptions(initialColumnState))
        }
    }, [initialColumnState]);


    useEffect(() => {
        if (ResearchInsightsColumns.length) {
            if (internalRef?.api) {
                setMasterUIConfig(internalRef.api.getColumnState());
            }
        }
    }, [internalRef, ResearchInsightsColumns]);
          
    const getUserColumnConfig = async () => {
        await applyResearchSavedLayout(savedLayoutRead.current!, setGridState);
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

    const onResetCallback = async () => {
        setGridState({
            charts: [],
            columns: masterUIConfig,
            pivot: false,
        })
    };


    useEffect(() => {
        async function getBPRRowData() {
            resetState()
            await Promise.all([getCountAndRowData(currentFilter), getRIUiConfig()]);
        }
        getBPRRowData().catch((err: any) => notifyError(err))
    }, [])

    const customCellRenderers = useMemo(() => ({
        grapCellRenderer:BPRGraphCellRenderer,
        colorTechCellRenderer:BPRTechColorCellRenderer,
        colorEcoCellRenderer:BPREcoColorCellRenderer,
        tagsCellRenderer:BPRTagsCellRenderer
      }), []);


      const defaultColDefObject = useMemo(()=>{
        return {
            floatingFilter: true,
            cellStyle:{
                flex: 1,
                textAlign: 'center',
                height: '50px',
                fontStyle: 'normal',
                display: 'block',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
            },
        }
      },[])
  
    const agGridProps:AgGridReactProps = useMemo(()=>{
        return {
        
            suppressRowTransform:true,
            readOnlyEdit:true,
            rowSelection:'multiple',
            gridOptions:{
                rowHeight:50,
                getRowStyle: (params: any) => {
                if (params.node.rowIndex % 2 === 0) {
                    return { background: "#EBEBEB" };
                }
                return { background: "#F7F7F7" };
                },
            },
            sideBar:defaultAgGridSideBarForBPR,
            // paginationPageSize:25,
            getMainMenuItems: MainMenuItemsCustomization,
            paginationPageSize:parseInt(RESEARCHINSIGHT_ROWS_PER_PAGE || '100'),
            suppressRowClickSelection:true,
            components:customCellRenderers,
            defaultColDef:defaultColDefObject,
            onGridReady:(params)=>setInternalRef(params),
            onFirstDataRendered:()=>screenRendered('Research'),
            onRowDataUpdated:()=>screenRendered('Research')
        }
    },[])

    const tempAgGridProps:AgGridReactProps = useMemo (()=> {
        return{
            rowSelection: 'multiple',
            onRowDataUpdated:(event)=>{
                if(tempDownloadData) event?.api?.exportDataAsExcel({fileName:'ResearchInsights',columnKeys:ref.current?.api.getAllDisplayedColumns().map((c)=>c.getColId())});
            }
        }
    },[tempDownloadData])      

    const getRecordCount = async (filter: any) => {
        const countData = await getBPRDataCount({
            id: 1,
            name: "",
            fields: [],
            filters: filter,
            paginationParameter: {
                pageNumber: 1,
                recordsPerPage: parseInt(RESEARCHINSIGHT_ROWS_PER_PAGE || '50')
            }
        })

        setRecordCount(countData.data.recordCount)
    }

    const readRowData = (filter: any, pageNo: number, pageSize?: number) => getBPRData({
            id: 1,
            name: "",
            fields: [],
            filters: filter,
            paginationParameter: {
                pageNumber: pageNo,
                recordsPerPage: pageSize || userPageSize|| parseInt(RESEARCHINSIGHT_ROWS_PER_PAGE || '50')
            }
        })

    const getRowData = async (filter: any, pageNo: number, pageSize?: number) => {
        notifyLoader("Loading Grid Data")
        const rowData = await readRowData(filter, pageNo, pageSize)
        toast.dismiss()
        notifySuccess("Data Loaded Successfully")
        setResearchInsightsRowData(rowData.data.data)
    }

    const getCountAndRowData = async (filter: any) => {
        const toastId = notifyLoader("Loading Grid Data")
        try {
            const { grid } = await settleRequestPair(
                () => getRecordCount(filter),
                () => readRowData(filter, 1)
            )
            setResearchInsightsRowData(grid.data.data)
            notifySuccess("Data Loaded Successfully")
        } finally {
            toast.dismiss(toastId)
        }
    }

    const onApplyFilter = async (filter: any) => {
        beginScreen('Research', 'filter');
        resetState()
        setCurrentFilter(filter)
        setCurrGridPage(1)
        try {
            await getCountAndRowData(filter)
        } catch (err: any) {
            notifyError(err)
        }

    }

    const onDeleteFilter = async (parentId: any, filterId: any, value: any) => {
        const updatedFilter = onDelete(parentId, filterId, value)
        onApplyFilter(updatedFilter)
    }

    const handlePageChange = async (pageNo: number) => {
        resetState()
        setCurrGridPage(pageNo)
        try {
            await getRowData(currentFilter, pageNo)
        } catch (err: any) {
            notifyError(err)
        }
    }
    
    const getColor = (date:any)=>{
      
        const doesExist = calenderData.slice(0,horizon).find((d)=>isSameDay(d.date,date))
        return doesExist?doesExist.color:'gray'
    }

    const savePageSize = async( pageSize:number)=>{
        setUserPageSize(pageSize)
        await getRowData(currentFilter , currGridPage,pageSize)
    }

    function getColorValues(jsonData: any) {

        const colorValues = [];
        for (const key in jsonData) {
            if (key.startsWith('D')) {
                colorValues.push(jsonData[key]);
            }
        }
        // Rather calculate range w.r.t horizon in the later functions instead of at the core
        // if(colorValues.length>horizon){
        //     return colorValues.slice(colorValues.length-horizon);
        // }
        return colorValues;
    }

    function convertToObjects(colorArray: Array<string>) {

        const today = new Date(lastRunDate);
        const result = [];
        // Loop through each color in the array
        for (let i = 0; i < colorArray.length; i++) {
            const daysBeforeToday = colorArray.length - i;
            const date = new Date(today);
            date.setDate(today.getDate() - daysBeforeToday+2); // Adding 1 to start from 1 day ago

            const dateString = date.toISOString().slice(0, 10); // Get date in YYYY-MM-DD format

            const color = colorArray[i];

            result.push({ date: dateString, color: color });
        }
    
        return result.reverse();
    }

    const resetState = () => {
        setSelectedRowsDates([])
        setResearchInsightsRowData([])
        // ref.current?.api.setNodesSelected({nodes:[],newValue:false})
        setGraphState('default')
    }

    const getColorData = (array: Array<any>) => {
        const colorFrequencyArray: any = [];
        for (const { field, date } of researchHistoryPositions(lastRunDate, horizon)) {
            const colorFrequency: any = {
                Red: 0,
                Blue: 0,
                Green: 0,
                Yellow: 0,
                Black: 0,
                White: 0
            };
            array.forEach((obj: any) => {
                const color = obj[field];
                if (color) colorFrequency[color]++
                else colorFrequency[color] = 0
            })
            colorFrequencyArray.push({ ...colorFrequency, date })
        }
        return colorFrequencyArray
    }

    const handleOnUpdateGraph = async () => {
        const selectedRows = ref.current?.api.getSelectedRows()
        if (selectedRows && selectedRows.length === 0) return setGraphState('default')
        beginScreen('Research', 'graph');
        const loaderId = notifyLoader('Loading graph data')
        try {
            const data = await getUpdatedGraphData({
                data: selectedRows?.map((s) => {
                    return {
                        "SKUCode": s.SKUCode,
                        "WhCode": s.WHCode
                    }
                })
            })
            setSelectedRowsDates(data.data.data)
            if (selectedRows && selectedRows.length > 1) {
                return setGraphState('graph')
            }
            if (selectedRows) {
                return setGraphState('calender')

            }
        } catch (error: any) {
            notifyError(error)
        } finally {
            toast.dismiss(loaderId)
        }
    }


    const updateGraphState = (id: number, property: string, payload: any) => {
        if (property !== 'filters') {
            return setGraphs(graphs.map((graph: ReseachInsightsGraphState) => {
                if (graph.id === id) {
                    return {
                        ...graph,
                        [property]: payload,
                        filters: []
                    }
                }
                return graph
            }))
        }
        return setGraphs(graphs.map((graph:ReseachInsightsGraphState)=>{
            if(graph.id===id){
                console.log(id)
                return {
                    ...graph,
                    [property]: payload
                }
            }
            return graph
        }))
    }

    const toggleGraphModal = (open: boolean, data?: any) => {
        if (data) {
            setExpandedGraphId(data)
        }
        setIsGraphOneOpen(open)
    }

    const calenderData = useMemo(() => {
        const selectedRows = ref.current?.api.getSelectedRows()
        if (selectedRows && selectedRows.length === 1) {
            const allDates = selectedRowsDates.find((row: any) => row.Type === 'Self' && row.Pen === calenderType)
            if (allDates) {
                return convertToObjects(getColorValues(allDates))

            }
        }
        return []
    }, [selectedRowsDates, horizon, calenderType])

    const calenderDataWithHorizon = useMemo(()=>calenderData.slice(0,horizon),[calenderData])

    const continuousBlack = useMemo(() => {
        let count = 0;
        for (let i = 0; i < calenderData.length; i++) {
            if (calenderData[i].color === 'Black') {
                count++;
            } else {
                break; 
            }
        }
        return count;
    }, [calenderData]);

    const continuousBlackAndRed = useMemo(() => {
        let count = 0;
        for (let i = 0; i < calenderData.length; i++) {
            const currColor = calenderData[i].color
            if ( currColor  === 'Black' || currColor === 'Red') {
                count++;
            } else {
                break; 
            }
        }
        return count;
    }, [calenderData]);

    const continuousWhite = useMemo(() => {
        let count = 0;
        for (let i = 0; i < calenderData.length; i++) {
            const currColor = calenderData[i].color
            if ( currColor  === 'White') {
                count++;
            } else {
                break; 
            }
        }
        return count;
    }, [calenderData]);
    

    

    const blackCount = useMemo(()=>{
        return Math.round(((calenderDataWithHorizon.filter((row:any)=>row.color==='Black').length)/horizon)*100)
    },[calenderDataWithHorizon])

    const redCount = useMemo(()=>{
        return Math.round(((calenderDataWithHorizon.filter((row:any)=>row.color==='Red').length)/horizon)*100)
    },[calenderDataWithHorizon])

    const whiteCount = useMemo(()=>{
        return Math.round(((calenderDataWithHorizon.filter((row:any)=>row.color==='White').length)/horizon)*100)
    },[calenderDataWithHorizon])

    const selfGraphData = useMemo(() => {
        const selectedRows = ref.current?.api.getSelectedRows()
        if (selectedRows && selectedRows.length > 1) {
            let selfArraySelectedData = selectedRowsDates.filter((row: any) => row.Pen === graphs[0].pen.value && row.Type === graphs[0].type.value)
            const filters = graphs[0].filters
            if (filters.length > 0) {
                filters.forEach((filter) => {
                    selfArraySelectedData = selfArraySelectedData.filter((row: any) => row[filter.key] === filter.value)
                })
            }
            const selfData = getColorData(selfArraySelectedData)
            return selfData
        }
        return []
    }, [graphs, selectedRowsDates, horizon, lastRunDate])

    const locationGraphData = useMemo(()=>{
        const selectedRows =  ref.current?.api.getSelectedRows()
       
        if(selectedRows && selectedRows.length>1){
            let locationArraySelectedData = selectedRowsDates.filter((row:any)=>
                row.Pen===graphs[1].pen.value && row.Type===graphs[1].type.value
            )
            const filters =graphs[1].filters
            const whKeys = [{label:'Child',value:'ChildCode'},{label:'Parent',value:'ParentWhCode'}]
            const currWhKey = whKeys.find((k)=>k.label ===graphs[expandedGraphId -1].type.value)?.value || 'ChildCode'
            if (filters.length > 0) {
                locationArraySelectedData = locationArraySelectedData.filter((row: any) =>{
                    return filters.every(filter => row[filter.key!=='Whcode'?filter.key:currWhKey] === filter.value)
            });
            }   
            const locationData = getColorData(locationArraySelectedData)   
            return locationData
        }
        return []
    }, [graphs, selectedRowsDates, horizon, lastRunDate])

    // console.log(selectedRowsDates)

    const expandedGraphAllFilterValues = useMemo(()=>{
        const index = expandedGraphId-1
        const locationArraySelectedData = selectedRowsDates.filter((row:any)=>row.Pen===graphs[index].pen.value && row.Type===graphs[index].type.value)
        let uniqueSkus:any = []
        let uniqueWhCode:any = []
        const whKeys = [{label:'Self',value:'Whcode'},{label:'Child',value:'ChildCode'},{label:'Parent',value:'ParentWhCode'}]
        const currWhKey = whKeys.find((k)=>k.label ===graphs[index].type.value)?.value || 'Whcode'
        locationArraySelectedData.map((row:any)=>{
            if(!uniqueSkus.includes(row.SKUCode)){
                uniqueSkus.push(row.SKUCode)
            }
            if(!uniqueWhCode.includes(row[currWhKey])){
                uniqueWhCode.push(row[currWhKey])
            }
           
        })
        uniqueSkus = uniqueSkus.map((sku: string) => {
            return {
                value: sku,
                label: sku
            }
        })
        uniqueWhCode = uniqueWhCode.map((whcode: string) => {
            return {
                value: whcode,
                label: whcode
            }
        })
        return {
            skus: uniqueSkus,
            whcodes: uniqueWhCode
        }
    },[selectedRowsDates,graphs,expandedGraphId])

    const historicalAvailabilityData = useMemo(() => {
        if (historicalAvailabilityResponse) {
            return historicalAvailabilityResponse.data.data[0]
        }
        return {
            Availability_01_30: 0,
            Availability_31_60: 0,
            Availability_61_90: 0
        }
    }, [historicalAvailabilityResponse])


    const onOpenDailyDataGraph = async (params: any) => {
        await loadDailyData(dispatch, getDailyData, params.data, 'WHCode');
    }

    // const ResearchInsightsColumns = useMemo(() => {
    //     return mapResearchInsightsFieldsToColDefs(data?.data.data, onOpenDailyDataGraph)
    // }, [data])

    const onExportToExcelCallBack = async (pageNumber: number) => {
        const data = await getBPRData({
            id: 1,
            name: '',
            fields: [],
            filters: currentFilter,
            paginationParameter: {
                pageNumber: pageNumber,
                recordsPerPage: 5000
            }
        })

        return data.data.data
    }

    const extras = [
        {
            field: 'checkbox',
            colId: 'checkbox',
            headerName: '',
            width: 70,
            minWidth: 50,
            checkboxSelection: true,
            headerCheckboxSelection: true,
            headerCheckboxSelectionCurrentPageOnly: true,
            resizable: false,
            suppressHeaderMenuButton: true,
            maxWidth: 50,
            pinned: 'left',
            filter: false,
        }
    ];
    
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
            sortable:false,
            suppressHeaderMenuButton:true,
            headerName:"Daily Data Graph",

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

    const rowsPerPage = useMemo(() => parseInt(RESEARCHINSIGHT_ROWS_PER_PAGE|| '50'), [])

    return {
        ref,
        agGridProps,
        ResearchInsightsData,
        ResearchInsightsColumns,
        isLoading: isUIConfigLoading || isBPRDataCountLoading || isBPRLoading,
        isUpdatedGraphDataLoading,
        horizon,
        graphState,
        blackCount,
        redCount,
        whiteCount,
        isGraphOneOpen,
        graphs,
        setGraphs,
        locationGraphData,
        selfGraphData,
        expandedGraphId,
        calenderData,
        expandedGraphAllFilterValues,
        calenderType,
        toggleGraphModal,
        setExpandedGraphId,
        updateGraphState,
        setIsGraphOneOpen,
        setHorizon,
        getColor,
        setCalenderType,
        handleOnUpdateGraph,
        setSelectedRowsDates,
        currGridPage,
        rowsPerPage,
        recordCount,
        isSavedDataLoading,
        gridState,
        tempRef,
        tempDownloadData,
        setTempDownloadData,
        tempAgGridProps,
        exportExcelRowData,
        setExportExcelRowData,
        exportExcelColumns,
        setExportExcelColumns,
        onExportToExcelCallBack,
        showDailyDataGraphModal,
        showNormChangeHistoryTable,
        dailyData,
        onApplyFilter,
        handlePageChange,
        onDeleteFilter,
        currentFilter,
        setCurrentFilter,
        historicalAvailabilityData,
        isHistoricalAvailabilityLoading,
        continuousBlack,
        continuousBlackAndRed,
        continuousWhite,
        generalFilterOptions,
        onResetCallback,
        lastRunDate,
        savePageSize,
        userPageSize
    }
}

export default useResearchInsights
