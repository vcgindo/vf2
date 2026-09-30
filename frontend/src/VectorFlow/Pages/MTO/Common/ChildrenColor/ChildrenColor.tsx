import { ICellRendererParams } from "ag-grid-enterprise";
import Tooltip from "../Tooltip";
import { ProcPlanningChildrenColor, ChildrenColorCellRenderer, Tooltipcontainer } from "./styles";
import _ from "lodash";

const ChildrenColor = (props: ICellRendererParams) => {
    if (_.isEmpty(props.data)) {
        return <></>
    }

    let str = ''
    if (props.data.clr === 'Purple') {
        str = "Full Kit"
    }
    else if (props.data.clr === 'Orange') {
        str = "Partial Kit/No kit"
    }
    return (
        str !== ""?
        <Tooltip  tooltipZoom='1' style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }} content={<><Tooltipcontainer>{str}</Tooltipcontainer></>}>
            <ProcPlanningChildrenColor data-testid="children-cell-renderer">
                <ChildrenColorCellRenderer value={props.data.clr} 
            
                />
            </ProcPlanningChildrenColor>
        </Tooltip>
        : <ProcPlanningChildrenColor data-testid="children-cell-renderer">
                <ChildrenColorCellRenderer value={props.data.clr} />
        </ProcPlanningChildrenColor>
        
    );
};

export default ChildrenColor;



