import { useSelector } from 'react-redux';
import { AnalyticsCol, AnalyticsRow, AnalyticsTable } from '../../../Procurement/InsightsAndTrends/DayWiseCoverage/style';


const ResourceUtilAnalytics = () => {

    const data = useSelector((state: any) => state.mto.ResourceUtilAnalytics)


    if (data === null || data === undefined || data.type === undefined || data.type === null) {
        return null;
    }



    if (data?.type === 'wip') {

        return (
            <AnalyticsTable style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }} >
                <thead>
                    <AnalyticsRow>
                        <AnalyticsCol style={{ display: 'flex', justifyContent: 'center' }}>WIP Analytics</AnalyticsCol>
                    </AnalyticsRow>
                    <hr />
                </thead>
                <tbody>
                    <AnalyticsRow style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <AnalyticsCol>Over Limit</AnalyticsCol>
                        <AnalyticsCol>{data.ol}</AnalyticsCol>

                    </AnalyticsRow>
                    <AnalyticsRow style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <AnalyticsCol>Under Limit</AnalyticsCol>
                        <AnalyticsCol>{data.ul}</AnalyticsCol>

                    </AnalyticsRow>
                    <hr />
                    <AnalyticsRow style={{ background: 'black', display: 'flex', justifyContent: 'space-between' }}>
                        <AnalyticsCol>Total</AnalyticsCol>
                        <AnalyticsCol>{data.ol + data.ul}</AnalyticsCol>

                    </AnalyticsRow>



                </tbody>
            </AnalyticsTable>
        )

    }
    else if (data?.type === 'util') {
        return (
            <AnalyticsTable style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }} >
                <thead>
                    <AnalyticsRow>
                        <AnalyticsCol style={{ display: 'flex', justifyContent: 'center' }}>Utilization Analytics</AnalyticsCol>
                    </AnalyticsRow>
                    <hr />
                </thead>
                <tbody>
                    <AnalyticsRow style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <AnalyticsCol>{'<60%'}</AnalyticsCol>
                        <AnalyticsCol>{data.sixty}</AnalyticsCol>

                    </AnalyticsRow>
                    <AnalyticsRow style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <AnalyticsCol>{'60% - 80%'}</AnalyticsCol>
                        <AnalyticsCol>{data.sixeight}</AnalyticsCol>

                    </AnalyticsRow>
                    <AnalyticsRow style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <AnalyticsCol>{'>80%'}</AnalyticsCol>
                        <AnalyticsCol>{data.eight}</AnalyticsCol>
                    </AnalyticsRow>
                    <hr />
                    <AnalyticsRow style={{ background: 'black', display: 'flex', justifyContent: 'space-between' }}>
                        <AnalyticsCol>Total</AnalyticsCol>
                        <AnalyticsCol>{data.sixty + data.eight + data.sixeight}</AnalyticsCol>

                    </AnalyticsRow>



                </tbody>
            </AnalyticsTable>
        )
    }

    return null;


}

export default ResourceUtilAnalytics