import { VFMasterCardContainer, VFMasterCardHeader, VFMasterCardListContainer, VFMasterCardListItem,VFMasterCardCheckBox } from "./styles"
import {type Master, type Field} from '../../../../VectorFlow/types/MDM';

interface VFMasterCardProps{
    data:Master
    selectedFields:string[],
    isSelected:boolean,
    onSelectCheckbox:any,
    isCheckBoxDisabled:boolean,
    themeUi:string,


}

const VFMasterCard = (props:VFMasterCardProps)=>{
    
    // const [checked,setChecked] = useState(false)
    //     const handleOnChange = () => {
    //         setChecked(!checked)
    //     }

    const {
        data,
        selectedFields,
        isSelected,
        onSelectCheckbox,
        isCheckBoxDisabled,
        themeUi,


    } = props

    return(
        <VFMasterCardContainer data-testid='master-card'>
            <VFMasterCardHeader>
                {data.name}
                {!isCheckBoxDisabled &&
                    <VFMasterCardCheckBox themeUi={themeUi} type='checkbox' data-testid="check-box"
                    checked={isSelected}
                    onChange={onSelectCheckbox}
                 />}
            </VFMasterCardHeader>
            <VFMasterCardListContainer data-testid='list-container'>
                {data.fields.map((title:Field,index)=>{
                    return title.visible && <VFMasterCardListItem themeUi={themeUi} key={index} isSelected={selectedFields.includes(title.displayName)}>{title.displayName}</VFMasterCardListItem>
                })}
            </VFMasterCardListContainer>
        </VFMasterCardContainer>
    )
}

export default VFMasterCard