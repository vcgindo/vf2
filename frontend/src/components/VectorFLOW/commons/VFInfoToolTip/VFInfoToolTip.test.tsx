import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import VFInfoToolTip from './'

// Mock the Portal component
jest.mock('../../layouts/Portal', () => {
    return ({ children }:any) => {
        return <div data-testid="portal">{children}</div>
    }
})

describe('VFInfoToolTip', () => {
    const infoList = ["Info 1", "Info 2", "Info 3"]

    it('renders the info icon initially', () => {
        render(<VFInfoToolTip infoList={infoList} />)
        const infoIcon = screen.getByRole('img')
        expect(infoIcon).toBeInTheDocument()
        expect(infoIcon).toHaveAttribute('src', '/assets/img/VectorFLOW/BPR/info.svg')
    })

    it('opens the tooltip on clicking the info icon', () => {
        render(<VFInfoToolTip infoList={infoList} />)
        const infoIcon = screen.getByRole('img')
        
        // Click the info icon to open the tooltip
        fireEvent.click(infoIcon)
        
        // Check if the cancel icon is rendered
        const cancelIcon = screen.getByRole('img')
        expect(cancelIcon).toBeInTheDocument()
        expect(cancelIcon).toHaveAttribute('src', '/assets/img/VectorFLOW/BPR/cancel.svg')
        
        // Check if the tooltip is rendered with correct content
        const tooltip = screen.getByTestId('portal')
        expect(tooltip).toBeInTheDocument()
        infoList.forEach((info) => {
            expect(screen.getByText(info)).toBeInTheDocument()
        })
    })

    it('closes the tooltip on clicking the cancel icon', () => {
        render(<VFInfoToolTip infoList={infoList} />)
        const infoIcon = screen.getByRole('img')
        
        // Click the info icon to open the tooltip
        fireEvent.click(infoIcon)
        
        // Click the cancel icon to close the tooltip
        const cancelIcon = screen.getByRole('img')
        fireEvent.click(cancelIcon)
        
        // Check if the info icon is rendered again
        const infoIconAgain = screen.getByRole('img')
        expect(infoIconAgain).toBeInTheDocument()
        expect(infoIconAgain).toHaveAttribute('src', '/assets/img/VectorFLOW/BPR/info.svg')
        
        // Check if the tooltip is removed
        const tooltip = screen.queryByTestId('portal')
        expect(tooltip).not.toBeInTheDocument()
    })
})
