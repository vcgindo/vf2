import { Allotment } from "allotment"
import React, { useEffect, useState } from "react"
import MTOActionToolBar from "../../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar"
import '../RMPMBufferTrends/style.css';
import { BTRAllomentSection, BTRTableWrapper, HorizontalViewWrapper } from "../RMPMBufferTrends/styles";
import ExpeditingMTA from "./MTAGraph/ExpeditingMTA";
import ExpeditingMTO from "./MTOGraph/ExpeditingMTO";
import { useGetDate } from '../../../../../Services/MTO/Production/InsightsAndTrends/RMPMExpediting/index';
import { useGetFilterData } from '../../../../../..//VectorFlow/Services/MTO/Common/CommonFilter';
import useFilter from '../../../../../../hooks/useFilter';
import { FilterPageName } from "../../../Common/Enum";
import { useUserData } from "../../../../../../context";


const APIFilterConfig = {
    filSecVisConfig: {
        "Proc_Expediting_RM_And_Suppliers" : {
            mjr : false,
            or: true,
            res: true,
            cus: true
        },
    }
};


const RMExpeditionSuppliers = () => {
    const [isMTO] = useState(true);
    const [supplierHorizon, setSupplierHorizon] = useState(14);
    const [rmHorizon, setRmHorizon] = useState(14);
    const [filterData, setFilterData] = useState({});
    const { mutateAsync: getPageWiseFilterData, /*isLoading*/ } = useGetFilterData()
    const { 
        state: currFilter, 
        setState: setCurrFilter, 
        onFilterRemove, 
        isFilterOpen, 
        isMfgSelected,
        onAddFilter, 
        onApplyFilter, 
        toggleFilter,
        appliedFilters
    } = useFilter(filterData, APIFilterConfig.filSecVisConfig.Proc_Expediting_RM_And_Suppliers);

    const { data, /*isLoading, refetch*/ } = useGetDate();
    
    const { user } = useUserData();
    const themeUi = user?.user?.theme_ui;
    const getFilterData = async () => {
        try {
            const response = await getPageWiseFilterData({
                page_name: FilterPageName.Proc_Expediting_RM_And_Suppliers,
                rm_horizon: rmHorizon,
                supplier_horizon: supplierHorizon
            });
            setFilterData(response?.data.data);
        } catch (error) {
            console.error(error);
        }
    }

    useEffect(()=>{
        getFilterData()
    },[])

    return (
        <div style={{ height: "90%", marginLeft: '20px' }}>
            <MTOActionToolBar 
                comp={"BTRMTO"} 
                themeUi = {themeUi}
                isAddFilterButton 
                isFilterOpen={isFilterOpen}
                onAddFilter={onAddFilter}
                toggleFilter={toggleFilter}
                onApplyFilter={onApplyFilter}
                multiFilter={currFilter}
                setMultiFilter={setCurrFilter}
                onFilterRemove={onFilterRemove}
                isMfgSelected={isMfgSelected}
            />
            <HorizontalViewWrapper>
                <BTRTableWrapper>
                    {
                        (isMTO) ?
                            (<Allotment
                                vertical={false}
                                separator={false}   >
                                <Allotment.Pane
                                    minSize={460}
                                    preferredSize={'50%'}>
                                    <BTRAllomentSection>
                                        <ExpeditingMTO
                                            getFilterData={getFilterData}
                                            rmHorizon={rmHorizon}
                                            setRmHorizon={setRmHorizon}
                                            isMTO={isMTO}
                                            date={data?.data?.data}
                                            appliedFilters={appliedFilters}
                                        />
                                    </BTRAllomentSection>
                                </Allotment.Pane>

                                <Allotment.Pane
                                    minSize={460}
                                    preferredSize={'50%'}>
                                    <BTRAllomentSection>
                                        <ExpeditingMTA
                                            getFilterData={getFilterData}
                                            supplierHorizon={supplierHorizon}
                                            setSupplierHorizon={setSupplierHorizon}
                                            isMTO={isMTO}
                                            date={data?.data?.data}
                                            appliedFilters={appliedFilters}
                                        />
                                    </BTRAllomentSection>
                                </Allotment.Pane>
                            </Allotment>)
                            :
                            <ExpeditingMTO
                                getFilterData={getFilterData}
                                rmHorizon={rmHorizon}
                                setRmHorizon={setRmHorizon}
                                isMTO={isMTO}
                                date={data?.data?.data}
                                appliedFilters={appliedFilters}
                            />
                    }
                </BTRTableWrapper>

            </HorizontalViewWrapper>
        </div>
    )
}

export default RMExpeditionSuppliers;