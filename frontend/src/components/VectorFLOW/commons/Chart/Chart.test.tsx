import { render } from "@testing-library/react"
import Chart from ".";
import {ChartData} from '../../../../mock-data/MDM';


describe("It handles all Chart Interactions",()=>{
    it('Renders the Chart',()=>{
        render(<Chart type="bar" data={ChartData} />)
    })
})