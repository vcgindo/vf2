import {useState,useMemo} from 'react'
import { ColDef } from 'ag-grid-enterprise';
import { useUserData } from '../../../../../context';
import BPRViewTableRequestCellRenderer from './BPRViewTableRequestCellRenderer';
import BPRViewTableRowCellWithReadMore from './BPRViewTableRowCellWithReadMore';
import {BPRViewTableWrapper,BPRViewTablePrefix,BPRViewTableGrid,BPRViewTableHeaderContainer,BPRViewTableRowContainer,BPRViewTableRow,BPRViewTableRowCell,BPRViewTablePrefixWrapper, BPRViewTablePrefixText, BPRViewTablePrefixIcon, BPRViewTableNoDataContainer, BPRViewTableNoDataHeader, BPRViewTableNoDataText, BPRViewTableHeaderTab, BPRViewTableAvailabilityCellRenderer} from './styles'
import AgeingCellRenderer from './AgeingCellRenderer';
import WhereAboutsCellRenderer from './WhereAboutsCellRenderer';
import BPRViewTableColumnHeader from './BPRViewTableColumnHeader';
import { getFiltersArrayFromColDefs, performNumericalOpertionsForBPRViewTableFilter, performStringOpertionsForBPRViewTableFilter } from '../../../../../helpers/utils';

export interface BPRViewTableColDef{
    headerName: any
    colId: string
    field?: string
    filter?:boolean
    filterValue?:string
    dataType?:string
    onApplyFilter?:(filterString:string,query:string)=>void
    onCellClicked?:()=>void
}

interface BPRViewTableProps{
    colDefs:BPRViewTableColDef[]
    rowData:any
    tablePrefixSrc:string
    tableHeader:string
    onRequestExpediting?:()=>void
}

const BPRViewTable = (props:BPRViewTableProps)=>{

    const {
        colDefs,
        rowData,
        tablePrefixSrc,
        tableHeader,
        onRequestExpediting
    } = props

    const onReq = ()=>{
        if(onRequestExpediting){
            onRequestExpediting()
        }
    }

    const {user} = useUserData()
    const {theme_ui} = user.user

    const [filters,setFilters] = useState<Array<any>>(getFiltersArrayFromColDefs(colDefs))
    const onApplyFilter = (key:string,value:string,query:string)=>{
       setFilters((prev)=>prev.map((f)=>f.colId===key?{...f,filterValue:value,query:query}:f))
    }

    const filteredRows = useMemo(():Array<any>=>{
        if(rowData){
        if(Array.isArray(rowData)){
            return rowData.filter((r:any)=>{
                return filters.every((f)=>{
                    

                    if(f.filterValue===""){
                        return true
                    }
                    
                    if(f.dataType==='number'){ 
                        return performNumericalOpertionsForBPRViewTableFilter(parseFloat(r[f.colId]),parseFloat(f.filterValue),f.query)
                    }

                    if(!r[f.colId])return false

                    return performStringOpertionsForBPRViewTableFilter(String(r[f.colId]).toUpperCase(),f.filterValue.toUpperCase(),f.query)
                })
            })
        }
    }
        return []
    },[filters,rowData])

    const renderRows = ()=>{
        

        if(!filteredRows || filteredRows.length===0){
            return(
                    <BPRViewTableNoDataContainer>
                        <BPRViewTableNoDataHeader>
                            No Data To Show 
                        </BPRViewTableNoDataHeader>
                        <BPRViewTableNoDataText>
                            Please select a row from above table to view data
                        </BPRViewTableNoDataText>
                    </BPRViewTableNoDataContainer>
            )
        }
        return(
            filteredRows && filteredRows.map((row:any,index:number)=>{
                return(
                    <BPRViewTableRow key={index}>
                        {
                            colDefs.map((colDef:ColDef,index:number)=>{
                                if(colDef.colId){
                                   if(row[colDef.colId] || colDef.colId==='whereabouts' || colDef.colId==="request"){

                                        if(colDef.colId==='whereabouts'){
                                            return <WhereAboutsCellRenderer value={row}/>
                                        }

                                        if(colDef.colId==='ag'){
                                            return (
                                                <AgeingCellRenderer value={row}/>
                                            )
                                        }

                                       if(colDef.colId==='remarks'){
                                            return(
                                                <BPRViewTableRowCellWithReadMore value={row[colDef.colId]} key={index}/>
                                            )
                                       }
                                       if(colDef.colId==='request'){
                                            return(
                                                <BPRViewTableRequestCellRenderer onClick={onReq} key={index}/>
                                            )
                                        }
                                        if(colDef.colId==='avail'){
                                            return(
                                                <BPRViewTableRowCell key={index}>
                                                    <BPRViewTableAvailabilityCellRenderer>
                                                        {row[colDef.colId]}
                                                    </BPRViewTableAvailabilityCellRenderer>
                                                </BPRViewTableRowCell>
                                            )
                                        }
                                       return(
                                        <BPRViewTableRowCell key={index}>
                                            {row[colDef.colId]}
                                        </BPRViewTableRowCell>
                                    )
                                   }
                                   return(
                                        <BPRViewTableRowCell key={index}>
                                            NULL
                                        </BPRViewTableRowCell>
                                   )
                                }
                                }
                            )
                        }
                    </BPRViewTableRow>
                )
            })
        )
    }

    return(
        <BPRViewTableWrapper>
            <BPRViewTablePrefixWrapper>
                <BPRViewTablePrefix>
                <BPRViewTableHeaderTab
                    themeUi={theme_ui}
                    zIndex={1}
                    marLeft={false}
                    status='active'
                >
                    <BPRViewTablePrefixText>
                    {tableHeader}
                    </BPRViewTablePrefixText>
                    <BPRViewTablePrefixIcon src={tablePrefixSrc}/>
                </BPRViewTableHeaderTab>
                </BPRViewTablePrefix>
            </BPRViewTablePrefixWrapper>
            
            <BPRViewTableGrid>
                {/* {tableHeader && (
                    <TableHeader>
                        {tableHeader}
                    </TableHeader>
                )} */}
                <BPRViewTableHeaderContainer>
                    {colDefs.map((colDef,index)=>{
                        const currFilter = filters.find((f)=>f.colId===colDef.colId)
                        return (
                            <BPRViewTableColumnHeader 
                                key={index}
                                colDef={{
                                    ...colDef,
                                    filterValue:currFilter?.filterValue || '',
                                    onApplyFilter:(filterString,query)=> {
                                    onApplyFilter(colDef.colId,filterString,query)
                                }}}
                                query={currFilter?.query}
                            />
                        )
                    })}
                </BPRViewTableHeaderContainer>
                <BPRViewTableRowContainer>
                    {renderRows()}
                </BPRViewTableRowContainer>
            </BPRViewTableGrid>
        </BPRViewTableWrapper>
    )
}



export default BPRViewTable;