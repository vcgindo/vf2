import React, { useState } from 'react';
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
} from './DynamicReleaseManagement.styled'
// import { useSelector } from 'react-redux';
// import { RootState } from '../../../../../../redux/store/store';
import { formatNumber } from '../../Procurement/MaterialCoverage/CommonFunc';


const DRMAnalytics = () => {

    const options = {
        "Order": [
            {
                "ccr": 'OverLimit',
                "RMS": 29,
                "RMT": 67,
                "others": 0,
                "count": 96,
            },
            {
                "ccr": 'UnderLimit',
                "RMS": 29,
                "RMT": 91,
                "others": 0,
                "count": 146,
            },
            {
                "ccr": 'Balanced',
                "RMS": 45,
                "RMT": 19,
                "others": 0,
                "count": 110,
            }
        ]
    }

    const [rowData] = useState([
        {
            headerName: 'CCR',
        },
        {
            headerName: 'RM In-Stock'
        },
        {
            headerName: 'RM In-Transit'
        },
        {
            headerName: 'Others'
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
                <BPRDailyAnalyticsHeader>
                    Analytics
                </BPRDailyAnalyticsHeader>

                <BPRDailyAnalyticsTableContainer>
                    <BPRDailyAnalyticsTableHeaderContainer style={{ borderTop: '1px dashed white', borderBottom: '1px dashed white' }}>
                        {rowData.map((data) => {
                            return (
                                <BPRDailyAnalyticsTableHeader>
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
                                    borderBottom: o.ccr === 'Balanced' ? '' : '1px white solid',
                                    borderRadius: 0
                                }}>

                                    <BPRDailyAnalyticsTableCell>
                                        <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                            {o.ccr}
                                        </BPRDailyAnalyticsTableCellHeader>

                                    </BPRDailyAnalyticsTableCell>
                                    <BPRDailyAnalyticsTableCell>
                                        <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                            {formatNumber(o.RMS)}
                                        </BPRDailyAnalyticsTableCellHeader>

                                    </BPRDailyAnalyticsTableCell>
                                    <BPRDailyAnalyticsTableCell>
                                        <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                            {formatNumber(o.RMT)}
                                        </BPRDailyAnalyticsTableCellHeader>

                                    </BPRDailyAnalyticsTableCell>
                                    <BPRDailyAnalyticsTableCell>
                                        <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }}>
                                            {formatNumber(o.others)}
                                        </BPRDailyAnalyticsTableCellHeader>

                                    </BPRDailyAnalyticsTableCell>
                                    <BPRDailyAnalyticsTableCell>
                                        <BPRDailyAnalyticsTableCellHeader style={{ color: 'white' }} >
                                            {formatNumber(o.count)}
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

export default DRMAnalytics