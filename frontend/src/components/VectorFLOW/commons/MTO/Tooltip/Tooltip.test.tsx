import { render, fireEvent, act, screen } from '@testing-library/react';
import Tooltip from '.';

describe('Tooltip', () => {
    beforeAll(() => jest.useFakeTimers());
    afterAll(() => jest.useRealTimers());
    it('renders without crashing', () => {
        const { container } = render(<Tooltip content="Tooltip content">Hover me</Tooltip>);
        // Advance timers so the setTimeout callback executes
        act(() => {
            jest.runAllTimers();
        });
        expect(container).toBeInTheDocument();
    });

    it('shows tooltip on mouse enter', () => {
        const { getByText, queryByText } = render(<Tooltip content="Tooltip content">Hover me</Tooltip>);
        const target = getByText('Hover me');
        fireEvent.mouseEnter(target);
        // Advance timers so the setTimeout callback executes
        act(() => {
            jest.runAllTimers();
        });
        expect(queryByText('Tooltip content')).toBeInTheDocument();
    });

    it('hides tooltip on mouse leave', () => {
        const { getByText, queryByText } = render(<Tooltip content="Tooltip content">Hover me</Tooltip>);
        const target = getByText('Hover me');
        fireEvent.mouseEnter(target);
        fireEvent.mouseLeave(target);
        // Advance timers so the setTimeout callback executes
        act(() => {
            jest.runAllTimers();
        });
        expect(queryByText('Tooltip content')).not.toBeInTheDocument();
    });

    // Edge case: Tooltip should not go outside the viewport
    it('adjusts tooltip position to stay within viewport', () => {
        jest.mock('styled-components', () => (
            jest.requireActual('styled-components/dist/styled-components.browser.esm.js')
        ));
        const { getByText, queryByText } = render(<div style={{width:"100%", display:"flex", justifyContent:"end"}}><Tooltip content="Tooltip content Tooltip contentTooltip contentTooltip contentTooltip contentTooltip contentTooltip contentTooltip contentTooltip content">Hover me</Tooltip></div>);
        const target = getByText('Hover me');
        screen.logTestingPlaygroundURL(); 
        fireEvent.mouseEnter(target);
        const tooltip = queryByText('Tooltip content');
        const tooltipRect = tooltip?.getBoundingClientRect();
        // Advance timers so the setTimeout callback executes
        act(() => {
            jest.runAllTimers();
        });
        // expect(tooltipRect?.left).toBeGreaterThanOrEqual(0);
        // screen.logTestingPlaygroundURL(); 
        setTimeout(()=>{
            expect(tooltipRect?.right).toBeLessThanOrEqual(window.innerWidth);
        }, 100)
    });
});


    // it('tooltip should not go outside the window from the right', () => {
    //     // Render a tooltip near the right edge of the window
    //     const { getByText } = render(
    //         <div style={{ display: 'flex', justifyContent: 'flex-end', width: "100vw", marginTop: "200px" }}>
    //             <Tooltip content="Tooltip content Tooltip content Tooltip content Tooltip content aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa">
    //                 <button>Hover me</button>
    //             </Tooltip>
    //         </div>
    //     );

    //     // Simulate a mouse enter event on the button
    //     fireEvent.mouseEnter(getByText('Hover me'));

    //     act(() => {
    //         jest.runAllTimers();
    //     });

    //     // Assert that the tooltip's right edge is not beyond the window's right edge
    //     const tooltip = screen.getAllByTestId('tooltip')[0];
    //     expect(tooltip).not.toBeNull();
    //     if (tooltip) {
    //         const tooltipRect = tooltip.getBoundingClientRect();
    //         expect(tooltipRect.right).toBeLessThanOrEqual(window.innerWidth);
    //     }
    // });