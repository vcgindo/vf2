import {DBMApplyNormButton} from "./styles"
import Checkbox from "../../../../../components/commons/Checkbox";

export const DBMApplyNormChange = (props:{onCheck:()=>void}) => {

    const {
        onCheck
    } = props

    const callTick = () => {
        onCheck();
    }

    return (
        <DBMApplyNormButton>

            <Checkbox onChange={callTick} name='' value="" defaultChecked={false}/>
            <p>Apply Selected Norms</p>
        </DBMApplyNormButton>
    )
}