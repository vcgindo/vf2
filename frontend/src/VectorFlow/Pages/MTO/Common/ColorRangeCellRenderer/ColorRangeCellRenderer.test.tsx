import { render } from '@testing-library/react';
import ColorCellRenderer from '.';

 const colorMapper =(color:number)=> {
    if(color<0){
        return {
            "bg":"white",
            "text":"black"
        }
    }
    if(color<33.33 && color>0){
        return {
            "bg":"#418D18",
            "text":"white"
        }
    }
    if(color>33.33 && color<66.66){
        return {
            "bg":"#EBBF2B",
            "text":"white"
        }
    }
    if(66.66<color && color<99.99){
        return {
            "bg":"#F04D4D",
            "text":"white"
        }
    }

    return{
        "bg":"#000000",
        "text":"white"
    }  
}


describe('ColorCellRenderer', () => {
  it('renders with the correct color and text', () => {
    const { getByTestId } = render(<ColorCellRenderer value={50} />);
    const colorCell = getByTestId('color-cell');

    expect(colorCell).toHaveStyle({ backgroundColor: '#EBBF2B', color: 'white' });
    expect(colorCell.textContent).toBe('50');
  });
});

describe('colorMapper', () => {
  it('returns white text on black background for negative color', () => {
    render(<ColorCellRenderer value={-10} />)
    const color = colorMapper(-10);
    expect(color).toEqual({ bg: 'white', text: 'black' });
  });

  it('returns white text on green background for color between 0 and 33.33', () => {
    const color = colorMapper(25);
    expect(color).toEqual({ bg: '#418D18', text: 'white' });
  });

  it('returns white text on yellow background for color between 33.33 and 66.66', () => {
    render(<ColorCellRenderer value={31} />)
    const color = colorMapper(50);
    expect(color).toEqual({ bg: '#EBBF2B', text: 'white' });
  });

  it('returns white text on red background for color between 66.66 and 99.99', () => {
    render(<ColorCellRenderer value={70} />)
    const color = colorMapper(80);
    expect(color).toEqual({ bg: '#F04D4D', text: 'white' });
  });

  it('returns white text on black background for color >= 100', () => {
    const color = colorMapper(110);
    expect(color).toEqual({ bg: '#000000', text: 'white' });
  });
});
