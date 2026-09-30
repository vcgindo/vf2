
import { ICellRendererParams } from "ag-grid-enterprise";
import { AvailabiltyCellRenderer, AvailabiltyCellRendererWrapper } from './styles';
import { useUserData } from "../../../../../context";
const AvlCellRenderer = (props: ICellRendererParams) => {

    const { user } = useUserData();

    const formatNumber = (num: any) => {
        if (num >= 10000000) {
            return (num / 10000000).toFixed(1) + 'Cr';
        } else if (num >= 100000) {
            return (num / 100000).toFixed(1) + 'L'; 
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K'; 
        } else {
            return num; 
        }
    };
    const themeUi = user?.user?.theme_ui;
    return (
        <AvailabiltyCellRendererWrapper data-testid="avl-cell-renderer">
            <div>{formatNumber(props.data.fka)}</div>
            <AvailabiltyCellRenderer value={props.data.fkapr} themeUi={themeUi}/>
        </AvailabiltyCellRendererWrapper>
    )
}

export default AvlCellRenderer