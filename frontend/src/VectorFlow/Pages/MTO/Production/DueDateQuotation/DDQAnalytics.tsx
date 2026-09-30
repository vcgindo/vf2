import React, { useEffect, useState } from 'react';
import {
    BPRDailyAnalyticsHeader,
    BPRDailyAnalyticsContainer,
    BPRDailyAnalyticsTableCell,
    BPRDailyAnalyticsTableContainer,
    BPRDailyAnalyticsTableHeader,
    BPRDailyAnalyticsTableHeaderContainer,
    BPRDailyAnalyticsTableRow,
    BPRDailyAnalyticsTableRowContainer,
    BPRDailyAnalyticsWrapper,
    BPRDailyAnalyticsTableCellHeader,
} from './DueDateQuotation.styled';
import { formatNumber } from '../../Procurement/MaterialCoverage/CommonFunc';
import { useGetDDQAnalytics } from '../../../../../VectorFlow/Services/MTO/Production/DueDateQuotation';

const DDQAnalytics = () => {

    const {mutateAsync: getAnalyticsData} = useGetDDQAnalytics()

    const [options , setOptions] = useState<any>({Order: [
        { "pcb": "--",
        "pdb":"--",
        "ccr": "--",
        "us": "--",
        "sc": "--",
        "ttl": "--"}
    ]});

    const getData = async()=>{
        try{
            const res:any = await getAnalyticsData();
            if(res.status===200){
                setOptions({Order: [res.data.data]})
            }
        }
        catch(e){
            console.log(e);
        }
    }


    useEffect(()=>{
        getData();
    },[])
    

    const [rowData] = useState([
        {
            headerName: 'Proc Buffer',
        },
        {
            headerName: 'Prod Buffer'
        },
        {
            headerName: 'CCR/ Route'
        },
        {
            headerName: 'Unscheduled'
        },
        {
            headerName: 'Scheduled'
        },
        {
            headerName: 'Count'
        },
    ])



    if (!options.Order) {
        return null
    }


    return (
        <BPRDailyAnalyticsWrapper>
            <BPRDailyAnalyticsContainer>
                <BPRDailyAnalyticsHeader style={{ borderBottom: '1px dashed white' }}>
                    Analytics
                </BPRDailyAnalyticsHeader>
                <BPRDailyAnalyticsHeader>
                    (Orders with unassigned)
                </BPRDailyAnalyticsHeader>

                <BPRDailyAnalyticsTableContainer>
                    <BPRDailyAnalyticsTableHeaderContainer style={{ borderBottom: '1px dashed white' }}>
                        {rowData.map((data) => {

                            if (data.headerName === 'Proc Buffer') {
                                return (
                                    <BPRDailyAnalyticsTableHeader style={{ wordBreak:'break-all', padding: '1px', borderTop: '1px solid white', borderLeft: '1px solid white' }}>
                                        {data.headerName}

                                    </BPRDailyAnalyticsTableHeader>
                                )
                            }
                            else if (data.headerName === "Prod Buffer") {
                                return (
                                    <BPRDailyAnalyticsTableHeader style={{ wordBreak:'break-all', padding: '1px', borderTop: '1px solid white' }}>
                                        {data.headerName}

                                    </BPRDailyAnalyticsTableHeader>
                                )
                            }
                            else if (data.headerName === 'CCR/ Route') {
                                return (
                                    <BPRDailyAnalyticsTableHeader style={{ wordBreak:'break-all', padding: '1px', borderTop: '1px solid white', borderRight: '1px solid white' }}>
                                        {data.headerName}

                                    </BPRDailyAnalyticsTableHeader>
                                )
                            }
                            return (
                                <BPRDailyAnalyticsTableHeader style={{ wordBreak:'break-all', padding: '1px',}}>
                                    {data.headerName}
                                </BPRDailyAnalyticsTableHeader>
                            )
                        })
                        }
                    </BPRDailyAnalyticsTableHeaderContainer>
                    <BPRDailyAnalyticsTableRowContainer>

                        {options?.Order?.map((o: any) => {
                            return (
                                <BPRDailyAnalyticsTableRow style={{
                                    height: 30,
                                    boxShadow: 'none',
                                    backgroundColor: 'transparent',
                                    borderBottom: '1px white solid',
                                    borderRadius: 0
                                }}>

                                    <BPRDailyAnalyticsTableCell>
                                        <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                            {o.pcb}
                                        </BPRDailyAnalyticsTableCellHeader>

                                    </BPRDailyAnalyticsTableCell>
                                    <BPRDailyAnalyticsTableCell>
                                        <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                            {o.pdb}
                                        </BPRDailyAnalyticsTableCellHeader>

                                    </BPRDailyAnalyticsTableCell>
                                    <BPRDailyAnalyticsTableCell>
                                        <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }} >
                                            {formatNumber(o.ccr)}
                                        </BPRDailyAnalyticsTableCellHeader>

                                    </BPRDailyAnalyticsTableCell>
                                    <BPRDailyAnalyticsTableCell>
                                        <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }} >
                                            {formatNumber(o.us)}
                                        </BPRDailyAnalyticsTableCellHeader>

                                    </BPRDailyAnalyticsTableCell>
                                    <BPRDailyAnalyticsTableCell>
                                        <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }} >
                                            {formatNumber(o.sc)}
                                        </BPRDailyAnalyticsTableCellHeader>

                                    </BPRDailyAnalyticsTableCell>
                                    <BPRDailyAnalyticsTableCell>
                                        <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }} >
                                            {formatNumber(o.ttl)}
                                        </BPRDailyAnalyticsTableCellHeader>

                                    </BPRDailyAnalyticsTableCell>
                                </BPRDailyAnalyticsTableRow>
                            )
                        })}
                    </BPRDailyAnalyticsTableRowContainer>

                </BPRDailyAnalyticsTableContainer>


            </BPRDailyAnalyticsContainer>
        </BPRDailyAnalyticsWrapper >

    )


}

export default DDQAnalytics;
