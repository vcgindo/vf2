import { useEffect, useState } from "react";
import ActionToolBar from "../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/MTOActionToolBar";
import useMaterialReq from './useMaterialRequirements';
import MaterialRequirementComponent from './MaterialRequirementComponent';
import OverlayLoader from '../../Common/Loader';
import useFilter from "../../../../../hooks/useFilter";
import { useGetFilterData } from "../../../../../VectorFlow/Services/MTO/Common/CommonFilter";
import { FilterPageName } from "../../Common/Enum";
import { useUserData } from "../../../../../context";

const APIFilterConfig = {
    filSecVisConfig: {
        "Proc_Material_Requirement" : {
            mjr : false,
            or: true,
            res: false,
            cus: false
        },
    }
};

const MaterialRequirement = () => {
    const [filterData, setFilterData] = useState({});
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
    } = useFilter(filterData, APIFilterConfig.filSecVisConfig.Proc_Material_Requirement);
    const { mutateAsync: getPageWiseFilterData, /*isLoading*/ } = useGetFilterData()
    const { 
        renderView, 
        toggleCurrentTab, 
        onDateChangeReq, 
        onDateSubmitReq, 
        date, 
        currentTab, 
        isMatReqLoading,
        isMatReqDayWiseLoading,
        isUpdateUserConfig,
        isGetUserConfig,
        handleResetClick,
        handleSaveClick, 
        onExcelExportClickReq
    } = useMaterialReq(appliedFilters);

    const getFilterData = async () => {
        try {
            const response = await getPageWiseFilterData({page_name: FilterPageName.Proc_Material_Requirement, release_date: date});
            setFilterData(response?.data.data);
        } catch (error) {
            console.error(error);
        }
    }
    
    useEffect(() => {
        getFilterData()
    }, []);


    const { user } = useUserData();
    const themeUi = user?.user?.theme_ui;

    return (
        <div style={{ display: "flex", flexDirection: "column", height: "100%", paddingBottom: "2rem" }}>
            {(isMatReqLoading || isMatReqDayWiseLoading || isUpdateUserConfig || isGetUserConfig) && (
                <OverlayLoader/>
            )}
            <ActionToolBar
                isReleaseDate
                themeUi={themeUi}
                isAddFilterButton
                isExcelExport
                comp={"MaterialRequirement"}
                onDateChange={onDateChangeReq}
                submitDate={() =>{ 
                    onDateSubmitReq()
                    getFilterData()
                }}
                onExcelExportClick = {onExcelExportClickReq}
                date={date}
                handleSaveClick={handleSaveClick}
                handleResetClick={handleResetClick}
                isFilterOpen={isFilterOpen}
                onAddFilter={onAddFilter}
                toggleFilter={toggleFilter}
                onApplyFilter={onApplyFilter}
                multiFilter={currFilter}
                setMultiFilter={setCurrFilter}
                onFilterRemove={onFilterRemove}
                isMfgSelected={isMfgSelected}

            />
            <MaterialRequirementComponent currentTab={currentTab} renderView={renderView} toggleCurrentTab={toggleCurrentTab} date={date} />
        </div>
    )
}

export default MaterialRequirement;


