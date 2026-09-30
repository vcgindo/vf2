 import { useState,useRef } from "react";
 import {  notifyLoader, notifySuccess } from "../../../../../helpers/notify";
 import { toast } from "react-toastify";
import useBPRFilter from "../../../../../hooks/useBPRFilter";
import { useUserData } from "../../../../../context";
import {useGetChronicUnavailabilityLoc,useGetChronicUnavailabilitySku, useGetChronicUnavailabilityGridView} from "../../../../Services/MTA/InsightsAndTrends";
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


const {mutateAsync:getChronicUnavailabilityLoc} = useGetChronicUnavailabilityLoc() || {} ;
const {mutateAsync:getChronicUnavailabilitySku} = useGetChronicUnavailabilitySku() || {};
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

    const fetchAndUpdateChartData=async(currentFilter?:any, horison?:any, ageing?:any)=>{
       try{
        const body:any=
           {filters:currentFilter,
           }
        
         const toastId = notifyLoader('Loading Chart Data');
        //  const result = await getChronicUnavailabilityGrid(body)
        let result;
        if (currentTab === 'availabilitytrend') {
          body.horison=horison;
          toast.dismiss(toastId);
            // result = await getAvaialabilityTrend (body);
          } 
          if (currentTab === 'chronicunavailability') {
            const s1 = await getChronicUnavailabilitySku(body);
            const s2 = await getChronicUnavailabilityLoc(body);
            result = {...s1,...s2};
          }
          if (currentTab === 'availabilityageingtrend') {
            body.horison=horison;
            body.ageing=ageing;
            toast.dismiss(toastId);
            // result = await getAvaialabilityAgeing(body);
          }
         if(currentTab==='excessinventorytrend'){
            body.horison=horison;
            // const r1= await getExcessInventorySku(body);
            // const r2 = await getExcessInventoryValue(body);
            // result = {...r1, ...r2};
            toast.dismiss(toastId);
         }

          if(result){
            setCurrentGridData(result.data.data);
          setChronicRowData(result.data.data);
          toast.dismiss(toastId);
          notifySuccess("Chart Details Fetched Successfully");
          }
                
       }
       catch(err){
        console.log(err)
       }
    }

    const onViewChange = (view:string) => {
         const activeTab = currentTab;
         if(activeTab){
               setCurrentTab(currentTab);
          } 
          setCurrentView(view);
          fetchAndUpdateGridData();
    }

    const  onApplyFilter = async(currentFilter?:any, filter?:any)=>{

        if (currentView==="chart") {
            setCurrentFilter(currentFilter)
            if (currentTab !== 'dbmnormsuggestions') {
              fetchAndUpdateChartData(currentFilter, horizon, ageing)
            }
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
