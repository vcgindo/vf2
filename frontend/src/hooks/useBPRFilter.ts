import {useState} from 'react';
import { BPRFilterState} from '../VectorFlow/types/BPR';
import { useDispatch } from 'react-redux';
import { UPDATE_MTA_VF_MULTI_FILTER } from '../redux/actions/MTA';

const useBPRFilter = () => {
    const defaultFilters = {
        supplyChainFilter: {
            id: '1',
            label: 'SupplyChain',
            filters: []
        },
        locationFilter: {
            id: '2',
            label: 'Location',
            filters: [
                // {   
                //     name:'LF1',
                //     attributeName: "L1",
                //     value: "",
                //     operator: "<=",          
                // },
                // {   
                //     name:'LF2',
                //     attributeName: "L2",
                //     value: "",
                //     operator: "<=",          
                // },
                // {   
                //     name:'LF3',
                //     attributeName: "L3",
                //     value: "",
                //     operator: "<=",          
                // },
                // {   
                //     name:'LF4',
                //     attributeName: "L4",
                //     value: "",
                //     operator: "<=",          
                // },
                // {   
                //     name:'LF5',
                //     attributeName: "L5",
                //     value: "",
                //     operator: "<=",          
                // },

            ]
        },
        productFilter: {
            id: '3',
            label: 'Product',
            filters: []
        },
        availabilityFilter: {
            id: '4',
            label: 'Availability',
            filters: []
        },
        coverageFilter: {
            id: '5',
            label: 'Coverage',
            filters: []
        },
        colorFilter: {
            id: '6',
            label: 'Color',
            filters: []
        },
        generalFilter: {
            id: '7',
            label: 'General',
            filters: []

        },
        customAttributeFilter:{
            id:'8',
            label:'Attribute',
            filters:[]
        },
        horizonFilter: {
            id:'9',
            label: 'Horizon',
            filters: []
        }
    };

    const [multiFilter, setMultiFilter]= useState<BPRFilterState>(defaultFilters)
    const dispatch = useDispatch();


    const onDelete = (parentId:any, filterId:any, value:any) => {
        const updatedMultiFilter = { ...multiFilter };
        const currGroupKey = Object.keys(updatedMultiFilter).find(
            (key) => updatedMultiFilter[key as keyof BPRFilterState].id === parentId
        ) as keyof BPRFilterState | undefined;
        
        if (currGroupKey && updatedMultiFilter[currGroupKey]?.filters) {
            updatedMultiFilter[currGroupKey] = {
                ...updatedMultiFilter[currGroupKey],
                filters: updatedMultiFilter[currGroupKey]!.filters.filter(
                    (filter) => filter.name !== filterId || filter.value !== value
                ),
            };
        }
        
        setMultiFilter(updatedMultiFilter);
        dispatch(UPDATE_MTA_VF_MULTI_FILTER(updatedMultiFilter))
        return updatedMultiFilter
    };
        
           

    return{
        state:multiFilter,
        setState:setMultiFilter,
        onDelete:onDelete,
        defaultFilters:defaultFilters
    }

}

export default useBPRFilter