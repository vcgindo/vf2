
import { ICellRendererParams } from "ag-grid-enterprise"
// import Tooltip from "../../../../../components/VectorFLOW/commons/MTO/Tooltip"
import { BTRAvailabiltyCellRenderer } from "../../../../../VectorFlow/Pages/MTA/InsightsAndTrends/BTR/styles"
import { BTRAvailabiltyCellRendererWrapper } from "./FullKitAssignment.styled"
import { useUserData } from "../../../../../context";


const AvailabilityCellRenderer = (props: ICellRendererParams) => {
    const { user } = useUserData();

    const themeUi = user.user.theme_ui;
    return (

        <BTRAvailabiltyCellRendererWrapper data-testid="availability-cell-renderer">
            {/* <Tooltip content={<div style={{padding:"1rem"}}>{props.data.fka}/{props.data.oq} kits can be manufactured</div>} zoom={1} style={{display:"flex", alignItems:"center", height:"100%"}}> */}
            <BTRAvailabiltyCellRenderer value={props.value} themeUi={themeUi} />
            {/* </Tooltip> */}
        </BTRAvailabiltyCellRendererWrapper>

    )
}

export default AvailabilityCellRenderer