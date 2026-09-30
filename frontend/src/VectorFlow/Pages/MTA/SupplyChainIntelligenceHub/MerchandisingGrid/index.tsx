import ChartView from "./ChartView"
import useMCGrid from "./useMCGrid"


const MCGrid = ()=>{

    const {
        gridData:data
    } = useMCGrid()

    return (
        <ChartView data={data}/>
    )
}

export default MCGrid