import { useEffect, useMemo, useState } from "react"
import { Field } from "../../../../../VectorFlow/types/MDM";
import { useGetMasterUIConfiguration, useGetSkuLoc, useGetTaskMastersHistory} from "../../../../../VectorFlow/Services/MTA/MDM"
import { useUserData } from "../../../../../context";
import { notifyError, notifySuccess } from '../../../../../helpers/notify'


const useDataModificationHistory = () => {
 
    const [rowData, setRowData] = useState<Array<any>>([])
    const [options, setOptions] = useState<any>(null);
    const [skuOptions, setSkuOptions] = useState<any>(null);
    const [locOptions, setLocOptions] = useState<any>(null);
 
    const [selectedOption, setSelectedOption] = useState<any>(null);
    const [selectedSkuOption, setSelectedSkuOption] = useState<any>(null);
    const [selectedLocOption, setSelectedLocOption] = useState<any>(null);
    // const [masterId, setMasterId]= useState<any>(null);
  
    const {mutateAsync:getSKULocations} = useGetSkuLoc();
    const {mutateAsync:masterUIConfiguration} = useGetMasterUIConfiguration();
    const {mutateAsync:getTaskMastersHistory} = useGetTaskMastersHistory()

    const {user} = useUserData()
    const theme_ui=user.user.theme_ui


 
    useEffect(()=>{
        const getMasterUIConfigurationData = async()=>{
        const {data} = await masterUIConfiguration('modify');
        setOptions(data.data.map((option: any)=>{
            return {label:option.name, value:option.id, fields:option.fields}
            }));
        }
        getMasterUIConfigurationData()
    },[])
    
 
    // useEffect(()=>{
    //     const fetchSKULocations = async()=>{
    //         const {data} = await getSKULocations({masterId:1});
    //         setSkuOptions(data.data.map((option: any)=>{
    //             return {label:option.SKUCode, value:option.id, fields:option.fields}
    //             }));
    //         }
    //     fetchSKULocations()
    // },[])

 
    const fetchSKULocations = async (masterId: any) => {
        try {
            const response = await getSKULocations({ masterId })

            const data = response?.data?.data
            const isDataEmpty = !data || (!data.sku?.length && !data.loc?.length)

            if (isDataEmpty) {
                notifyError("No Data Found")
                return;
            }
            
            setSkuOptions(response?.data?.data?.sku.map((option: any) => ({
                label: option.SKUCode, value: option.SKUCode, fields: option.fields
            })) || []);
            setLocOptions(response?.data?.data?.loc.map((option: any) => ({
                label: option.WHCode, value: option.WHCode, fields: option.fields
            })) || []);

    
        } catch (error) {
            notifyError("Failed to fetch data");
        }
    };
    
    const onMasterChange = (newValue: any) => {
        setSelectedOption(newValue)
        setSkuOptions([])          
        setLocOptions([]) 
        setSelectedSkuOption(null)
        setSelectedLocOption(null) 
        setRowData([])       
        fetchSKULocations(newValue.value)
    }

     
    const handleChange = () => {
        const postTaskMasterHistory = async() =>{
            const payload:any = {masterId:selectedOption.value}
            if(isSkuDisabled()){
                payload['WHCode'] = selectedLocOption.value;
            }
            if(isLocDisabled()){
                payload['skuCode'] = selectedSkuOption.value;
            }
            if(!isSkuDisabled() && !isLocDisabled()){
                payload['WHCode'] = selectedLocOption.value;
                payload['skuCode'] = selectedSkuOption.value;
            }
            const {data} = await getTaskMastersHistory(payload);
            data.data === null ? notifyError(data.msg) : notifySuccess(data.msg)
            setRowData(data.data);
        }
        postTaskMasterHistory()
    }
    

    const handleReset = () => {
        setSelectedSkuOption([]);
        setSelectedLocOption([]);
        setRowData([]);
        setSkuOptions([]);
        setLocOptions([]);
        setSelectedOption([])
 
        const fetchInitialData = async () => {
            try {
                  const { data: optionsData } = await masterUIConfiguration('modify');
                        setOptions(optionsData?.data?.map((option: any) => ({
                        label: option.name,
                        value: option.id,
                        fields: option.fields
                    })) || []);
                }
        
                catch (error) {
                    notifyError("Something went wrong")
                }
        };
   
        fetchInitialData();  
    }
 

    const isSkuDisabled =() => {
        if(!selectedOption) return false
        return selectedOption.value==='2' ||
        selectedOption.value==='15' ||
        selectedOption.value==='20' ||
        selectedOption.value==='21' ||
        selectedOption.value==='23' ||
        selectedOption.value==='26' ||
        selectedOption.value==='24' 

    }

    const isLocDisabled = () => {
        if(!selectedOption) return false
        return selectedOption.value ==='1' || selectedOption.value === '5' ||
        selectedOption.value==='27'
    };



    const staticColDefs:any= useMemo(()=>{
        return[
                {
                    headerName: "Date",
                    colId: 'Date',
                    field: 'PendingSince',
                    sort: 'desc',
                   
                },
                {
                    headerName: "RequesterName",
                    colId: 'Requester',
                    field: 'RequesterName',
                },
                {
                    headerName: "ApproverName",
                    colId: 'Approver',
                    field: 'ApproverName',
                },  
        ]
    },[]);
 
    const areValuesEqual = (value1: any, value2: any) => {
        return value1 === value2;
    };
    const getCellStyle = (field: Field) => (params: any) => {
        const rowIdx = params.rowIndex;
        const totalRows = params.api?.getDisplayedRowCount();
        const isLastRow = rowIdx === totalRows - 1;
   
        if (isLastRow) {
            return {};
        }
   
        const previousRowData = params.api?.getDisplayedRowAtIndex(rowIdx + 1)?.data;
        const currentRowData = params.data;
   
        const isChanged = previousRowData && !areValuesEqual(currentRowData[field.key], previousRowData[field.key]);
   
        return {
            // color: isChanged ? '#BC3D80' : 'black',
            // backgroundColor: isChanged ? '#bc3d814d' : 'white',
            fontWeight: isChanged ? '500' : 'normal', 
            color:isChanged?theme_ui==="REGALBLAZE"?"#FCA311": "#BC3D80" : "black",
            backgroundColor:isChanged ? theme_ui==="REGALBLAZE"?"rgb(252, 163, 17,0.3) ": "#bc3d814d": 'white',
        };
    };
   
    const dynamicColDefs = useMemo(() => {
        const arr = selectedOption?.fields?.map((field: Field) => ({
            headerName: field.displayName,
            colId: field.key,
            field: field.key,
            floatingFilter: false,
            cellStyle: getCellStyle(field)
        })) || [];
 
        const arr2 = selectedSkuOption?.fields?.map((field: Field) => ({
            headerName: field.displayName,
            colId: field.key,
            field: field.key,
            floatingFilter: false,
            cellStyle: getCellStyle(field)
        })) || [];
        return [...arr, ...arr2]
 
    }, [selectedOption,selectedSkuOption]);
 
   
    const colDefs = useMemo(() => {
        return [...staticColDefs, ...dynamicColDefs];
      }, [staticColDefs, dynamicColDefs]);
 
      return{
        colDefs,
        rowData,
        options,
        skuOptions,
        locOptions,
        handleChange,
        setRowData,
        handleReset,
        setSelectedOption,
        setSelectedSkuOption,
        setSelectedLocOption,
        selectedOption,
        selectedSkuOption,
        selectedLocOption,
        isSkuDisabled,
        isLocDisabled,
        onMasterChange
       
    }
 
}
 
export default useDataModificationHistory