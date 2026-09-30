
import { ICellRendererParams } from "ag-grid-enterprise"
import { AvailabiltyCellRenderer, AvailabiltyCellRendererWrapper } from './styles';
import { useUserData } from "../../../../../context";
import _ from "lodash";
const FullkitCellRenderer = (props: ICellRendererParams) => {

    const { user } = useUserData();
    const themeUi = user?.user?.theme_ui;

    const formatNumber = (num: any) => { 
        if (num >= 10000000) {
            return (num / 10000000).toFixed(2) + 'Cr';
        } else if (num >= 100000) {
            return (num / 100000).toFixed(2) + 'L'; 
        } else if (num >= 1000) {
            return (num / 1000).toFixed(2) + 'K'; 
        } else {
            return num.toFixed(2); 
        }
    };

    const FOLValue = props.value ?? props.data?.fol;

    if (FOLValue == null) {
        return <></>;
    }

    return (
        <AvailabiltyCellRendererWrapper data-testid="avl-cell-renderer">
            <div>{formatNumber(FOLValue)}</div> 
            <AvailabiltyCellRenderer value={FOLValue} themeUi={themeUi}/>     
        </AvailabiltyCellRendererWrapper>
    )
}

export default FullkitCellRenderer;
