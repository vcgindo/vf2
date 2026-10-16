 import { useState,useRef } from "react";
 import {  notifyLoader, notifySuccess } from "../../../../../helpers/notify";
 import { toast } from "react-toastify";
import useBPRFilter from "../../../../../hooks/useBPRFilter";
import { useUserData } from "../../../../../context";
import { useGetChronicUnavailabilityGridView } from "../../../../Services/MTA/InsightsAndTrends";
import { useSelector } from "react-redux";
import { RootState } from "../../../../../redux/store/store";


const useGuidedInsights = ()=>{

    const {user} = useUserData()

    const themeUi = user.user.theme_ui

const [currentTab,setCurrentTab] = useState<string>('availabilitytrend');
const [currentCategory,setCurrentCategory] = useState<string>('');
const [currentView,setCurrentView] = useState<string>('chart');
const [currentGridData,setCurrentGridData] = useState([{}]);

const ref = useRef()

const {state:currentFilter,setState:setCurrentFilter,onDelete,defaultFilters} = useBPRFilter()


const {mutateAsync:getChronicUnavailabilityGrid} = useGetChronicUnavailabilityGridView() || {};
const [chroniceRowData,setChronicRowData] = useState<Array<any>>([])

const [horizon,setHorizon] = useState<number>(9)
const [ageing,setAgeing] = useState<number>(1)

const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
const GUIDEDINSIGHT_ROWS_PER_PAGE = EnvConfig['GUIDEDINSIGHT_ROWS_PER_PAGE']; 

// const ChronicUnavailabilityGridViewData=ChronicUnavailabilityGrid?.data?.data;
 const onFloatingTabChange = (tab:any) => {
        setCurrentTab(tab.value);
        setCurrentView("chart");
        setCurrentFilter(defaultFilters)
    }
     const onGoBack = () => {
        // setIsSelectCategoryOpen(true);
        setCurrentCategory('');
        setCurrentView('');
        setCurrentTab('');
    }
    const fetchAndUpdateGridData=async(filter?:any)=>{
        const body:any={
            "id": 0,
            "name": "",
            "fields": [],
            "paginationParameter": {
                "pageNumber": 1,
                "recordsPerPage": GUIDEDINSIGHT_ROWS_PER_PAGE || 100
            },
            filters:filter || currentFilter
        }
         const toastId = notifyLoader('Loading Grid Data');
         const result = await getChronicUnavailabilityGrid(body)
         setCurrentGridData(result?.data?.data != null? result?.data?.data:[]);
         setChronicRowData(result?.data?.data != null? result?.data?.data:[]);
         toast.dismiss(toastId);
         notifySuccess("Grid Details Fetched Successfully");
                    
    }

    const onViewChange = (view:string) => {
         const activeTab = currentTab;
         if(activeTab){
               setCurrentTab(currentTab);
          } 
          setCurrentView(view);
          if (view === "grid") {
            fetchAndUpdateGridData();
          }
    }

    const  onApplyFilter = async(currentFilter?:any, filter?:any)=>{

        if (currentView==="chart") {
            setCurrentFilter(currentFilter)
          }
          else{
            setCurrentFilter(currentFilter)
            fetchAndUpdateGridData(currentFilter)
          }
        // await getDataCount(filter)
        //await getDBMRowData(filter,1)
    }
   
    const onDeleteFilter = async(parentId:any, filterId:any, value:any)=>{
        const updatedFilter = onDelete(parentId,filterId,value)
       onApplyFilter(updatedFilter)
    }

    

      const getFloatingTabsList = () => {
        return([
                        {
                            id:'AvailabilityTrend',
                            label:'Availability Trend',
                            value:'availabilitytrend'
                        },
                        {
                            id:'ChronicUnavailability',
                            label:'Chronic Unavailability',
                            value:'chronicunavailability'
                        },
                        {
                            id:'AvailabilityAgeingTrend',
                            label:'Availability Ageing Trend',
                            value:'availabilityageingtrend'
                        },
                        {
                            id:'DBMNormSuggestions',
                            label:'DBM Norm Suggestions',
                            value:'dbmnormsuggestions'
                        },
                        {
                            id:'ExcessInventoryTrend',
                            label:'Excess Inventory Trend',
                            value:'excessinventorytrend'
                        },
                        // {
                        //     id:'CustomScreens',
                        //     label:'Custom Screens',
                        //     value:'customscreens'
                        // }
                    ])
      }

    return{
        onFloatingTabChange,
        onGoBack,
        onViewChange,
        currentView,
        currentTab,
        setCurrentTab,
        getFloatingTabsList,
        currentCategory,
        currentGridData,
        ref,
        chroniceRowData,
        currentFilter,
        setCurrentFilter,
        onDelete,
        onApplyFilter,
        onDeleteFilter,
        themeUi,
        horizon,
        setHorizon,
        ageing,
        setAgeing,
        
    }
}
export default useGuidedInsights;
