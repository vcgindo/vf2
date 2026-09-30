import { SaveDueDateWrapper } from "./styles";
import VFButtonOutline from '../../../../../components/VectorFLOW/commons/VFButtonOutline';
import { useUserData } from "../../../../../context/UserDataContext";

interface VFSaveDueDateProps {
    onSubmitDueDate: () => void;
    isDisabled?:boolean
}

const VFSave = (props: VFSaveDueDateProps) => {
    const {
        onSubmitDueDate,
        isDisabled
    } = props;

    const { user } = useUserData();
    const themeUi = user?.user?.theme_ui;

    return (
        <SaveDueDateWrapper style={{ margin: '1rem 0', padding: 0 }}>
            <VFButtonOutline 
                style={{ height: '30px', width: '159px', borderRadius: '4px', fontSize: '14px', fontWeight: '400', cursor: 'pointer' }} 
                themeUi={themeUi} 
                onClick={onSubmitDueDate}
                disabled = {isDisabled}
            >
                Save Due Date
            </VFButtonOutline>
        </SaveDueDateWrapper>
    );
};

export default VFSave;
