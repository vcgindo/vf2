import React from 'react';
import { SaveRemarkWrapper } from "./styles";
import VFButtonOutline from '../VFButtonOutline';
import { useUserData } from "../../../../context/UserDataContext";

interface VFSaveRemarkProps {
    onSubmitRemarks: () => void;
    isDisabled?:boolean
}

const VFSaveRemark = (props: VFSaveRemarkProps) => {
    const {
        onSubmitRemarks,
        isDisabled
    } = props;

    const { user } = useUserData();
    const themeUi = user?.user?.theme_ui;


    return (
        <SaveRemarkWrapper style={{ margin: '1rem 0', padding: 0 }}>
            <VFButtonOutline 
                style={{ height: '30px', width: '159px', borderRadius: '4px', fontSize: '14px', fontWeight: '400', cursor: 'pointer' }} 
                themeUi={themeUi} 
                onClick={onSubmitRemarks}
                disabled = {isDisabled}
            >
                Save Remark
            </VFButtonOutline>
        </SaveRemarkWrapper>
    );
};

export default VFSaveRemark;
