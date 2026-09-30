import {useEffect,useMemo} from 'react'
import { fallbackData } from '../../../../../mock-data/MCGrid'
import { useGetGridHealth } from "../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/MCGrid"


const useMCGrid = ()=>{

    const {mutateAsync:getGridHealth,isLoading,data} = useGetGridHealth()
    

    const fetchGridHealth = async()=>{
        await getGridHealth({})
    }

    useEffect(()=>{
        fetchGridHealth()
    },[])

    const gridData = useMemo(()=>{
        if(data)return data.data.data
        return fallbackData
    },[data])

    return{
        gridData,
        isLoading
    }
}

export default  useMCGrid