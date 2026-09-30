import { fireEvent, render, screen } from "@testing-library/react"
import VFErrorFallBack from "."


describe('VFErrorFallBack Componenet',()=>{
    
    it("Should render on the dom",()=>{
        render(<VFErrorFallBack/>)
    })

    it('Clicks on Go Home button',()=>{
        render(<VFErrorFallBack/>)
        const btn = screen.getByText('Go back to home')
        fireEvent.click(btn)
    })

    it('Clicks on Refresh button',()=>{
        render(<VFErrorFallBack/>)
        const btn = screen.getByText('Refresh Now')
        fireEvent.click(btn)
    })
    // it('Clicks on Go Contact Support button',()=>{
    //     render(<VFErrorFallBack/>)
    //     const btn = screen.getByText('Contact Support')
    //     fireEvent.click(btn)
    // })
})