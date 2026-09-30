
import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/extend-expect';
import ColorPriority from './index';
import { ICellRendererParams } from 'ag-grid-enterprise';

// Mock the styles module
jest.mock('./styles', () => ({
    ColorPriorityCellRendererWrapper: (props: React.PropsWithChildren<any>) => <div data-testid="cp-cell-renderer" {...props} />,
    ColorPriorityCellRenderer: (props: any) => <div data-testid="color-priority-cell-renderer" style={{ background: `linear-gradient(to right, ${props.B}%, ${props.R}%, ${props.Y}%, ${props.G}%, ${props.W}%, ${props.Bl}%)` }} />
}));

describe('ColorPriority Component', () => {
    const renderComponent = (colorValues: any) => {
        const params: ICellRendererParams = {
            data: { cp: [colorValues] }
        } as ICellRendererParams;
        render(<ColorPriority {...params} />);
    };

    it('renders the ColorPriorityCellRenderer with correct gradient for given colors', () => {
        const testColorValues = { B: 20, R: 20, Y: 20, G: 20, W: 20, Bl: 0 };
        renderComponent(testColorValues);

        const cellElement = screen.getByTestId('color-priority-cell-renderer');
        expect(cellElement).toHaveStyle('background: linear-gradient(to right, 20%, 20%, 20%, 20%, 20%, 0%)');
    });

    it('renders the ColorPriorityCellRenderer with correct gradient for no color values', () => {
        const testColorValues = { B: 30, R: 70, Y: 0, G: 0, W: 0, Bl: 0 };
        renderComponent(testColorValues);

        const cellElement = screen.getByTestId('color-priority-cell-renderer');
        expect(cellElement).toHaveStyle('background: linear-gradient(to right, 30%, 70%, 0%, 0%, 0%, 0%)');
    });

    it('renders the ColorPriorityCellRendererWrapper component', () => {
        const testColorValues = { B: 10, R: 10, Y: 10, G: 10, W: 10, Bl: 50 };
        renderComponent(testColorValues);
        const wrapperElement = screen.getByTestId('cp-cell-renderer');
        expect(wrapperElement).toBeInTheDocument();
    });
});
