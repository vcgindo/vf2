
import { Dispatch, SetStateAction, useEffect } from "react";
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
import { ADD_MASTER , FILL_SELECTED_OPTIONS, REMOVE_MASTER, RESET_STATE, UPDATE_ACTIVE_MASTER, UPDATE_MASTER_CHECKED_STATUS } from "../../../../redux/actions/MDM";
import VFLoader from "../../commons/VFLoader";

interface SelectMasterProps {
    data: MDMMasterState[],
    options: Option[],
    selectedOptions: Option[],
    filterButtonStatus: number[],
    setFilterButtonStatus: Dispatch<SetStateAction<number[]>>
    themeUi: string,
    isLoading: boolean,
    handleSubmit: () => void
    canToggleMaster:boolean
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
        canToggleMaster
    }: SelectMasterProps) => {


useEffect(()=>{
    const masterIdsArray = getSelectedMasterValues();
    if(masterIdsArray.length > 0) {
        masterIdsArray.map((item:any)=>setFilterButtonStatus([...filterButtonStatus, item]))
    }
},[])
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

    function removeFromSelectedMaster(valueToRemove:any) {
        let currentUrl = window.location.href;
        const paramName = 'selectedMaster';

        const regex = new RegExp(`[?&]${paramName}=([^&]*)`);
        const match = currentUrl.match(regex);
        
        if (match) {
            let currentValues = match[1].split(',');
            currentValues = currentValues.filter(value => value !== valueToRemove);
            const newParamString = currentValues.length ? `${paramName}=${currentValues.join(',')}` : '';
    

            if (newParamString) {
                currentUrl = currentUrl.replace(regex, `${match[0][0]}${newParamString}`);
            } else {
                currentUrl = currentUrl.replace(regex, '');
                currentUrl = currentUrl.replace(/([?&])$/, '');
            }
    
            window.history.replaceState(null, '', currentUrl);
        }
    }

    function addToSelectedMaster(masterId:any) {
        const currentUrl = window.location.href;
        const paramName = 'selectedMaster';
       
        if (currentUrl.includes('/view-modify')) {
            const baseUrl = currentUrl.split('?')[0];
            let newUrl = currentUrl;
    
            const regex = new RegExp('/view-modify\\?' + paramName + '=([^&]*)');
            const match = currentUrl.match(regex);
    
            if (match) {
                let queryParams = match[1];
                if (!queryParams.split(',').includes(masterId)) {
                    queryParams += ',' + masterId;
                }
                newUrl = baseUrl + '?' + paramName + '=' + queryParams;
            } else {
                if (!currentUrl.includes('?')) {
                    newUrl = baseUrl + '?' + paramName + '=' + masterId;
                } else {
                    newUrl = baseUrl + window.location.search + '&' + paramName + '=' + masterId;
                }
            }
            window.history.replaceState(null, '', newUrl);
        }
    }
    
   

    const onClickFilterButton = (currMaster: MDMMasterState) => {

        if (getFilterButtonStatus(currMaster.id) && !canToggleMaster) {
            notifyError('You can only add new master')
            return
        }

        dispatch(FILL_SELECTED_OPTIONS([]));

        if (getFilterButtonStatus(currMaster.id) || masters.find((selectedMaster: MDMMasterState) => selectedMaster.id === currMaster.id)) {
            removeFromSelectedMaster(currMaster.id)
            setFilterButtonStatus(filterButtonStatus.filter((masterId: number) => masterId !== currMaster.id));
            dispatch(REMOVE_MASTER(currMaster.id))
        }
        else {
            addToSelectedMaster(currMaster.id);
            setFilterButtonStatus([...filterButtonStatus, currMaster.id]);
            dispatch(ADD_MASTER(currMaster));
        }
        if (masters?.length > 1)
            { 
                dispatch(UPDATE_ACTIVE_MASTER((0)))
            }
        else{
            dispatch(UPDATE_ACTIVE_MASTER({id:0,fields:[],filters:[],progress:'default',name:"",colDefs:[],rowData:[],isChecked:true}))
        }
    }

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
        dispatch(RESET_STATE());
        navigate('/mta/master-data-management/control-panel');
    }

    function getSelectedMasterValues() {
        const currentUrl = window.location.href;
        const paramName = 'selectedMaster';
        
        const regex = new RegExp(`[?&]${paramName}=([^&]*)`);
        const match = currentUrl.match(regex);
    
        if (match) {
            return match[1].split(',');
        }
        
        return [];
    }

    const isAnyMasterChecked = masters.length > 0 && masters.every(master => !master.isChecked);

    return (

        <Container style={{zoom:'var(--default-zoom)'}}>
            <Container style={{ flexDirection: 'row', gap: '44px' }}>
                <VFMasterFieldSearch
                    value={selectedOptions}
                    setValue={setValue}
                    options={options}
                    placeholder={'Select'}
                    handleListChild={() => { setFilterButtonStatus([]) }}
                    maxToShow={3}
                    backgroundColor={'#FFFFFF'}
                    disabled={false}
                />
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
                                marginBottom: '10px',
                                marginTop:'10px',
                            }}
                        >
                            {data?.map((master: MDMMasterState) => {
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