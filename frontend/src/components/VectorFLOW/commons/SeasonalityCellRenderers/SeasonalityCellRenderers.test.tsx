import { fireEvent, render, screen } from "@testing-library/react"
import { SeasonalityColorCellRenderer, SeasonalityGraphCellRenderer } from "."


describe("It handles all SeasonalityCellRenderers renders",()=>{
    it('Renders the graph renderer',()=>{
        render(<SeasonalityGraphCellRenderer onShowChart={jest.fn}/>)
        fireEvent.click(screen.getAllByTestId('graph-icon')[0])
    })

    it('Renders the color renderer',()=>{
        render(<SeasonalityColorCellRenderer data={{sts:'fasfas'}}/>)
    })
})