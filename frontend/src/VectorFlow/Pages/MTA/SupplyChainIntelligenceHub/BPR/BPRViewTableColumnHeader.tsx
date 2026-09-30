import React, {useState, useEffect, useRef} from 'react'

import {BPRViewTableColumnFilterWrapper, BPRViewTableHeader,BPRViewTableHeaderFilterIcon,BPRViewTableHeaderFilterAlert} from './styles'

import BPRViewTableColumnFilter from './BPRViewTableColumnFilter'
import { BPRViewTableColDef } from './BPRViewTable'
import Portal from '../../../../../components/VectorFLOW/layouts/Portal'
import { useUserData } from '../../../../../context'

const BPRViewTableColumnHeader = ({colDef,query}:{colDef:BPRViewTableColDef,query:string})=>{
    const {user} = useUserData()
    const themeUi = user.user.theme_ui
    const [isFilterOpen, setFilterOpen] = useState<boolean>(false)
    const [filterPosition, setFilterPosition] = useState<{top:number,left:number}>({
        top:0,
        left:0
    })
    const filterRef = useRef<HTMLDivElement>(null)

    const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
        const { top, left } = e.currentTarget.getBoundingClientRect();
        const newTop = top + e.currentTarget.offsetHeight + 10; 
        const newLeft = left - 85; 
        setFilterPosition({ top: newTop, left: newLeft });
        setFilterOpen((prev) => !prev);
        e.stopPropagation();
    };

    const handleClickAway = (e: MouseEvent) => {
        if (filterRef.current && !filterRef.current.contains(e.target as Node)) {
            setFilterOpen(false)
        }
    }

    useEffect(() => {
        if (isFilterOpen) {
            document.addEventListener('mousedown', handleClickAway)
        } else {
            document.removeEventListener('mousedown', handleClickAway)
        }
        return () => {
            document.removeEventListener('mousedown', handleClickAway)
        }
    }, [isFilterOpen])


    return (
        <BPRViewTableHeader style={{minWidth:colDef.colId==='whereabouts'?200:120}} key={colDef.colId}>
            {colDef.headerName}
            {colDef.filter && (
                <React.Fragment>
                    <BPRViewTableHeaderFilterIcon src='/assets/img/VectorFLOW/BPR/filter.svg' onClick={handleClick} style={{border:isFilterOpen?'1px solid black':'none'}}/>
                    {colDef.filterValue!=='' && (<BPRViewTableHeaderFilterAlert themeUi={themeUi}/>)}
                </React.Fragment>
            )}
            {isFilterOpen && (
                <Portal wrapperId='filter'>
                    <BPRViewTableColumnFilterWrapper
                        ref={filterRef}
                        style={filterPosition}
                    >
                        <BPRViewTableColumnFilter
                            dataType={colDef.dataType}
                            
                            filterString={colDef.filterValue || ""}
                            onApplyFilter={(f,q)=>{
                                if(colDef.onApplyFilter){
                                    colDef.onApplyFilter(f,q)
                                }
                            }}
                            query={query}
                        />
                    </BPRViewTableColumnFilterWrapper>
                </Portal>
            )}
        </BPRViewTableHeader>
    )
}

export default BPRViewTableColumnHeader
