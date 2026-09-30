import {useState,useEffect,useCallback, useRef} from 'react'

import VFTable from "../../VectorFLOW/commons/VFTable"

import { TableWrapper } from "../UserURLsDrawer/styles"

import { useUserData } from "../../../context"
import { SecondaryButton, Skeleton } from "../../commons/styled"
import { notifyError } from '../../../helpers/notify'
import { useGetAllEnvironmentConfiguration } from '../../../VectorFlow/Services/MTA/MDM'
import { GridRef } from '../../../VectorFlow/types/MDM'
import { GridFilterWrapper, TextBtn } from '../../../VectorFlow/Pages/MTO/Common/VFPagination/styles'
import { useDispatch } from 'react-redux'
import { UPDATE_ENV_CONFIG } from '../../../redux/actions/MTA'

 type EnvConfig = {
    Id: number;
    ConfigKey: string;
    ConfigValue: string;
    Description: string;
    Category: string; 
    };
 const initialConfig = {
        EnvProductPermissionArray: [],
        EnvLocationPermissionArray: []
    };
    
interface ViewProps {
    onEdit: (data: any) => void;
    savedFilters: any;
    onSaveFilters: (filters: any) => void;
}

const ViewEnvConfig = (props:ViewProps)=>{

    const {
        onEdit,
        savedFilters,    // Destructure new props
        onSaveFilters
    } = props

    const {user} = useUserData()
    const ref = useRef<GridRef>();
    const [isDisabled, setIsDisabled]= useState<boolean>(true)
    const themeUi = user.user.theme_ui
    const dispatch = useDispatch();
    const [rowData,setRowData] = useState<Array<any>>([])
    const {mutateAsync : getAllEnvConfiguration} = useGetAllEnvironmentConfiguration();
    const getAllEnvConfig = useCallback(async()=>{
        try{
            const response = await getAllEnvConfiguration();
            const data : EnvConfig[]  = response?.data?.data;
            
            const configMap = data.reduce((map: any, item: EnvConfig) => {
                map[item.ConfigKey] = item.ConfigValue;
                if (item.Category === 'ProductPermission') {
                    map.EnvProductPermissionArray.push(item.ConfigValue);
                } else if (item.Category === 'LocationPermission') {
                    map.EnvLocationPermissionArray.push(item.ConfigValue);
                }
                return map;
            }, JSON.parse(JSON.stringify(initialConfig)));

            dispatch(UPDATE_ENV_CONFIG(configMap));


            const filteredData = data.filter(item => 
                item.Category !== "Filters"
            );
            setRowData(filteredData.sort((row1:any,row2:any)=>row1.id - row2.id));
        }catch(error:any){
            console.error(error)
            notifyError("Server Went Unresponsive")
        }finally{
            setIsLoading(false)
        }
    },[])

    // const allUrls = [
    //     {
    //         "id": 1,
    //         "name": "VectorFlow. Master Data Management. Control Panel",
    //         "code": "MDM-CP",
    //         "description": "VectorFlow. Master Data Management. Control Panel",
    //         "url": "/master-data-management/control-panel"
    //     }
    // ]

    const [isLoading,setIsLoading] = useState<boolean>(true)
    
    useEffect(()=>{
        getAllEnvConfig()
    },[])

    const onFirstDataRendered = (params: any) => {
        if (savedFilters && Object.keys(savedFilters).length > 0) {
            params.api.setFilterModel(savedFilters);
            setIsDisabled(false);
            params.api.onFilterChanged();
        }
    }
    if(isLoading){
        return (
            <Skeleton
                style={{height:400,width:'100%'}}
            />
        )
    }

    const clearGridFilter = () =>{   
        ref?.current?.api.setFilterModel(null);
          setIsDisabled(true);
    }

    const CustomStatusPanel = () => {
        return (
            <GridFilterWrapper style={{marginTop:'25px'}}>
                <TextBtn onClick={clearGridFilter} disabled={isDisabled} themeUi={themeUi}>
                    Clear All Grid Filters
                </TextBtn>  
            </GridFilterWrapper>           
        );
    };

    return(
        <TableWrapper>
            <VFTable 
                ref={ref}
                defaultColDef={{
                    flex:1,
                    cellStyle:{
                        'text-align':'center'
                    },
                    floatingFilter: true,
                    filter: "agMultiColumnFilter"
                }}
                onFirstDataRendered={onFirstDataRendered}
                rowHeight={50}
                height="600px"
                rowData={rowData}
                statusBar={{
                    statusPanels: !isLoading?[
                      { statusPanel: 'agTotalAndFilteredRowCountComponent', align: 'left' },
                      { statusPanel: 'agTotalRowCountComponent', align: 'left' },
                      { statusPanel: 'agFilteredRowCountComponent', align: 'left' },
                      { statusPanel: 'agSelectedRowCountComponent', align: 'left' },
                      { statusPanel: 'agAggregationComponent', align: 'left' },
                      { statusPanel: CustomStatusPanel, align: "right" },

                    ]:
                    [],
                  }}
                columnDefs={[
                    {
                        colId:"ConfigKey",
                        field:"ConfigKey"
                    },
                    {
                        colId:"ConfigValue",
                        field:"ConfigValue"
                    },
                    {
                        colId:"Description",
                        field:"Description"
                    },
                    {
                        colId:'edit',
                        field:'edit',
                        headerName:'',
                        floatingFilter:false,
                        maxWidth:80,
                        cellStyle:{
                            display:'flex',
                            'align-items':'center',
                        },
                        cellRenderer:(params:any)=>(
                            <SecondaryButton
                                style={{backgroundColor:'transparent'}}
                                themeUi={themeUi}
                                onClick={()=>onEdit(params.data)}
                            >
                               
                                <img src="/assets/img/VectorFLOW/NMS/edit-draft.svg" height={20} width={20}/>
                            </SecondaryButton>
                        )
                    },                  
                ]}
                onFilterChanged={() => {
                    if (rowData && rowData.length > 0) {
                        const filterModel = ref?.current?.api?.getFilterModel();
                        onSaveFilters(filterModel);
                        if (filterModel && Object.keys(filterModel).length > 0) {
                            setIsDisabled(false);
                        } else {
                            setIsDisabled(true);
                        }
                    }
                }}
            />
            </TableWrapper>
    )
}

export default ViewEnvConfig