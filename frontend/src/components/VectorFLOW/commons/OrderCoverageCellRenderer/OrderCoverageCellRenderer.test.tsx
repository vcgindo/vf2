import { render, screen } from "@testing-library/react"
import { OrderCoverageCellRenderer } from "."


describe("It handles all Ageing Cell Renderer renders",()=>{
    const cellData:any = {
        data: {
         c:'Gap > 67%'
        },
      };
    it('Renders the OrderCoverageCellRenderer renderer With Red Color for Gap > 67%',()=>{
        render(<OrderCoverageCellRenderer {...cellData}/>);
        const coverageColorBox = screen.getByTestId('coverage-color-box');
        expect(coverageColorBox).toHaveStyle('background-color:#9A0101');
    })
    it('Renders the OrderCoverageCellRenderer renderer With Yellow Color for 33% <= Gap <= 67%',()=>{
        cellData.data = {c:'33% <= Gap <= 67%'}
        render(<OrderCoverageCellRenderer {...cellData}/>);
        const coverageColorBox = screen.getByTestId('coverage-color-box');
        expect(coverageColorBox).toHaveStyle('background-color:#EBBF2B');
    })
    it('Renders the OrderCoverageCellRenderer renderer With Red Color for Gap < 33%',()=>{
        cellData.data = {c:'Gap < 33%'}
        render(<OrderCoverageCellRenderer {...cellData}/>);
        const coverageColorBox = screen.getByTestId('coverage-color-box');
        expect(coverageColorBox).toHaveStyle('background-color:#418D18');
    })

    it('Renders No Box for Empty String',()=>{
        cellData.data = {c:''}
        render(<OrderCoverageCellRenderer {...cellData}/>);
        const coverageColorBox = screen.getByTestId('coverage-color-box');
        expect(coverageColorBox).not.toHaveStyle('background-color:#418D18');
    })


})