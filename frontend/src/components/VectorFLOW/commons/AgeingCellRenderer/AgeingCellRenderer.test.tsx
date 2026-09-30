import { fireEvent, render, screen } from "@testing-library/react"
import { AgeingCellRenderer } from "."


describe("It handles all Ageing Cell Renderer renders",()=>{
    const cellData:any = {
        data: {
          AgeingOrder: 84,
          EcoPen: '30',
        },
      };
    it('Renders the Ageing renderer',()=>{
        render(<AgeingCellRenderer {...cellData}/>)
        fireEvent.mouseEnter(screen.getAllByTestId('ageing-warning-icon')[0])
        fireEvent.mouseLeave(screen.getAllByTestId('ageing-warning-icon')[0])
    })

    it('Renders the Ageing renderer',()=>{
        cellData.data = {EcoPen: '30',}
        render(<AgeingCellRenderer {...cellData}/>)
    })

})