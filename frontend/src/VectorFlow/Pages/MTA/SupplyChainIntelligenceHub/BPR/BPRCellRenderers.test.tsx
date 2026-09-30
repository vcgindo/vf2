import { render, screen } from '@testing-library/react';
import {
  BPRTechColorCellRenderer,
  BPREcoColorCellRenderer,
  BPRTagsCellRenderer,
} from './BPRCellRenderers';

describe('Test BPRTechColorCellRenderer Component', () => {
  it('renders cell with correct text and color', () => {
    const cellData = {
      data: {
        TechColor: 'Green',
        TechPen: '50',
      },
    };

    render(<BPRTechColorCellRenderer {...cellData} />);

    const cellElement = screen.getByText('50%')
    expect(cellElement).toHaveTextContent('50%');
    expect(cellElement).toHaveStyle({ backgroundColor: '#418D18', color: 'white' });
  });
  it('renders cell with correct all colors', () => {
    const cellData = [
        {
            data: {
              TechPen: '30',
            },
          },
          {
            data: {
              TechColor: 'White',
              TechPen: '30',
            },
          },
          {
            data: {
              TechColor: 'Black',
              TechPen: '30',
            },
          },
          {
            data: {
              TechColor: 'Yellow',
              TechPen: '30',
            },
          }
        ];

        cellData.forEach((c:any)=>{
            render(<BPRTechColorCellRenderer {...c} />)
        })
    })
});

describe('Test BPREcoColorCellRenderer Component', () => {
  it('renders cell with correct text and color', () => {
    const cellData = {
      data: {
        EcoColor: 'Red',
        EcoPen: '30',
      },
    };

    render(<BPREcoColorCellRenderer {...cellData} />);

    const cellElement = screen.getByText('30%');

    expect(cellElement).toHaveTextContent('30%');
    expect(cellElement).toHaveStyle({ backgroundColor: '#F04D4D', color: 'white' });
  });
  it('renders cell with all colors', () => {
    const cellData = [
        {
            data: {
              EcoPen: '30',
            },
          },
          {
            data: {
              EcoColor: 'White',
              EcoPen: '30',
            },
          },
          {
            data: {
              EcoColor: 'Black',
              EcoPen: '30',
            },
          },
          {
            data: {
              EcoColor: 'Yellow',
              EcoPen: '30',
            },
          }
    ];

    cellData.forEach((c:any)=>{
        render(<BPREcoColorCellRenderer {...c} />)
    })

  });
});

describe('Test BPRTagsCellRenderer Component', () => {
  it('renders cell with correct tags', () => {
    const cellData = {
      value:'tag1'
    };

    render(<BPRTagsCellRenderer {...cellData} />);

    const cellElement = screen.getByText('tag1');

    expect(cellElement).toHaveTextContent('tag1');
  });
});

// describe('Test BPRSubmitRemarkCellRenderer Component', () => {
//   it('renders cell with input placeholder', () => {
//     const onClickMock = jest.fn();
//     render(<BPRSubmitRemarkCellRenderer onClick={onClickMock} />);

//     const inputElement = screen.getByPlaceholderText('Type Remark');
//     fireEvent.click(inputElement)

//     expect(inputElement).toBeInTheDocument();
//   });
// });

// describe('Test BPRRemarksCellRenderer Component', () => {
//   it('renders cell with icon', () => {
//     const onClickMock = jest.fn();
//     render(<BPRRemarksCellRenderer onClick={onClickMock} />);

//     const iconElement = screen.getByAltText('eye icon');

//     expect(iconElement).toBeInTheDocument();
//   });

//   it('calls onClick handler when icon is clicked', () => {
//     const onClickMock = jest.fn();

//     render(<BPRRemarksCellRenderer onClick={onClickMock} />);

//     const iconElement = screen.getByAltText('eye icon');
//     fireEvent.click(iconElement);
//   });
// });
