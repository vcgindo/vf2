import { useEffect, useState,useMemo,useRef } from "react"
import { fulfillmentFailureMessage } from './fulfillmentFailure';
import { expediteFailureMessage } from './expediteFailure';
import { gitFailureMessage } from './gitFailure';
import { excessFailureMessage } from './excessFailure';
import { toast } from "react-toastify";
import { VFPaginationProps } from "../../../../../components/VectorFLOW/commons/VFPagination";
import { notifyError, notifyLoader, notifySuccess } from "../../../../../helpers/notify";
import { useGetDailyData } from "../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR";
import { useGetPlanningDataCount,useGetPlanningDataGraph, useGetPlanningDataGrid, useGetPlanningDataGridCount } from "../../../../Services/MTA/SupplyChainIntelligenceHub/Planning";
import { PlanningCategory, PlanningCounts, DailyDataGraph } from "../../../../types/MTA"
import {useSelector,useDispatch} from 'react-redux';
import { type RootState } from "../../../../../redux/store/store";
import {TOGGLE_GRAPH_MODAL,UPDATE_DAILY_DATA, UPDATE_PLANNING_DATA} from '../../../../../redux/actions/MTA';
import { AgGridReactProps } from 'ag-grid-react';
import useBPRFilter from "../../../../../hooks/useBPRFilter";
import { GridRef } from "../../../../../VectorFlow/types/MDM";
import { useGetUIConfigData } from "../../../../../VectorFlow/Services/MTA/Common/UIConfig";
import { UIColumnConfigName } from "../../../../../helpers/Enum";
import _ from "lodash";
import useGetLastRunData from "../../../../../hooks/useGetLastRunData"

