
import { ICellRendererParams } from "ag-grid-enterprise"

import { BTRAvailabiltyCellRenderer, BTRAvailabiltyCellRendererWrapper } from './styles'
import { useUserData } from "../../../../../context";
const AvailabilityCellRenderer = (props: ICellRendererParams) => {
    const { user } = useUserData();

    const themeUi = user.user.theme_ui;
    
    return (
        <BTRAvailabiltyCellRendererWrapper data-testid="availability-cell-renderer">
            <BTRAvailabiltyCellRenderer value={props.value} themeUi={themeUi} />
        </BTRAvailabiltyCellRendererWrapper>
    )
}

export default AvailabilityCellRenderer