import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/extend-expect';
import ChildrenColor from './ChildrenColor';
import { ICellRendererParams } from 'ag-grid-enterprise';

// Mock the styles module
jest.mock('./styles', () => ({
    ProcPlanningChildrenColor: (props: React.PropsWithChildren<any>) => <div data-testid="children-cell-renderer" {...props} />,
    ChildrenColorCellRenderer: (props: { value: string }) => <div data-testid="color-cell-renderer">{props.value}</div>
}));

describe('ChildrenColor Component', () => {
    const renderComponent = (clr: string) => {
        const params: ICellRendererParams = {
            data: { clr }
        } as ICellRendererParams;
        render(<ChildrenColor {...params} />);
    };

    it('renders the ChildrenColorCellRenderer with correct text', () => {
        const testColor = 'Red';
        renderComponent(testColor);

        const cellElement = screen.getByTestId('color-cell-renderer');
        expect(cellElement).toHaveTextContent(testColor);
    });

    it('renders the ProcPlanningChildrenColor component', () => {
        const testColor = 'Green';
        renderComponent(testColor);

        const containerElement = screen.getByTestId('children-cell-renderer');
        expect(containerElement).toBeInTheDocument();
    });
    it('renders the ProcPlanningChildrenColor component', () => {
        const testColor = 'Yellow';
        renderComponent(testColor);

        const containerElement = screen.getByTestId('children-cell-renderer');
        expect(containerElement).toBeInTheDocument();
    });
    it('renders the ProcPlanningChildrenColor component', () => {
        const testColor = 'Black';
        renderComponent(testColor);

        const containerElement = screen.getByTestId('children-cell-renderer');
        expect(containerElement).toBeInTheDocument();
    });
});