const usePlanning = ()=>{

    const initialPlanningCounts = {
        childMonitorCount:0,
        parentMonitorCount:0,
        childMonitorCustomCount:0,
        parentExpediteCount:0,
        parentExpediteCustomCount:0,
        childExpediteCount:0,
        childExpediteCustomCount:0,
        reviewExcessInventoryCount:0,
        reviewExcessInventoryCustomCount:0,
        reviewOrderFulfillmentCount:0,
        reviewOrderFulfillmentCustomCount:0
        
    }

    const dispatch = useDispatch(); 

    const ref = useRef<GridRef>()
    const tempRef:any = useRef<GridRef>()

    const {state:currentFilter,setState:setCurrentFilter,onDelete} = useBPRFilter()
   
    const [planningCounts,setPlanningCounts] = useState<PlanningCounts>(initialPlanningCounts)

    const [isSelectCategoryOpen,setIsSelectCategoryOpen] = useState(true);

    const { date: lastRunDate } = useGetLastRunData();
    const {mutateAsync:getPlanningDataCount} = useGetPlanningDataCount();

    const {mutateAsync:getPlanningDataGraph} = useGetPlanningDataGraph();

    const {mutateAsync:getPlanningDataGrid} = useGetPlanningDataGrid();

    const {mutateAsync:getPlanningDataGridCount} = useGetPlanningDataGridCount()

    const [isOverlayVisible,setIsOverlayVisible] = useState(false);

    const [currentCategory,setCurrentCategory] = useState<string>('');

    const [tempDownloadData,setTempDownloadData] = useState<boolean>(false);

    const [currentGraphData,setCurrentGraphData] = useState();

    const [exportExcelColumns,setExportExcelColumns] = useState<Array<any>>([])

    const [exportExcelRowData,setExportExcelRowData] = useState<Array<any>>([])

    const [currentGridData,setCurrentGridData] = useState<any>();
    const [fulfillmentError,setFulfillmentError] = useState<string | null>(null);

    const [currentTab,setCurrentTab] = useState<string>('');

    const [currentView,setCurrentView] = useState<string>('chart');

    const [currentPage,setCurrentPage] = useState<number>(1);

    const [totalRows,setTotalRows] = useState<number>(0);

    const [goBack,setGoBack] = useState<boolean>(false);

    // const [currentGridState,setCurrentGridState] = useState<any>()

    const [isDataLoading,setIsDataLoading] = useState(false);

    const [globalColDef, setGlobalColDef] = useState<any>();

    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const PLANNING_ROWS_PER_PAGE = EnvConfig['PLANNING_ROWS_PER_PAGE'];  
    const rowsPerPage = parseInt(PLANNING_ROWS_PER_PAGE || '50');

    const showDailyDataGraphModal = useSelector((state:RootState) => state.mta.showDailyDataGraphModal);
    const showNormChangeHistoryTable = useSelector((state:RootState) => state.mta.showNormChangeHistoryTable);
    const dailyData = useSelector((state:RootState) => state.mta.dailyData);
    const [OrderFulfillmentuserPageSize , setOrderFulfillmentuserPageSize]  = useState<number>(PLANNING_ROWS_PER_PAGE?parseInt(PLANNING_ROWS_PER_PAGE):50) 
    const [GITFromParentuserPageSize , setGITFromParentuserPageSize]  = useState<number>(PLANNING_ROWS_PER_PAGE?parseInt(PLANNING_ROWS_PER_PAGE):50) 
    const [GITToChildLocationWiseuserPageSize , setGITToChildLocationWiseuserPageSize]  = useState<number>(PLANNING_ROWS_PER_PAGE?parseInt(PLANNING_ROWS_PER_PAGE):50) 
    const [GITToChildTransporterWiseuserPageSize , setGITToChildTransporterWiseuserPageSize]  = useState<number>(PLANNING_ROWS_PER_PAGE?parseInt(PLANNING_ROWS_PER_PAGE):50) 
    const [ExpediteFromParentcreateAvailabilityAtParentuserPageSize , setExpediteFromParentcreateAvailabilityAtParentuserPageSize]  = useState<number>(PLANNING_ROWS_PER_PAGE?parseInt(PLANNING_ROWS_PER_PAGE):50) 
    const [ExpediteFromParentexpediteDispatchesuserPageSize , setExpediteFromParentexpediteDispatchesuserPageSize]  = useState<number>(PLANNING_ROWS_PER_PAGE?parseInt(PLANNING_ROWS_PER_PAGE):50) 
    const [ExpediteToChilduserPageSize , setExpediteToChilduserPageSize]  = useState<number>(PLANNING_ROWS_PER_PAGE?parseInt(PLANNING_ROWS_PER_PAGE):50) 
    const [ExcessInventoryuserPageSize , setExcessInventoryuserPageSize]  = useState<number>(PLANNING_ROWS_PER_PAGE?parseInt(PLANNING_ROWS_PER_PAGE):50) 
 
    const {mutateAsync:getDailyData} = useGetDailyData();

    const getUserPageSizeForCategory = (category: string , currentTab:string) => {
        
        switch(category){
            case 'GITFromParent': return GITFromParentuserPageSize;
            case 'GITToChild': {
                if(currentTab === 'transporterWise') return GITToChildTransporterWiseuserPageSize;
                else    return GITToChildLocationWiseuserPageSize;
            }
            case 'ExpediteFromParent': {
                if(currentTab === 'expediteDispatches') return ExpediteFromParentexpediteDispatchesuserPageSize
                else    return ExpediteFromParentcreateAvailabilityAtParentuserPageSize;
            }
            case 'ExpediteToChild': return ExpediteToChilduserPageSize;
            case 'ExcessInventory': return ExcessInventoryuserPageSize;
            case 'OrderFulfillment': return OrderFulfillmentuserPageSize;
            default: return rowsPerPage;
        }
    };

    const updateUserPageSizeForCategory = (category: string, pageSize: number , currentTab:string) => {
        
        switch(category){
            case 'GITFromParent':
                setGITFromParentuserPageSize(pageSize);
                break;
            case 'GITToChild':
                if(currentTab === 'transporterWise')  setGITToChildTransporterWiseuserPageSize(pageSize);
                else  setGITToChildLocationWiseuserPageSize(pageSize);
                break;
            case 'ExpediteFromParent':
                if(currentTab === 'expediteDispatches')  setExpediteFromParentexpediteDispatchesuserPageSize(pageSize)
                else    setExpediteFromParentcreateAvailabilityAtParentuserPageSize(pageSize);
                break;
            case 'ExpediteToChild':
                setExpediteToChilduserPageSize(pageSize);
                break;
            case 'ExcessInventory':
                setExcessInventoryuserPageSize(pageSize);
                break;
            case 'OrderFulfillment':
                setOrderFulfillmentuserPageSize(pageSize);
                break;
        }
    };
    const savePageSize = async( pageSize:number)=>{
        updateUserPageSizeForCategory(currentCategory, pageSize,currentTab);
        await fetchAndUpdateGridData(currentPage,false,currentFilter, currentTab,pageSize)
    }
    let currentUserPageSize = getUserPageSizeForCategory(currentCategory,currentTab);

    const paginationProps:VFPaginationProps = {
        selectedRows:0,
        totalRows:totalRows,
        rowsPerPage: currentUserPageSize,
        currentPage:currentPage,
        handleChangePage:(currPage:number) => {
            fetchAndUpdateGridData(currPage,true,currentFilter, currentTab,currentUserPageSize);
            setCurrentPage(currPage)
        },
        customPageSizeEnabled:true,
        userPageSize:currentUserPageSize,
        savePageSize:savePageSize
        
    }

    const tempAgGridProps: AgGridReactProps = {
        onRowDataUpdated: (event) => {
            if (tempDownloadData) {
                const allColumns = ref.current?.api.getAllDisplayedColumns();
                const columnKeys = allColumns?.map(c => c.getColId())
                    .filter(colId => !['t','dailydatagraph'].includes(colId)); // Replace with actual column IDs to exclude
                
                event?.api.exportDataAsExcel({
                    fileName: `${currentCategory}${currentTab}`,
                    columnKeys: columnKeys
                });
                
                setTempDownloadData(false);
            }
        }
    };
    useEffect(()=>{
        fetchPlanningDataCount();
    },[goBack])

    const {mutateAsync: getUIConfig}  = useGetUIConfigData();

    const [gridColDefs,setGridColDefs] = useState<any>([]);

    const getAllUIConfig = async(category:string,tab:string) => {

        
        let coldefs:any = [];
        try {
            switch (category) {
            case 'GITFromParent': {
                coldefs = await getUIConfig(UIColumnConfigName.GIT_From_Parent);
                break;
            }
            case 'GITToChild': {
                switch (tab) {
                case 'locationWise':
                    coldefs = await getUIConfig(UIColumnConfigName.GIT_To_Child_LW);
                    break;
                case 'transporterWise':
                    coldefs = await getUIConfig(UIColumnConfigName.GIT_To_Child_TW);
                    break;
                case 'custom':
                    coldefs = await getUIConfig(UIColumnConfigName.GIT_To_Child_CS);
                    break;
                default:
                    coldefs = await getUIConfig(UIColumnConfigName.GIT_To_Child_LW);
                    break;
                }
                break;
            }
            case 'ExpediteFromParent': {
                switch (tab) {
                case 'expediteDispatches':
                    coldefs = await getUIConfig(UIColumnConfigName.Expedite_From_Parent_ED);
                    break;
                case 'createAvailabilityAtParent':
                    coldefs = await getUIConfig(UIColumnConfigName.Expedite_From_Parent_CAAP);
                    break;
                default:
                    coldefs = await getUIConfig(UIColumnConfigName.Expedite_From_Parent_ED);
                    break;
                }
                break;
            }
            case 'ExpediteToChild': {
                switch (tab) {
                case 'expediteDispatches':
                    coldefs = await getUIConfig(UIColumnConfigName.Expedite_To_Child_ED);
                    break;
                case 'custom':
                    coldefs = await getUIConfig(UIColumnConfigName.Expedite_To_Child_CS);
                    break;
                default:
                    coldefs = await getUIConfig(UIColumnConfigName.Expedite_To_Child_ED);
                    break;
                }
                break;
            }
            case 'ExcessInventory': {
                switch (tab) {
                case 'excessInventory':
                    coldefs = await getUIConfig(UIColumnConfigName.Excess_Inventory_Review);
                    break;
                case 'custom':
                    coldefs = await getUIConfig(UIColumnConfigName.Excess_Inventory_Review_CS);
                    break;
                default:
                    coldefs = await getUIConfig(UIColumnConfigName.Excess_Inventory_Review);
                    break;
                }
                break;
            }
            case 'OrderFulfillment': {
                switch (tab) {
                case 'orderFulfillment':
                    coldefs = await getUIConfig(UIColumnConfigName.Order_Fulfillment_Review);
                    break;
                case 'custom':
                    coldefs = await getUIConfig(UIColumnConfigName.Order_Fulfillment_Review_CS);
                    break;
                default:
                    coldefs = await getUIConfig(UIColumnConfigName.Order_Fulfillment_Review);
                    break;
                }
                break;
            }
            }
        } catch (error: any) {
            console.log(error);
            notifyError(error);
        }
        setGridColDefs(coldefs?.data?.data);
    }



    useEffect(()=>{
        dispatch(UPDATE_PLANNING_DATA({
            currentTab:currentTab,
            currentCategory:currentCategory,
            currentView:currentView
        }))  
        if(currentView==='grid'){
            getAllUIConfig(currentCategory,currentTab);
        }

    },[currentCategory,currentTab,currentView])

   
    const getFloatingTabsList = (view:string) => {
        switch(currentCategory){
            case 'GITFromParent':{
                return [];
            }
            case 'GITToChild':{
                if(view === 'chart'){
                     return([
                        {
                            id:'locationWise',
                            label:'Location-Wise',
                            value:'locationWise'
                        },
                        {
                            id:'transporterWise',
                            label:'Transporter-Wise',
                            value:'transporterWise'
                        }
                    ])
                }
                else{
                    return ([
                        {
                            id:'locationWise',
                            label:'Location-Wise',
                            value:'locationWise'
                        },
                        {
                            id:'transporterWise',
                            label:'Transporter-Wise',
                            value:'transporterWise'
                        }
                        ,
                        {
                            id:'custom',
                            label:'Custom Screens',
                            value:'custom'
                        }
                    ])
                }
                
            }
        case 'ExpediteFromParent':{
            if(view === 'chart'){
                return([
                    {
                        id:'expediteDispatches',
                        label:'Expedite Dispatches',
                        value:'expediteDispatches'
                    },
                    {
                        id:'createAvailabilityAtParent',
                        label:'Create Availability At Parent',
                        value:'createAvailabilityAtParent'
                    },
                    // {
                    //     id:'custom',
                    //     label:'Custom Screens',
                    //     value:'custom'
                    // }
                ])
            }
            else{
                return ([
                    {
                        id:'expediteDispatches',
                        label:'Expedite Dispatches',
                        value:'expediteDispatches'
                    },
                    {
                        id:'createAvailabilityAtParent',
                        label:'Create Availability At Parent',
                        value:'createAvailabilityAtParent'
                    },
                ])
            }
          
        }
        case 'ExpediteToChild':{
            if(view === 'chart'){
                return([])
            }
            else{
                return ([
                    {
                        id:'expediteDispatches',
                        label:'Expedite Dispatches',
                        value:'expediteDispatches'
                    },
                    {
                        id:'custom',
                        label:'Custom Screens',
                        value:'custom'
                    }
                    // {
                    //     id:'createAvailabilityAtParent',
                    //     label:'Create Availability At Parent',
                    //     value:'createAvailabilityAtParent'
                    // },
                ])
            }
          
        }
        case 'ExcessInventory':{
            if(view === 'chart'){
                return([
                    {
                        id:'excessInventoryLocation',
                        label:'Excess Inventory Location-wise',
                        value:'excessInventoryLocation'
                    },
                    {
                        id:'excessInventoryProduct',
                        label:'Excess Inventory Product-wise',
                        value:'excessInventoryProduct'
                    },
                   
                ])
            }
            else{
                return [
                    {
                        id:'excessInventory',
                        label:'Excess Inventory',
                        value:'excessInventory'
                    },
                    {
                        id:'custom',
                        label:'Custom Screens',
                        value:'custom'
                    }
                ]
            }
          
        }
        case 'OrderFulfillment':{
            if(view === 'chart'){
                return([
                    {
                        id:'orderFulfillmentLocation',
                        label:'Order Fulfillment Location-wise',
                        value:'orderFulfillmentLocation'
                    },
                    {
                        id:'orderFulfillmentProduct',
                        label:'Order Fulfillment Product-wise',
                        value:'orderFulfillmentProduct'
                    }
                ])
            }
            else{
                return [
                    {
                        id:'orderFulfillment',
                        label:'Order Fulfillment',
                        value:'orderFulfillment'
                    },
                    {
                        id:'custom',
                        label:'Custom Screens',
                        value:'custom'
                    }
                ]
            }
          
        }
        default:
            return([])
        }
    }
    const [initialPlanningCount, setInitialPlanningCount] = useState<any>();
    const fetchPlanningDataCount = async (filter?:any) => {
        setIsOverlayVisible(true);
        try {
            const result = await getPlanningDataCount({...filter});
            const data = result.data.data;
            const tempPlanningCount = {...initialPlanningCounts};
            data?.forEach((planningCategoryObj:PlanningCategory) => {
                if(planningCategoryObj.category === 'git/wip'){
                    if(planningCategoryObj.parentCount) tempPlanningCount.parentMonitorCount = planningCategoryObj.parentCount;
                    if(planningCategoryObj.childCount) tempPlanningCount.childMonitorCount = planningCategoryObj.childCount;
                    if(planningCategoryObj.custom) tempPlanningCount.childMonitorCustomCount = planningCategoryObj.custom;
                }
                if(planningCategoryObj.category === 'expedite'){
                    if(planningCategoryObj.parentCount) tempPlanningCount.parentExpediteCount = planningCategoryObj.parentCount;
                    if(planningCategoryObj.childCount) tempPlanningCount.childExpediteCount = planningCategoryObj.childCount;
                    if(planningCategoryObj.custom) tempPlanningCount.childExpediteCustomCount = planningCategoryObj.custom;
                }
                if(planningCategoryObj.category === 'excessInventory'){
                    if(planningCategoryObj.reviewCount) tempPlanningCount.reviewExcessInventoryCount = planningCategoryObj.reviewCount ;
                    if(planningCategoryObj.custom) tempPlanningCount.reviewExcessInventoryCustomCount = planningCategoryObj.custom;
                }
                if(planningCategoryObj.category === 'orderFulfillment'){
                    if(planningCategoryObj.reviewCount) tempPlanningCount.reviewOrderFulfillmentCount = planningCategoryObj.reviewCount;
                    if(planningCategoryObj.custom) tempPlanningCount.reviewOrderFulfillmentCustomCount = planningCategoryObj.custom;
                }
            });
            setInitialPlanningCount(_.cloneDeep(tempPlanningCount));
            setPlanningCounts(tempPlanningCount);
            setFulfillmentError(null);
        } catch (error) {
            console.error(error);
            setFulfillmentError(fulfillmentFailureMessage(error));
            notifyError('Planning counts could not be loaded');
        } finally {
            setIsOverlayVisible(false);
        }
    }
    
   


    const onExportToExcelCallBack = async(pageNumber:number)=>{
        const data =  await getPlanningDataGrid({
            category:currentPageData.category,
            type:currentPageData.type,
            filters:currentFilter,
            paginationParameter:{
                pageNumber:pageNumber,
                recordsPerPage:5000
            }
        })

        if(currentPageData.category==='git' && currentPageData.type==='child'){
            if(currentTab==='transporterWise'){
                return data.data.data.transporterWise.data
            }
            return data.data.data.locationWise.data
        }
        if(currentPageData.category==='expedite' && currentPageData.type==='child'){
            if(currentTab==='expediteDispatches'){
                return data.data.data.data.expediteDispatches
            }
            return data.data.data.data.createAvailabilityAtParent
        }
        if(currentPageData.category==='expedite' && currentPageData.type==='parent'){
            if(currentTab==='expediteDispatches'){
                return data.data.data.data.expediteDispatches
            }
            return data.data.data.data.createAvailabilityAtParent
        }
        console.log(data.data.data.data);
        return data.data.data.data
    }

    const handlePlanningQuadrantClick = async (category:string) => {
        try {
            switch(category){
                case 'GITFromParent':{
                    const toastId = notifyLoader('Loading Grid Data');
                    const body = {
                        category:'git',
                        type:'parent',
                        filters:currentFilter,
                        paginationParameter:{
                            pageNumber:1,
                            recordsPerPage:GITFromParentuserPageSize
                        }
                    }
                    const count = await getPlanningDataGridCount(body)
                    setTotalRows(count.data.data[0].locationwise)
                    setPlanningCounts({...planningCounts,parentMonitorCount:count.data.data[0].locationwise})

                    const result = await getPlanningDataGrid(body);
                    setCurrentView('grid');
                    setCurrentCategory(category);
                    setCurrentGridData(result.data.data);
                    setIsSelectCategoryOpen(false);
                    toast.dismiss(toastId);
                    if(count.data.data[0].locationwise!==0)notifySuccess("Grid Data Fetched Successfully");
                    break;
                }
             
                case 'GITToChild':{
                    const toastId = notifyLoader('Loading Graphs');
                    setCurrentCategory('GITToChild');
                    setCurrentView('chart');
                    const body = {
                        category:'git',
                        type:'child',
                        filters:[]
                    }
                    const result = await getPlanningDataGraph(body);
                    if(!result.data.data.data)throw new Error("Data Not Available") 
                    setIsSelectCategoryOpen(false);
                    setCurrentGraphData(result.data.data.data)
                    setCurrentTab('locationWise');
                    toast.dismiss(toastId);
                    notifySuccess("Graph Details Fetched Successfully");
                    break;
                }
                case 'ExpediteFromParent':{
                    const toastId = notifyLoader('Loading Graphs');
                    setCurrentCategory('ExpediteFromParent');
                    setCurrentView('chart');
                    const body = {
                        category:'expedite',
                        type:'parent',
                        filters:[]
                    }
                    const result = await getPlanningDataGraph(body);
                    setIsSelectCategoryOpen(false);
                    setCurrentGraphData(result.data.data.data);
                    setCurrentTab('expediteDispatches');
                    toast.dismiss(toastId);
                    notifySuccess("Graph Details Fetched Successfully");
                    break;
                }
                case 'ExpediteToChild':{
                    const toastId = notifyLoader('Loading Graphs');
                    setCurrentCategory('ExpediteToChild');
                    setCurrentView('chart');
                    const body = {
                        category:'expedite',
                        type:'child',
                        filters:[]
                    }
                    const result = await getPlanningDataGraph(body);
                    setIsSelectCategoryOpen(false);
                    setCurrentGraphData(result.data.data.data);
                    setCurrentTab('expediteDispatches');
                    toast.dismiss(toastId);
                    notifySuccess("Graph Details Fetched Successfully");
                    break;
                }
                case 'ExcessInventory':{
                    const toastId = notifyLoader('Loading Graphs');
                    setCurrentCategory('ExcessInventory');
                    setCurrentView('chart');
                    const body = {
                        category:'excessInventory',
                        type:'review',
                        filters:[]
                    }
                    const result = await getPlanningDataGraph(body);
                    setIsSelectCategoryOpen(false);
                    setCurrentGraphData(result.data.data.data)
                    setCurrentTab('excessInventoryLocation');
                    toast.dismiss(toastId);
                    notifySuccess("Graph Details Fetched Successfully");
                    break;
                }
                case 'OrderFulfillment':{
                    const toastId = notifyLoader('Loading Graphs');
                    setCurrentCategory('OrderFulfillment');
                    setCurrentView('chart');
                    const body = {
                        category:'orderFulfillment',
                        type:'review',
                        filters:[]
                    }
                    const result = await getPlanningDataGraph(body);
                    setIsSelectCategoryOpen(false);
                    setCurrentGraphData(result.data.data.data);
                    setCurrentTab('orderFulfillmentLocation');
                    toast.dismiss(toastId);
                    notifySuccess("Graph Details Fetched Successfully");
                    break;
                }
                    
                default:
                    return;
                    
            }
            
        } catch (error:any) {
            toast.dismiss();
            notifyError(error.message)
        }

    }

    // const getAndApplyGridState = async()=>{
    //     try{
    //         const result  = await getGridState(`${currentCategory}${currentTab}`)
    //         const tempState = JSON.parse(result.data.data)
    //         // setCurrentGridState(tempState)
            
    //     }catch(error:any){
    //         console.log(error)
    //         notifyError(error)
    //     }
    // }


    const fetchAndUpdateGridData = async (currentPage:number,fromPagination:boolean,filter?:any,tab?:string  , pageSize?:number) => {
        try {            
            setIsDataLoading(true);
            // await getAndApplyGridState()
            switch(currentCategory){
                case 'GITFromParent':{
                    let totalTempCount
                    const toastId = notifyLoader('Loading Grid Data');
                    const body = {
                        category:'git',
                        type:'parent',
                        filters:filter || currentFilter,
                        paginationParameter:{
                            pageNumber:currentPage,
                            recordsPerPage:pageSize || currentUserPageSize || rowsPerPage
                        }
                    }
                    if(!fromPagination){
                        const count = await getPlanningDataGridCount(body)
                        setTotalRows(count.data.data[0].locationwise)
                        totalTempCount = count.data.data[0].locationwise
                        setPlanningCounts({...planningCounts,parentMonitorCount:count.data.data[0].locationwise})
                    }
                    const result = await getPlanningDataGrid(body);
                    setCurrentGridData(result.data.data);
                    if(fromPagination){
                        setTotalRows(planningCounts.parentMonitorCount)
                        totalTempCount = planningCounts.parentMonitorCount
                    }
                    toast.dismiss(toastId);
                    if(totalTempCount !==0)notifySuccess("Grid Details Fetched Successfully");
                    break;
                }
                case 'GITToChild':{
                    let totalTempCount
                    const toastId = notifyLoader('Loading Grid Data');
                    const body = {
                        category:'git',
                        type:'child',
                        filters:filter || currentFilter,
                        paginationParameter:{
                            pageNumber:currentPage,
                            recordsPerPage:pageSize || currentUserPageSize || rowsPerPage
                        }
                    }
                    if(!fromPagination){
                        const count = await getPlanningDataGridCount(body)
                        const {locationwise,transporterwise} = count.data.data[0]
                        const tempTab =tab?tab:currentTab
                        if(tempTab==="locationWise"){
                            setPlanningCounts({...planningCounts,childMonitorCount:locationwise})
                            setTotalRows(locationwise)
                            totalTempCount = locationwise
                        }
                        else {
                            setPlanningCounts({...planningCounts,childMonitorCount:transporterwise})
                            setTotalRows(transporterwise)
                            totalTempCount = transporterwise
                        }
                    }
                    const result = await getPlanningDataGrid(body);
                    setCurrentGridData(result.data.data);
                    if(fromPagination){
                        setTotalRows(planningCounts.childMonitorCount)
                        totalTempCount = planningCounts.childMonitorCount
                    }
                    toast.dismiss(toastId);
                    if(totalTempCount !==0)notifySuccess("Grid Details Fetched Successfully");
                    break;
                }
                case 'ExpediteFromParent':{
                    let totalTempCount
                    const toastId = notifyLoader('Loading Grid Data');
                    const body = {
                        category:'expedite',
                        type:'parent',
                        filters:filter,
                        paginationParameter:{
                            pageNumber:currentPage,
                            recordsPerPage:pageSize || currentUserPageSize || rowsPerPage
                        }
                    }
                    if(!fromPagination){
                        const count = await getPlanningDataGridCount(body)
                        const {createAvailabilityAtParent,expediteDispatches} = count.data.data
                        const tempTab =tab?tab:currentTab
                        if(tempTab==="createAvailabilityAtParent"){
                            setPlanningCounts({...planningCounts,parentExpediteCount:createAvailabilityAtParent})
                            setTotalRows(createAvailabilityAtParent)
                            totalTempCount = createAvailabilityAtParent
                        }
                        else {
                            setPlanningCounts({...planningCounts,parentExpediteCount:expediteDispatches})
                            setTotalRows(expediteDispatches)
                            totalTempCount = expediteDispatches
                        }
                    }
                    
                    const result = await getPlanningDataGrid(body);
                    const uiConfig = result.data.data.uiConfig;
                    const {createAvailabilityAtParent,createAvailabilityAtParentwip,createAvailabilityAtParenttransit,expediteDispatches,expediteDispatcheswip,expediteDispatchestransit} = result.data.data.data;
                    // const customData = {
                    //     "createAvailabilityAtParent": { "data": createAvailabilityAtParent, transitData: createAvailabilityAtParentwip, stockData: createAvailabilityAtParenttransit, "uiConfig": uiConfig },
                    //     "expediteDispatches": { "data": expediteDispatches, transitData: expediteDispatcheswip, stockData: expediteDispatchestransit, "uiConfig": uiConfig }
                    // };
                    const customData = {
                        "createAvailabilityAtParent": { "data": createAvailabilityAtParent, "uiConfig": uiConfig },
                        "expediteDispatches": { "data": expediteDispatches,stockData: expediteDispatchestransit, "uiConfig": uiConfig },
                    };
                    setCurrentGridData(customData);
                    if(fromPagination){
                        setTotalRows(planningCounts.parentExpediteCount)
                        totalTempCount = planningCounts.parentExpediteCount
                    }
                    toast.dismiss(toastId);
                    if(totalTempCount !==0)notifySuccess("Grid Details Fetched Successfully");
                    break;
                }
                case 'ExpediteToChild':{
                    let totalTempCount
                    const toastId = notifyLoader('Loading Grid Data');
                    const body = {
                        category:'expedite',
                        type:'child',
                        filters:filter,
                        paginationParameter:{
                            pageNumber:currentPage,
                            recordsPerPage:pageSize || currentUserPageSize || rowsPerPage
                        }
                    }
                    if(!fromPagination){
                        body.paginationParameter.pageNumber  = 1
                        const count = await getPlanningDataGridCount(body)
                        const {createAvailabilityAtParent,expediteDispatches} = count.data.data
                        const tempTab =tab?tab:currentTab
                        if(tempTab==="createAvailabilityAtParent"){
                            setPlanningCounts({...planningCounts,childExpediteCount:createAvailabilityAtParent})
                            setTotalRows(createAvailabilityAtParent)
                            totalTempCount = createAvailabilityAtParent
                        }
                        else {
                            setPlanningCounts({...planningCounts,childExpediteCount:expediteDispatches})
                            setTotalRows(expediteDispatches)
                            totalTempCount = expediteDispatches
                        }
                        setCurrentPage(1)
                    }
                    const result = await getPlanningDataGrid(body);
                    const {createAvailabilityAtParent,expediteDispatches} = result.data.data.data;
                    const uiConfig = result.data.data.uiConfig;
                    const customData = {"createAvailabilityAtParent":{"data":createAvailabilityAtParent,"uiConfig":uiConfig},"expediteDispatches":{"data":expediteDispatches,"uiConfig":uiConfig}};
                    setCurrentGridData(customData);
                    if(fromPagination){
                        setTotalRows(planningCounts.childExpediteCount)
                        totalTempCount = planningCounts.childExpediteCount
                    }
                    toast.dismiss(toastId);
                    if(totalTempCount !==0)notifySuccess("Grid Details Fetched Successfully");
                    break;
                }
                case 'ExcessInventory':{
                    let totalTempCount
                    const toastId = notifyLoader('Loading Grid Data');
                    const body = {
                        category:'excessInventory',
                        type:'review',
                        filters:filter,
                        paginationParameter:{
                            pageNumber:currentPage,
                            recordsPerPage:pageSize || currentUserPageSize || rowsPerPage
                        }
                    }
                    if(!fromPagination){
                        body.paginationParameter.pageNumber  = 1
                        const count = await getPlanningDataGridCount(body)
                        setTotalRows(count.data.data)
                        setCurrentPage(1)
                        setPlanningCounts({...planningCounts,reviewExcessInventoryCount:count.data.data})
                        totalTempCount = count.data.data
                        // setPlanningCounts({...planningCounts,parentMonitorCount:count.data.data})
                    }
                    const result = await getPlanningDataGrid(body);
                    if(fromPagination){
                        setTotalRows(planningCounts.reviewExcessInventoryCount)
                        totalTempCount = planningCounts.reviewExcessInventoryCount
                    }
                    setCurrentGridData(result.data.data);
                    toast.dismiss(toastId);
                    if(totalTempCount !==0)notifySuccess("Grid Details Fetched Successfully");
                    break;
                }
                case 'OrderFulfillment':{
                    let totalTempCount
                    const toastId = notifyLoader('Loading Grid Data');
                    const body = {
                        category:'orderFulfillment',
                        type:'review',
                        filters:filter,
                        paginationParameter:{
                            pageNumber:currentPage,
                            recordsPerPage:pageSize || currentUserPageSize || rowsPerPage
                        }
                    }
                    if(!fromPagination){
                        body.paginationParameter.pageNumber  = 1
                        const count = await getPlanningDataGridCount(body)
                        setTotalRows(count.data.data)
                        totalTempCount = count.data.data
                        setCurrentPage(1)
                        setPlanningCounts({...planningCounts,reviewOrderFulfillmentCount:count.data.data})
                        // setPlanningCounts({...planningCounts,parentMonitorCount:count.data.data})
                    }
                    const result = await getPlanningDataGrid(body);
                    if(fromPagination){
                        totalTempCount = planningCounts.reviewOrderFulfillmentCount
                        setTotalRows(planningCounts.reviewOrderFulfillmentCount)
                    }
                    setCurrentGridData(result.data.data);
                    toast.dismiss(toastId);
                    if(totalTempCount !==0)notifySuccess("Grid Details Fetched Successfully");
                    break;
                }
            }
            setFulfillmentError(null);
            setIsDataLoading(false);
            
        } catch (error) {
            toast.dismiss();
            console.error(error)
            if(currentCategory==='OrderFulfillment') {
                setFulfillmentError(fulfillmentFailureMessage(error) || 'Fulfilment could not be loaded. Retry or change the filter; the previous grid is not a result for this request.');
            }
            if(currentCategory==='ExpediteFromParent' || currentCategory==='ExpediteToChild') {
                // Existing error gate hides stale grids and their pagination.
                setFulfillmentError(expediteFailureMessage(error));
            }
            if(currentCategory==='GITFromParent' || currentCategory==='GITToChild') {
                setFulfillmentError(gitFailureMessage(error));
            }
            if(currentCategory==='ExcessInventory') {
                setFulfillmentError(excessFailureMessage(error));
            }
            notifyError('Something Went Wrong')
            setIsDataLoading(false);
        }
    }

    const onApplyFilter = async(filter:any)=>{
        if(isSelectCategoryOpen){
            await fetchPlanningDataCount(filter)
            return 
        }
        // await fetchPlanningDataCount(filter)
        setCurrentFilter(filter)
        setCurrentPage(1)
        fetchAndUpdateGridData(1,false,filter)
    }

    const onDeleteFilter = async(parentId:any, filterId:any, value:any)=>{
        const updatedFilter = onDelete(parentId,filterId,value)
        await onApplyFilter(updatedFilter)
    }


    const onFloatingTabChange = (tab:any) => {
        setCurrentTab(tab.value);
        currentUserPageSize = getUserPageSizeForCategory(currentCategory,tab.value);
        if(currentCategory==='GITToChild' && currentView==='grid'){
            setCurrentPage(1)
            // Custom uses GetPlanningDataCustom in its own mounted component;
            // the unrelated failed combined normal grid must not gate it.
            if(tab.value==='custom') setFulfillmentError(null);
            else fetchAndUpdateGridData(1,false,currentFilter,tab.value , currentUserPageSize)
        }
        if(currentCategory==='ExpediteFromParent' && currentView==='grid'){
            setCurrentPage(1)
            fetchAndUpdateGridData(1,false,currentFilter,tab.value , currentUserPageSize)
        }
        if(currentCategory==='ExpediteToChild' && currentView==='grid'){
            setCurrentPage(1)
            if(tab.value==='custom') setFulfillmentError(null);
            else fetchAndUpdateGridData(1,false,currentFilter,tab.value , currentUserPageSize)
        }
        if(currentCategory==='ExcessInventory' && currentView==='grid'){
            setCurrentPage(1)
            fetchAndUpdateGridData(1,false,currentFilter,tab.value , currentUserPageSize)
        }
        if(currentCategory==='OrderFulfillment' && currentView==='grid'){
            setCurrentPage(1)
            fetchAndUpdateGridData(1,false,currentFilter,tab.value , currentUserPageSize)
        }
    }


    const onGoBack = () => {
        setFulfillmentError(null);
        setCurrentFilter({
            supplyChainFilter:{
                id:'1',
                label:'SupplyChain',
                filters:[]
            },
            locationFilter:{
                id:'2',
                label:'Location',
                filters:[]
            },
            productFilter:{
                id:'3',
                label:'Product',
                filters:[]
            },
            availabilityFilter:{
                id:'4',
                label:'Availability',
                filters:[]
            },
            coverageFilter:{
                id:'5',
                label:'Coverage',
                filters:[]
            },
            colorFilter:{
                id:'6',
                label:'Color',
                filters:[]
            },
            generalFilter:{
                id:'7',
                label:'General',
                filters:[]
            },
            customAttributeFilter:{
                id:'8',
                label:'Attribute',
                filters:[]
            },
            horizonFilter: {
                id:'9',
                label: 'Horizon',
                filters: [],
            }
        })
        setIsSelectCategoryOpen(true);
        setCurrentCategory('');
        setCurrentView('');
        setCurrentTab('');
        setCurrentPage(1);
        setGoBack(true);
        toast.dismiss();
    }

    const onViewChange = async (view: string) => {
        // P4a: the failed combined child GRID does not invalidate its separately
        // loaded canonical chart. Returning to grid will fetch/fail explicitly.
        if((currentCategory==='GITToChild' || currentCategory==='ExpediteToChild') && view==='chart') setFulfillmentError(null);
        const tabsList = getFloatingTabsList(view);
        if (currentTab === '') {
            if (tabsList.length > 0) {
                setCurrentTab(tabsList[0].value);
            }
            if (view === 'grid') await fetchAndUpdateGridData(currentPage, false, currentFilter);
            setCurrentView(view);
        } else {
            const activeTab = tabsList.find(tab => tab.value === currentTab);
            if (!activeTab && tabsList.length > 0) {
                setCurrentTab(tabsList[0].value);
            }
            if (view === 'grid') await fetchAndUpdateGridData(currentPage, false, currentFilter);
            setCurrentView(view);
        }
    }

    const onOpenDailyDataGraph = async (params:any) => {
        const payload:any = {
            SKUCode:params.data['sc'].toString(),
            WHCode:params.data['wc']
        }
        const result = await getDailyData(payload)
        const data = result.data.data[0];
        const dailyData:DailyDataGraph = {
            rowData:params.data,
            chartData:data['StockData'] ? data['StockData'] : [],
            normChangeData:data['NormChangeHistoryData'] ? data['NormChangeHistoryData'] : [],
            masterData:data['MasterData'][0],
            suggestionData:data['SuggestionHistoryData'] ? data['SuggestionHistoryData'] : [],
            monitoringData:data['MonitoringData']
        }

        dispatch(UPDATE_DAILY_DATA(dailyData));
        dispatch(TOGGLE_GRAPH_MODAL(true));
    }



    const currentPageData = useMemo(()=>{
        switch(currentCategory){
            case "GITFromParent":
                return {
                    category:'git',
                    type:'parent'
                }
            case "GITToChild":
                return {
                    category:'git',
                    type:'child'
                }
            case "ExpediteFromParent":
                return {
                    category:'expedite',
                    type:'parent'
                }
            case "ExpediteToChild":
                return {
                    category:'expedite',
                    type:'child'
                }
            case "ExcessInventory":
                return {
                    category:'excessInventory',
                    type:'review'
                }
            case "OrderFulfillment":
                return {
                    category:'orderFulfillment',
                    type:'review'
                }
            default:
                return  {
                    category:'orderFulfillment',
                    type:'review'
                }
        }
    },[currentCategory])

    // const currentColDefs = useMemo(()=>{
    //     if(currentGridData){
    //         let currUiConfig = []
    //         if(currentCategory==="GITToChild"){
    //             if(currentTab==="locationWise") currUiConfig=currentGridData['locationWise'].uiConfig
    //             else currUiConfig=currentGridData['transporterWise'].uiConfig
    //         }
    //         else if(currentCategory==="ExpediteFromParent"){
    //             if(currentTab==="createAvailabilityAtParent") currUiConfig=currentGridData['createAvailabilityAtParent'].uiConfig
    //             else currUiConfig=currentGridData['expediteDispatches'].uiConfig
    //         }
    //         else if(currentCategory==="ExpediteToChild"){
    //             if(currentTab==="createAvailabilityAtParent") currUiConfig=currentGridData['createAvailabilityAtParent'].uiConfig
    //             else currUiConfig=currentGridData['expediteDispatches'].uiConfig
    //         }
    //         else currUiConfig = currentGridData.uiConfig
    //         let colDefs = [];
    //     colDefs = currUiConfig.map((column:{header:string,colCode:string})=>{
    //         if(['plp','pip'].includes(column.colCode)){
    //             return {
    //                 field:column['colCode'],
    //                 colId:column['colCode'],
    //                 headerName:column['header'],
    //                 cellRenderer:'colorCellRenderer',
    //             }
    //         }
    //         return {
    //             field:column['colCode'],
    //             colId:column['colCode'],
    //             headerName:column['header']
    //         }
    //     })
    //     return [...colDefs]
    //     }
    //     return []
    // },[currentGridData])

    // console.log(currentPageData,currentTab)

 
    return {
        fulfillmentError,
        planningCounts,
        isSelectCategoryOpen,
        isOverlayVisible,
        currentCategory,
        currentGraphData,
        currentTab,
        currentView,
        handlePlanningQuadrantClick,
        onFloatingTabChange,
        onGoBack,
        onViewChange,
        setCurrentTab,
        getFloatingTabsList,
        currentGridData,
        paginationProps,
        showDailyDataGraphModal,
        showNormChangeHistoryTable,
        dailyData,
        exportExcelColumns,
        setExportExcelColumns,
        onOpenDailyDataGraph,
        tempDownloadData,
        setTempDownloadData,
        tempAgGridProps,
        exportExcelRowData,
        setExportExcelRowData,
        onExportToExcelCallBack,
        ref,
        tempRef,
        currentFilter,
        setCurrentFilter,
        onDelete,
        onApplyFilter,
        onDeleteFilter,
        isDataLoading,
        gridColDefs,
        initialPlanningCount,
        globalColDef,
        setGlobalColDef,
        lastRunDate,
    }



}

export default usePlanning
 



