import {useState,useEffect,useCallback, useRef} from 'react'

import VFTable from "../../VectorFLOW/commons/VFTable"

import { TableWrapper } from "../UserURLsDrawer/styles"

import { useUserData } from "../../../context"
import { SecondaryButton, Skeleton } from "../../commons/styled"
import { notifyError } from '../../../helpers/notify'
import {  useGetAllUIMDMConfiguration } from '../../../VectorFlow/Services/MTA/MDM'
import { GridRef } from '../../../VectorFlow/types/MDM'
import { GridFilterWrapper, TextBtn } from '../../../VectorFlow/Pages/MTO/Common/VFPagination/styles'

interface ViewProps {
    onEdit: (data: any) => void;
    savedFilters: any;
    onSaveFilters: (filters: any) => void;
}

const ViewUiMDMConfig = (props:ViewProps)=>{

    const {
        onEdit,
        savedFilters,
        onSaveFilters
    } = props

    const {user} = useUserData()

    const themeUi = user.user.theme_ui

    const [rowData,setRowData] = useState<Array<any>>([])
    const {mutateAsync : getAllUIMDMConfiguration} = useGetAllUIMDMConfiguration();
    const getAllUIMDMConfig = useCallback(async()=>{
        try{
            const response = await getAllUIMDMConfiguration();
            const data = response?.data?.data;
            setRowData(data)
        }catch(error:any){
            console.error(error)
            notifyError("Server Went Unresponsive")
        }finally{
            setIsLoading(false)
        }
    },[])

    const [isLoading,setIsLoading] = useState<boolean>(true)
    
    useEffect(()=>{
        getAllUIMDMConfig()
    },[])

    const onFirstDataRendered = (params: any) => {
        if (savedFilters && Object.keys(savedFilters).length > 0) {
            params.api.setFilterModel(savedFilters);
            setIsDisabled(false);
            params.api.onFilterChanged();
        }
    }

    const ref = useRef<GridRef>();
    const [isDisabled, setIsDisabled]= useState<boolean>(true)

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

    if(isLoading){
        return (
            <Skeleton
                style={{height:400,width:'100%'}}
            />
        )
    }

    return(
        <TableWrapper>
            <VFTable 
                ref={ref}
                defaultColDef={{
                    minWidth: 200,
                    cellStyle:{
                         'text-align':'center',
                      'justify-content':'center',
                     
                    },
                    floatingFilter: true,
                    filter: "agMultiColumnFilter"
                }}
                rowHeight={50}
                height="600px"
                rowData={rowData}
                onFirstDataRendered={onFirstDataRendered}
                columnDefs={[
                    { colId:"MasterId", field:"MasterId" },
                    { colId:"MasterName", field:"MasterName" },
                    { colId:"Col_Code", field:"Col_Code" },
                    { colId:"TableField", field:"TableField" },
                    { colId:"Col_Position", field:"Col_Position" },
                    { colId:"Header", field:"Header" },
                    { 
                        colId:"Visible", 
                        field:"Visible",
                        cellStyle:{ display:'flex', justifyContent:'center', alignItems:'center' }
                    },
                    { 
                        colId:"CellAlignment", 
                        field:"CellAlignment",
                        cellStyle: { 'text-align':'center' }
                    },
                
                    { colId:"IsAdd", field:"IsAdd", cellStyle:{ display:'flex', justifyContent:'center', alignItems:'center' } },
                    { colId:"IsEdit", field:"IsEdit", cellStyle:{ display:'flex', justifyContent:'center', alignItems:'center' } },
                    { colId:"IsFilter", field:"IsFilter", cellStyle:{ display:'flex', justifyContent:'center', alignItems:'center' } },
                    { colId:"IsDownload", field:"IsDownload", cellStyle:{ display:'flex', justifyContent:'center', alignItems:'center' } },
                    { colId:"IsApplicable", field:"IsApplicable", cellStyle:{ display:'flex', justifyContent:'center', alignItems:'center' } },
                    { colId:"DataType", field:"DataType" },
                    { colId:"IsDelete", field:"IsDelete", cellStyle:{ display:'flex', justifyContent:'center', alignItems:'center' } },
              
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
            />
            </TableWrapper>
    )
}

export default ViewUiMDMConfig