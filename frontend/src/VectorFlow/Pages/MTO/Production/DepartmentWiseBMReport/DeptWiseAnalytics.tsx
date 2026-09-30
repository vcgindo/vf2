
import { ColDef } from 'ag-grid-enterprise'
import React, { useMemo, useState } from 'react'
import { BMReportAnaytics } from './helper';
import { useSelector } from 'react-redux';

import {
    BPRDailyAnalyticsHeader,
    BPRDailyAnalyticsContainer,
    BPRDailyAnalyticsTableCell,
    BPRDailyAnalyticsTableContainer,
    BPRDailyAnalyticsTableHeader,
    BPRDailyAnalyticsTableHeaderContainer,
    BPRDailyAnalyticsTableRow,
    BPRDailyAnalyticsTableRowContainer,
    BPRDailyAnalyticStatusBar,
    BPRDailyAnalyticsWrapper,
    BPRDailyAnalyticsTableChangeIcon,
    BPRDailyAnalyticsTableNoChangeWrapper,
    BPRDailyAnalyticStatusBarSection,
    BPRDailyAnalyticsTableCellHeader,
    BPRDailyAnalyticsTableCellText,
} from './styles'
import Tooltip from '../../Common/Tooltip';


const DeptWiseAnalytics = () => {


    // const user = useUserData();
    // const themeUi = user.user.theme_ui;
    const [isLoading] = useState<boolean>(false);

    const rowData = useSelector((state: any)=> state.mto.BMReportAnalytics);


    const colHeaders: any = [
        { headerName: 'color' },
        { headerName: 'Procurement' },
        { headerName: 'Production' }
    ];

    // const rowData: any = [
    //     {
    //         color: 'black',
    //         ProcCount: 100,
    //         ProcPer: 20,
    //         ProdCount: 80,
    //         ProdPer: 15,
    //         ProcValue: -10,
    //         ProdValue: 20
    //     },
    //     {
    //         color: 'red',
    //         ProcCount: 100,
    //         ProcPer: 20,
    //         ProdCount: 80,
    //         ProdPer: 15,
    //         ProcValue: -10,
    //         ProdValue: 10
    //     },
    //     {
    //         color: 'yellow',
    //         ProcCount: 100,
    //         ProcPer: 20,
    //         ProdCount: 80,
    //         ProdPer: 15,
    //         ProcValue: 10,
    //         ProdValue: -5
    //     },
    //     {
    //         color: 'green',
    //         ProcCount: 100,
    //         ProcPer: 20,
    //         ProdCount: 80,
    //         ProdPer: 15,
    //         ProcValue: 0,
    //         ProdValue: 0

    //     },
    //     {
    //         color: 'blue',
    //         ProcCount: 100,
    //         ProcPer: 20,
    //         ProdCount: 80,
    //         ProdPer: 15,
    //         ProcValue: -2,
    //         ProdValue: -2
    //     },
    //     {
    //         color: 'white',
    //         ProcCount: 100,
    //         ProcPer: 20,
    //         ProdCount: 80,
    //         ProdPer: 15,
    //         ProcValue: 2,
    //         ProdValue: -2
    //     }

    // ]


    const summation = useMemo(()=>{
        let total = 0
        rowData?.forEach((row: any)=>{
            total += (row.ProcCount + row.ProdCount) ;
        })
        return total;
    }, [])


    const getCellIcons = (value: BMReportAnaytics) => {
        if (value == BMReportAnaytics.INCREASE) {
            return <BPRDailyAnalyticsTableChangeIcon src='/assets/img/VectorFLOW/BPR/analytics-increase.svg' />
        }
        
        if (value == BMReportAnaytics.DECREASE) {
            return <BPRDailyAnalyticsTableChangeIcon src='/assets/img/VectorFLOW/BPR/analytics-decrease.svg' style={{ transform: 'rotate(90deg)' }} />
        }

        if(value == BMReportAnaytics.INCREASE_DECREASE){
            return (
                <BPRDailyAnalyticsTableNoChangeWrapper>
                    <BPRDailyAnalyticsTableChangeIcon src='/assets/img/VectorFLOW/BPR/analytics-increase.svg' />
                    <BPRDailyAnalyticsTableChangeIcon src='/assets/img/VectorFLOW/BPR/analytics-decrease.svg' style={{ transform: 'rotate(90deg)' }} />
                </BPRDailyAnalyticsTableNoChangeWrapper>
            )
        } 

        if(value == BMReportAnaytics.DECREASE_INCREASE){
            return (
                <BPRDailyAnalyticsTableNoChangeWrapper>
                    <BPRDailyAnalyticsTableChangeIcon src='/assets/img/VectorFLOW/BPR/analytics-decrease.svg' style={{ transform: 'rotate(90deg)' }} />
                    <BPRDailyAnalyticsTableChangeIcon src='/assets/img/VectorFLOW/BPR/analytics-increase.svg' />
                </BPRDailyAnalyticsTableNoChangeWrapper>
            )
        }
    }



    if (isLoading) {
        return (
            <BPRDailyAnalyticsWrapper>
                <BPRDailyAnalyticsContainer style={{ aspectRatio: '0.9', width: '90%' }}>
                    <BPRDailyAnalyticsHeader  >
                        Analytics (For all orders)
                    </BPRDailyAnalyticsHeader>
                    <div style={{ width: '100%', height: '100%', display: 'grid', placeItems: 'center' }}>
                        <p style={{ color: 'white' }}>________</p>
                    </div>
                </BPRDailyAnalyticsContainer>
            </BPRDailyAnalyticsWrapper>
        )
    }

    if (!rowData || !Array.isArray(rowData) || rowData.length === 0) {
        return (
            <BPRDailyAnalyticsWrapper>
                <BPRDailyAnalyticsContainer style={{ aspectRatio: '0.9', width: '90%' }}>
                    <BPRDailyAnalyticsHeader  >
                        Analytics (For all orders)
                    </BPRDailyAnalyticsHeader>
                    <div style={{ width: '100%', height: '100%', display: 'grid', placeItems: 'center' }}>
                        <p style={{ color: 'white' }}>No data</p>
                    </div>
                </BPRDailyAnalyticsContainer>
            </BPRDailyAnalyticsWrapper>
        )
    }



    return (
        <BPRDailyAnalyticsWrapper>
            <BPRDailyAnalyticsContainer  >
                <BPRDailyAnalyticsHeader  >
                    Analytics (For all orders)
                </BPRDailyAnalyticsHeader>
                <BPRDailyAnalyticsTableContainer>
                    <BPRDailyAnalyticsTableHeaderContainer>
                        {
                            colHeaders.map((colDef: ColDef) => {
                                if (colDef.headerName === 'color') {
                                    return (
                                        <BPRDailyAnalyticsTableHeader style={{ width: 33 }} />
                                    )
                                }
                                return (
                                    <BPRDailyAnalyticsTableHeader>
                                        {colDef.headerName}
                                    </BPRDailyAnalyticsTableHeader>
                                )
                            })
                        }
                    </BPRDailyAnalyticsTableHeaderContainer>
                    <BPRDailyAnalyticsTableRowContainer>
                        {rowData.map((row: any) => {
                            return (
                                <BPRDailyAnalyticsTableRow>
                                    {Object.keys(row).map((key: string) => {
                                        if (key === 'color') {
                                            return (
                                                <BPRDailyAnalyticsTableCell style={{ backgroundColor: row[key], width: 60, boxShadow: "0px 3px 12px #AFAFAF" }} />
                                            )
                                        }
                                        if (key == 'ProcCount') {
                                            return (
                                                <React.Fragment>
                                                    <BPRDailyAnalyticsTableCell>
                                                        <BPRDailyAnalyticsTableCellHeader>{row.ProcCount}</BPRDailyAnalyticsTableCellHeader>
                                                        <BPRDailyAnalyticsTableCellText>{row.ProcPer + '%'}</BPRDailyAnalyticsTableCellText>
                                                    </BPRDailyAnalyticsTableCell>
                                                    <BPRDailyAnalyticsTableCell>
                                                        <Tooltip content={<div style={{padding:"0.5rem 1rem", fontSize:"12px"}}>{row.ProcPer}%</div>} tooltipZoom={1}>
                                                            {getCellIcons(row.ProcValue)}
                                                        </Tooltip>
                                                    </BPRDailyAnalyticsTableCell>
                                                </React.Fragment>
                                            )
                                        }
                                        if (key === 'ProdCount') {
                                            return (
                                                <React.Fragment>
                                                    <BPRDailyAnalyticsTableCell>
                                                        <BPRDailyAnalyticsTableCellHeader>{row.ProdCount}</BPRDailyAnalyticsTableCellHeader>
                                                        <BPRDailyAnalyticsTableCellText>{row.ProdPer + '%'}</BPRDailyAnalyticsTableCellText>
                                                    </BPRDailyAnalyticsTableCell>
                                                    <BPRDailyAnalyticsTableCell>
                                                    <Tooltip content={<div style={{padding:"0.5rem 1rem", fontSize:"12px"}}>{row.ProdPer}%</div>} tooltipZoom={1}>
                                                        {getCellIcons(row.ProdValue)}
                                                    </Tooltip>
                                                    </BPRDailyAnalyticsTableCell>
                                                </React.Fragment>
                                            )
                                        }
                                    })}
                                </BPRDailyAnalyticsTableRow>
                            )
                        })}
                    </BPRDailyAnalyticsTableRowContainer>
                </BPRDailyAnalyticsTableContainer>
                <BPRDailyAnalyticStatusBar style={{margin:"0 1rem"}}>
                    <BPRDailyAnalyticStatusBarSection>
                        Total
                    </BPRDailyAnalyticStatusBarSection>
                    <BPRDailyAnalyticStatusBarSection>
                        {summation}
                    </BPRDailyAnalyticStatusBarSection>
                </BPRDailyAnalyticStatusBar>
            </BPRDailyAnalyticsContainer>
        </BPRDailyAnalyticsWrapper>
    )
}

export default DeptWiseAnalytics