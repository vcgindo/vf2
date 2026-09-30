import {useState,useEffect,useCallback} from 'react'

import VFTable from "../../VectorFLOW/commons/VFTable"

import { TableWrapper } from "../UserURLsDrawer/styles"

import { useUserData } from "../../../context"
import { SecondaryButton, Skeleton } from "../../commons/styled"
import axios from 'axios'
import { notifyError } from '../../../helpers/notify'


const ViewURLs = (props:{onDelete:(data:any)=>void,onEdit:(data:any)=>void})=>{

    const {
        onDelete,
        onEdit
    } = props

    const {user} = useUserData()

    const themeUi = user.user.theme_ui

    const [rowData,setRowData] = useState<Array<any>>([])

    const getAllRoles = useCallback(async()=>{
        try{
            const {data} = await axios.get(`${process.env.REACT_APP_API_HOST}api/user/all-role/`)
            setRowData(data.sort((row1:any,row2:any)=>row1.id - row2.id))
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
        getAllRoles()
    },[])

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
                defaultColDef={{
                    flex:1,
                    cellStyle:{
                        'text-align':'center'
                    }
                }}
                rowHeight={50}
                height="600px"
                rowData={rowData}
                columnDefs={[
                    {
                        colId:"name",
                        field:"name"
                    },
                    {
                        colId:"code",
                        field:"code"
                    },
                    {
                        colId:"description",
                        field:"description"
                    },
                    {
                        colId:'edit',
                        field:'edit',
                        headerName:'',
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
                    {
                        colId:'delete',
                        field:'delete',
                        headerName:'',
                        maxWidth:80,
                        cellStyle:{
                            display:'flex',
                            'align-items':'center',
                        },
                        cellRenderer:(params:any)=>(
                            <SecondaryButton
                                style={{backgroundColor:'transparent'}}
                                themeUi={themeUi}
                                onClick={()=>onDelete(params.data)}
                            >
                               
                                <img src="/assets/img/VectorFLOW/NMS/delete-draft.svg" height={20} width={20}/>
                            </SecondaryButton>
                        )
                    }
                ]}
            />
            {/* <Skeleton
                style={{height:300,width:'100%'}}
            /> */}
            </TableWrapper>
    )
}

export default ViewURLs