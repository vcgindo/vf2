
import {
    VFFloatingTabWrapper,
    VFFloatingTabButton,
    VFFloatingTabButtonActiveShadow
} from './styles'



const MTOFloatingTab = () => {



    return (
        <VFFloatingTabWrapper>
            <VFFloatingTabButton isActive={true}>
                Press
            </VFFloatingTabButton>
            <VFFloatingTabButtonActiveShadow/>
        </VFFloatingTabWrapper>
    )
}

export default MTOFloatingTab;