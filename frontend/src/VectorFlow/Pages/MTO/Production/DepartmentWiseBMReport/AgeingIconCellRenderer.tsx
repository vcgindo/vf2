//import { CustomCellRendererProps } from "@ag-grid-community/react";
import _ from "lodash";
import { FlatIcon1 } from "./styles";


const ActionCellRenderer = (props: any) => {

    return (
        !_.isEmpty(props.data) && props.data?.ha &&
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <FlatIcon1
                title="High Ageing"
            //src={"/assets/img/mto/DeptWiseBmReport/exclamatory.svg"}
            />
        </div>
    )

}

export default ActionCellRenderer;
