import React, { useMemo, useState } from 'react'
import {
    BPRDailyAnalyticsWrapper,
    BPRDailyAnalyticsContainer,
    BPRDailyAnalyticsHeader,
    BPRDailyAnalyticsTableContainer,
    BPRDailyAnalyticsTableHeaderContainer,
    BPRDailyAnalyticsTableHeader,
    BPRDailyAnalyticsTableRowContainer,
    BPRDailyAnalyticsTableRow,
    BPRDailyAnalyticsTableCell,
    BPRDailyAnalyticsTableCellHeader
} from './styles';

import { useGetReasonForPoogiAnalytics } from '../../../../../VectorFlow/Services/MTO/Poogi/ReasonOrderChange/index';


const ReasonsOrderAnalyticalScreen = () => {
    const { data, isLoading, /*refetch*/ } = useGetReasonForPoogiAnalytics();
    const analyticsData = useMemo(()=>{
        if(!data)return []
        return data?.data?.data
    },[isLoading])

    const [rowData] = useState([
        {
            headerName: 'Order\n Status',
        },
        {
            headerName: 'Unassigned'
        },
        {
            headerName: 'Assigned'
        },
        {
            headerName: 'Order\n Count'
        },
    ])


    if (!analyticsData) {
        return null;
    }

    if(isLoading){
        return null
    }

    return (
        <BPRDailyAnalyticsWrapper>
            <BPRDailyAnalyticsContainer>
                <BPRDailyAnalyticsHeader>
                    Analytics
                </BPRDailyAnalyticsHeader>

                <BPRDailyAnalyticsTableContainer>
                    <BPRDailyAnalyticsTableHeaderContainer style={{ wordWrap: 'break-word', borderTop: '1px white dashed', borderBottom: '1px dashed white' }}>
                        {rowData.map((data) => {
                            return (
                                <BPRDailyAnalyticsTableHeader>
                                    {data.headerName}
                                </BPRDailyAnalyticsTableHeader>
                            )
                        })
                        }
                    </BPRDailyAnalyticsTableHeaderContainer>
                </BPRDailyAnalyticsTableContainer>

                <BPRDailyAnalyticsTableRowContainer>

                    {/**for Closed */}
                    <BPRDailyAnalyticsTableRow style={{
                        height: 30,
                        boxShadow: 'none',
                        backgroundColor: 'transparent',
                        borderBottom: '1px white solid',
                        borderRadius: 0
                    }}>
                        <BPRDailyAnalyticsTableCell>
                            <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                Closed
                            </BPRDailyAnalyticsTableCellHeader>
                        </BPRDailyAnalyticsTableCell>

                        <BPRDailyAnalyticsTableCell>
                            <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                {analyticsData?.closed?.unassigned}
                            </BPRDailyAnalyticsTableCellHeader>
                        </BPRDailyAnalyticsTableCell>

                        <BPRDailyAnalyticsTableCell>
                            <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                {analyticsData.closed.assigned}
                            </BPRDailyAnalyticsTableCellHeader>
                        </BPRDailyAnalyticsTableCell>

                        <BPRDailyAnalyticsTableCell>
                            <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                {analyticsData.closed.total_count}
                            </BPRDailyAnalyticsTableCellHeader>
                        </BPRDailyAnalyticsTableCell>
                    </BPRDailyAnalyticsTableRow>

                    {/**for Open */}
                    <BPRDailyAnalyticsTableRow style={{
                        height: 30,
                        boxShadow: 'none',
                        backgroundColor: 'transparent',
                        borderBottom: '1px white solid',
                        borderRadius: 0
                    }}>
                        <BPRDailyAnalyticsTableCell>
                            <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                Open
                            </BPRDailyAnalyticsTableCellHeader>
                        </BPRDailyAnalyticsTableCell>

                        <BPRDailyAnalyticsTableCell>
                            <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                {analyticsData.open.unassigned}
                            </BPRDailyAnalyticsTableCellHeader>
                        </BPRDailyAnalyticsTableCell>

                        <BPRDailyAnalyticsTableCell>
                            <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                {analyticsData.open.assigned}
                            </BPRDailyAnalyticsTableCellHeader>
                        </BPRDailyAnalyticsTableCell>

                        <BPRDailyAnalyticsTableCell>
                            <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                {analyticsData.open.total_count}
                            </BPRDailyAnalyticsTableCellHeader>
                        </BPRDailyAnalyticsTableCell>

                    </BPRDailyAnalyticsTableRow>

                    <BPRDailyAnalyticsTableRow style={{
                        height: 30,
                        boxShadow: 'none',
                        backgroundColor: 'black',
                        borderRadius: 0
                    }}>

                        <BPRDailyAnalyticsTableCell>
                            <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                Total
                            </BPRDailyAnalyticsTableCellHeader>

                        </BPRDailyAnalyticsTableCell>
                        <BPRDailyAnalyticsTableCell>
                            <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                {analyticsData.closed.unassigned + analyticsData.open.unassigned}
                            </BPRDailyAnalyticsTableCellHeader>

                        </BPRDailyAnalyticsTableCell>
                        <BPRDailyAnalyticsTableCell>
                            <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                {Number(analyticsData.closed.assigned) + Number(analyticsData.open.assigned)}
                            </BPRDailyAnalyticsTableCellHeader>

                        </BPRDailyAnalyticsTableCell>
                        <BPRDailyAnalyticsTableCell>
                            <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }} >
                                {analyticsData.closed.total_count + analyticsData.open.total_count}
                            </BPRDailyAnalyticsTableCellHeader>

                        </BPRDailyAnalyticsTableCell>
                    </BPRDailyAnalyticsTableRow>


                </BPRDailyAnalyticsTableRowContainer>
            </BPRDailyAnalyticsContainer>
        </BPRDailyAnalyticsWrapper >
    )
}

export default ReasonsOrderAnalyticalScreen