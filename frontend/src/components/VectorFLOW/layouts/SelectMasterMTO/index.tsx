
import { Dispatch, SetStateAction } from "react";
import { Container, QuickFilterHeader, SCButtonContainer, SCCardContainer } from "./styles"

import VFMasterCard from "../../commons/VFMasterCard";
import VFMasterFieldSearch from "../../commons/VFMasterFieldSearch";
import ButtonOutlineStatus from "../../../commons/ButtonOutline/button";
import VFButton from "../../commons/VFButton";
import VFButtonOutline from "../../commons/VFButtonOutline";
import { useNavigate } from "react-router";
import { type MDMMasterState, type Option } from "../../../../VectorFlow/types/MDM";
import { useDispatch, useSelector } from 'react-redux';
import { notifyError } from "../../../../helpers/notify";
import { RootState } from "../../../../redux/store/store";
import { ADD_MASTER, FILL_SELECTED_OPTIONS, REMOVE_MASTER, RESET_STATE, UPDATE_MASTER_CHECKED_STATUS } from "../../../../redux/actions/MDM";
import VFLoader from "../../commons/VFLoader";
import { RESET_MTO_STATE } from "../../../../redux/actions/MTO";

interface SelectMasterProps {
    data: MDMMasterState[],
    options: Option[],
    selectedOptions: Option[],
    filterButtonStatus: number[],
    setFilterButtonStatus: Dispatch<SetStateAction<number[]>>
    themeUi: string,
    isLoading: boolean,
    handleSubmit: () => void
}

const SelectMaster = (
    {
        data,
        options,
        selectedOptions,
        filterButtonStatus,
        setFilterButtonStatus,
        themeUi,
        isLoading,
        handleSubmit,
    }: SelectMasterProps) => {



    const navigate = useNavigate();
    const dispatch = useDispatch();
    const masters = useSelector((state: RootState) => state.mdm.masters);
    const activeMaster = useSelector((state: RootState) => state.mdm.activeMaster);

    const toggledFromAddMaster = () => {
        return masters.length > 0 && activeMaster.id !== 0;
    }


    if (isLoading) {
        return (
            <VFLoader />
        )
    }

    const onClickFilterButton = (currMaster: MDMMasterState) => {
        if (getFilterButtonStatus(currMaster.id) && toggledFromAddMaster()) {
            notifyError('You can only add new master');
            return;
        }
    
        dispatch(FILL_SELECTED_OPTIONS([]));
    
        const isAlreadySelected = filterButtonStatus.includes(currMaster.id);
    
        if (isAlreadySelected) {
            setFilterButtonStatus([]);
            dispatch(REMOVE_MASTER(currMaster.id));
        } else {
            setFilterButtonStatus([currMaster.id]);
    
            masters.forEach((m: MDMMasterState) => {
                dispatch(REMOVE_MASTER(m.id));
            }); 
    
            dispatch(ADD_MASTER(currMaster));
        }
    };
    
    

    const getFilterButtonStatus = (masterId: number) => {
        return (filterButtonStatus.find((id: number) => id === masterId) || masters.find((master: MDMMasterState) => master.id === masterId)) ? true : false;
    }

    const setValue = (options: any) => {
        // if(options.length===0) {
        //     setFilterButtonStatus([])
        // }
        dispatch(FILL_SELECTED_OPTIONS(options))
    }

    const onCancel = () => {
        dispatch(RESET_MTO_STATE());
        dispatch(RESET_STATE());
        navigate('/mto/master-data-management/control-panel');
    }

    const isAnyMasterChecked = masters.length > 0 && masters.every(master => !master.isChecked);

    return (

        <Container style={{paddingTop: '15px'}} >
            <Container style={{ flexDirection: 'row', gap: '44px' }}>
                {/* <VFMasterFieldSearch
                    value={selectedOptions}
                    setValue={setValue}
                    options={options}
                    placeholder={'Select'}
                    handleListChild={() => { setFilterButtonStatus([]) }}
                    maxToShow={3}
                    backgroundColor={'#FFFFFF'}
                    disabled={toggledFromAddMaster()}
                /> */}
                <Container style={{ flexDirection: 'row' }}>
                    <QuickFilterHeader>
                        Quick Filters -
                    </QuickFilterHeader>
                    <div style={{ flexDirection: 'row' }}>
                        <Container
                            style={{
                                flexDirection: 'row',
                                flexWrap: 'wrap',
                                maxWidth: '900px',
                                gap: '10px',
                                marginBottom: '10px'
                            }}
                        >
                            {data?.map((master: MDMMasterState) => {
                                if (master.isMTO) {
                                    return (
                                        <ButtonOutlineStatus
                                            status={getFilterButtonStatus(master.id)}
                                            text={master.name}
                                            onChange={() => onClickFilterButton(master)}
                                            icon=''
                                            key={master.id}
                                            style={{ fontSize: '13px', fontFamily: 'Roboto', letterSpacing: '0px', fontWeight: 400, lineHeight: '15px', width: 'auto', minWidth: '90px' }}
                                        />
                                    )
                                }
                            })}
                        </Container>
                    </div>
                </Container>
            </Container>

            <SCCardContainer>
                {(masters.length > 0 ? masters : data).map((item: MDMMasterState) => {
                    return (
                        <VFMasterCard
                            themeUi={themeUi}
                            isSelected={(item.isChecked) && (selectedOptions.length > 0)}
                            onSelectCheckbox={() => { if (toggledFromAddMaster()) notifyError("You can add only new Masters!"); else dispatch(UPDATE_MASTER_CHECKED_STATUS(item.id)) }}
                            data={item}
                            key={item.id}
                            selectedFields={selectedOptions.map((s: Option) => s.label)}
                            isCheckBoxDisabled={filterButtonStatus.length > 0 || masters.length === 0}
                        />
                    )
                })}
            </SCCardContainer>

            <SCButtonContainer>

                <VFButtonOutline
                    onClick={onCancel}
                    themeUi={themeUi}
                    width={141}
                    disabled={false}>
                    Cancel
                </VFButtonOutline>
                <VFButton
                    onClick={() => { handleSubmit() }}
                    themeUi={themeUi}
                    width={141}
                    disabled={masters.length === 0 || isAnyMasterChecked}>
                    Submit
                </VFButton>

            </SCButtonContainer>

        </Container>
    )
}

export default SelectMaster;