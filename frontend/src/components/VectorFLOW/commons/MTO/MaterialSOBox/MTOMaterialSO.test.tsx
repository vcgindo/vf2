import React from 'react';
import { render } from '@testing-library/react';
import MTOMaterialSO from './MTOMaterialSO'; // Adjust the import path based on your file structure

// Mock the Tooltip component since it's used within MTOMaterialSO
jest.mock('../../../../../VectorFLOW/Pages/MTO/Common/Tooltip', () => {
  return function MockedTooltip({ content }: { content: React.ReactNode }) {
    return <div data-testid="tooltip">{content}</div>;
  };
});

describe('MTOMaterialSO Component', () => {
  test('renders with Red colors and Tooltips', () => {
    const colors = {
      c1: '#000',
      c2: '#E53F40',
      c3: '#EBBF2B'
    };

    const ToolTipdata = {
      p1: 50,
      c1: 'SomeValue1',
      p2: 75,
      c2: 'SomeValue2',
      p3: 25,
      c3: 'SomeValue3'
    };

    const { getByText, getByAltText, getAllByTestId } = render(
      <MTOMaterialSO
        kit="No Kit"
        colors={colors}
        height="20px"
        text="Sample Text"
        orderCount={10}
        cutCount={5}
        orderValue={100}
        percent={0.5}
        ToolTipdata={ToolTipdata}
      />
    );

    // Assert that Tooltip with 'Red' content is rendered
    expect(getAllByTestId('tooltip')[0]).toHaveTextContent('Black');
    expect(getAllByTestId('tooltip')[0]).toHaveTextContent('Red');
    expect(getByText('Black')).toBeInTheDocument();
    expect(getByText('Red')).toBeInTheDocument();

    // Assert that images are rendered based on kit prop
    expect(getByAltText('Logo')).toBeInTheDocument();
  });

  test('renders with Green color and Tooltip', () => {
    const colors = {
      c1: '#418D18'
    };

    const ToolTipdata = {
      p1: 60,
      c1: 'SomeValue1'
    };

    const { getByText, getAllByTestId } = render(
      <MTOMaterialSO
        kit="Partial Kit"
        colors={colors}
        height="20px"
        text="Another Text"
        orderCount={8}
        cutCount={3}
        orderValue={80}
        percent={0.6}
        ToolTipdata={ToolTipdata}
      />
    );

    // Assert that Tooltip with 'Green' content is rendered
    expect(getAllByTestId('tooltip')[0]).toHaveTextContent('Green');
    expect(getByText('Green')).toBeInTheDocument();
  });

  test('renders with Blue color and Tooltip', () => {
    const colors = {
      c1: '#003366'
    };

    const ToolTipdata = {
      p1: 75,
      c1: 'SomeValue1'
    };

    const { getByText, getAllByTestId } = render(
      <MTOMaterialSO
        kit="Full Kit"
        colors={colors}
        height="20px"
        text="Different Text"
        orderCount={15}
        cutCount={7}
        orderValue={150}
        percent={0.75}
        ToolTipdata={ToolTipdata}
      />
    );

    // Assert that Tooltip with 'Blue' content is rendered
    expect(getAllByTestId('tooltip')[0]).toHaveTextContent('Blue');
    expect(getByText('Blue')).toBeInTheDocument();
  });

  // Add more test cases as needed for different scenarios and edge cases
});