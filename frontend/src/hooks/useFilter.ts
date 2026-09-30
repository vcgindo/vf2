import {useEffect, useState} from 'react';
import { InputTypes } from '../VectorFlow/Pages/MTO/Common/Enum';
import { checkValue, findUniqueKeysAndValues, getDynamicAttributes, getKeyName, getType } from '../helpers/utils';
import { filterAttributes, staticHeaderConfig } from '../VectorFlow/Pages/MTO/Common/VFCommonFilter/Constants';
import { FilterState } from '../VectorFlow/types/MTO';
import _ from 'lodash';

const useFilter=(filterData: any, page: any)=>{
    const [multiFilter, setMultiFilter]= useState<any>({})
    const [isFilterOpen, setIsFilterOpen] = useState(false);
    const [isMfgSelected, setIsMfgSelected] = useState<boolean>(false);
    const [appliedFilters, setAppliedFilters] = useState<any>({});
    
    const onFilterRemove = (parentId: string, filterId: any, value: any) => {
         const updatedMultiFilter = { ...multiFilter };
        const filters = updatedMultiFilter[parentId as keyof FilterState]?.filters || [];
      
        for (let i = 0; i < filters.length; i++) {
        const { attributeName } = filters[i];
      
          if (attributeName === filterId) {
            filters[i].value = filters[i]?.value?.filter((val: any) => {

                const newVal = val.value;
              const compareValue = value === "0" && typeof val.value === "number" ? Number(value) : value;
              if(compareValue !==newVal){
                    return val
              }
            })
          }
        }
 
        updatedMultiFilter[parentId as keyof FilterState].filters = [...filters];

        
        const newFilters = _.cloneDeep(updatedMultiFilter).filters.filter((e: any) => {
            return e?.header?.attributeName !== filterId;
        });

        


        if(newFilters.length===0){
            newFilters.push({
                attributeName: '',
                operator: '',
                value: []
              });
        }
        const val = {...updatedMultiFilter, filters: newFilters};
        setMultiFilter(val); 
        return val;
     
      };

    const onApplyFilter = (filter: any,selectedHeader?:any,selectedOperator?:any,selectedValue?:any) => {

        const filterPayload = {
            headers: selectedHeader,
            operators: selectedOperator,
            values: selectedValue,
          };
        
        setAppliedFilters(filter || filterPayload );
        setIsMfgSelected(true);
        setIsFilterOpen(false)
    }
    const onAddFilter = () => {
        setIsFilterOpen(true)
    }

    const toggleFilter = (state: boolean) => {
        setIsFilterOpen(state);
    }
    



    useEffect(()=>{

        if(filterData && Object.keys(filterData)?.length){

        const updatedFilterAttributes: any = {
            customer: [...filterAttributes.customer, ...getDynamicAttributes( filterData?.hdrkeymap?.cattr)],
            resource: [...filterAttributes.resource],
            order: [...filterAttributes.order, ...getDynamicAttributes(filterData?.hdrkeymap?.lattr), ...getDynamicAttributes(filterData?.hdrkeymap?.oattr)], 
            major: [...filterAttributes.major]
        };

        const filterOptionsConfig = findUniqueKeysAndValues(filterData);

        const routes = filterOptionsConfig?.route?.map((r: any) => r.value) || [];
        const { ccrs, ccrgroups, mappings, dept } = filterData || {};
        const department: any = [];
        const ccr: any = [];
        const ccrGrp: any = [];
        const mjr: any = [];
        let min: any = [];

        for(let i = 0; i < mappings.length; i++){
            const { rid, ccrid, grpid, deptid } = mappings[i];
            if(routes.includes(rid)){
                if(dept[deptid]?.nm && !checkValue(department,  deptid )){
                    department.push({value: deptid, label :dept[deptid]?.nm})
                }
                if(ccrs[ccrid]?.nm && !checkValue(ccr, ccrid )){
                    ccr.push({value: ccrid, label: ccrs[ccrid]?.nm})
                }
                if(ccrgroups[grpid]?.nm && !checkValue(ccrGrp, grpid)){
                    ccrGrp.push({value: grpid, label: ccrgroups[grpid]?.nm})
                }
            }
        }

        for(let i = 0; i < filterOptionsConfig?.majid?.length; i++){
            const mjrid = filterOptionsConfig?.majid[i].id;
            if(filterData?.mjar[mjrid]?.name && !checkValue(mjr, mjrid )){
                mjr.push({value: mjrid, label: filterData?.mjar[mjrid]?.name});
                const minors = filterData?.mjar[mjrid]?.min?.map((reason: any) => ({ value: reason.id, label: reason.name}));
                min = [...min, ...minors];
            }
        }

        filterOptionsConfig.majid = mjr;
        filterOptionsConfig.minid = min;
        filterOptionsConfig.deptid = department;
        filterOptionsConfig.grpid = ccrGrp;
        filterOptionsConfig.ccrid = ccr;
        const filterObjects: FilterState = {}

        if(page?.mjr){
            filterObjects['major'] = {
                id: "mjr",
                label: "Major Reason & Minor Reason ",
                filters: updatedFilterAttributes?.major?.map((key: any) => ({
                    type: staticHeaderConfig[key]?.type || InputTypes.MultiSelect,
                    name: staticHeaderConfig[key]?.name ,
                    attributeName: key,
                    operator: '',
                    value: '',
                    options: filterOptionsConfig[key]
                }))
            }
        }
        if(page?.or){
            filterObjects["orders"] = {
                id: "odr",
                label: "Order Details Filter",
                filters: updatedFilterAttributes?.order?.map((key: any) => ({
                    type: staticHeaderConfig[key]?.type || getType(filterData?.hdrkeymap?.lattr, key) || getType(filterData?.hdrkeymap?.oattr, key),
                    name: staticHeaderConfig[key]?.name || (getKeyName(filterData?.hdrkeymap?.lattr, key) || getKeyName(filterData?.hdrkeymap?.oattr, key)),
                    attributeName: key,
                    operator: '',
                    value: [],
                    options: key === 'ms' ?  filterData?.system_type?.map((type: any) => ({ value: type, label: type })): filterOptionsConfig[key]
                })
            ).filter((fil: any) => filterAttributes.order.includes(fil.attributeName) || ((getKeyName(filterData?.hdrkeymap.lattr, fil.attributeName) === fil.name) || (getKeyName(filterData?.hdrkeymap.oattr, fil.attributeName) === fil.name)))

            }

        }     

        if(page?.res){
            filterObjects["resources"] = {
                id: "res",
                label: "Resources Filter",
                filters: updatedFilterAttributes?.resource?.map((key: any) => ({
                    type: staticHeaderConfig[key]?.type || InputTypes.MultiSelect,
                    name: staticHeaderConfig[key]?.name,
                    attributeName: key,
                    operator: '',
                    value: '',
                    options: filterOptionsConfig[key]
                }))
            }
        }
        if(page?.cus){
            filterObjects["customers"] = {
                id: "cus",
                label: "Customer Filter",
                filters: updatedFilterAttributes?.customer?.map((key: any) =>  ({
                    type: staticHeaderConfig[key]?.type || InputTypes.MultiSelect,
                    name: staticHeaderConfig[key]?.name || getKeyName(filterData?.hdrkeymap?.cattr, key),
                    attributeName: key,
                    operator: '',
                    value: '',
                    options: filterOptionsConfig[key]
                })).filter((fil: any) => filterAttributes.customer.includes(fil.attributeName) || (getKeyName(filterData?.hdrkeymap.cattr, fil.attributeName) === fil.name))
            }
        }
        setMultiFilter(filterObjects);
    }

    },[filterData])

    useEffect(()=>{
        if(Object.keys(multiFilter).length){
            setAppliedFilters(multiFilter);
        }
    },[multiFilter])
           
    return{
        state:multiFilter,
        setState:setMultiFilter,
        onFilterRemove:onFilterRemove,
        isFilterOpen:isFilterOpen,
        isMfgSelected:isMfgSelected,
        onApplyFilter:onApplyFilter,
        onAddFilter:onAddFilter,
        toggleFilter:toggleFilter,
        appliedFilters:appliedFilters,
        setAppliedFilters:setAppliedFilters
    }

}

export default useFilter