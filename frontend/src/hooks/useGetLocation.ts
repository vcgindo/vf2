import {useMemo} from 'react'
import { notifyError } from '../helpers/notify'

import { MultiFilterSupplyChainCheckboxList } from '../helpers/BPRConstants'

import { useGetLocationTypes } from "../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR"

export const parseLocationTypes = (response: any) => {
    const rawLocations = response?.data?.data

    // A reconstructed/local database can legitimately have no location rows yet.
    // Keep the filter usable with the same defaults shown while the request loads.
    if (rawLocations == null || rawLocations === '') {
        return MultiFilterSupplyChainCheckboxList
    }

    const parsed = typeof rawLocations === 'string'
        ? JSON.parse(rawLocations)
        : rawLocations

    if (!Array.isArray(parsed) || parsed.length === 0) {
        return MultiFilterSupplyChainCheckboxList
    }

    const locations = parsed
        .map((location: any) => location?.lt)
        .filter((locationType: any) => typeof locationType === 'string' && locationType.trim())
        .map((locationType: string) => ({ label: locationType, id: locationType }))

    return locations.length > 0 ? locations : MultiFilterSupplyChainCheckboxList
}


const useGetLocation =()=>{

    const {data,isLoading} = useGetLocationTypes()

    const locations= useMemo(()=>{
        try{
            if(isLoading)return MultiFilterSupplyChainCheckboxList
            return parseLocationTypes(data)
        }catch(err){
            notifyError('Failed To Fetch Location Types')
            return MultiFilterSupplyChainCheckboxList
        }
    },[data,isLoading])

    return {
        locations
    }
}

export default useGetLocation
