import { render, fireEvent, screen } from '@testing-library/react';
import VFButton from './index';

describe('VFButton Component', () => {
  it('renders the button with the provided text', () => {
    const buttonText = 'Click Me';
    render(<VFButton onClick={() => {console.log("test")}} themeUi="NOIRFUSION">{buttonText}</VFButton>);
    const button = screen.getByText(buttonText);
    expect(button).toBeInTheDocument();
  });

  it('calls the onClick function when the button is clicked', () => {
    const onClickMock = jest.fn();
    render(<VFButton onClick={onClickMock} themeUi="NOIRFUSION">Click Me</VFButton>);
    const button = screen.getByText('Click Me');
    fireEvent.click(button);
    expect(onClickMock).toHaveBeenCalled();
  });

  it('applies the custom width to the button', () => {
    const customWidth = 200;
    render(<VFButton onClick={() => {console.log("test")}} themeUi="NOIRFUSION" width={customWidth}>Click Me</VFButton>);
    const button = screen.getByText('Click Me');
    expect(button).toHaveStyle(`width: ${customWidth}px`);
  });

  it('renders with default width(130px) when not supplied ', () => {
    render(<VFButton onClick={() => {console.log("test")}} themeUi="NOIRFUSION">Click Me</VFButton>);
    const button = screen.getByText('Click Me');
    expect(button).toHaveStyle(`width: 130px`);
  });

  it('disables the button when disabled prop is true', () => {
    render(<VFButton onClick={() => {console.log("test")}} themeUi="NOIRFUSION" disabled={true}>Click Me</VFButton>);
    const button = screen.getByText('Click Me');
    expect(button).toHaveStyle(`pointer-events:none`);
    expect(button).toHaveStyle(`opacity:0.2`);
  });

  it('applies the specified theme', () => {
    render(<VFButton onClick={() => {console.log("test")}} themeUi="REGALBLAZE">Click Me</VFButton>);
    const button = screen.getByText('Click Me');
    expect(button).toHaveStyle(`background-image:#C7810F`)
  });
  
  it("onHoverChild on Hover",() => {
    render(<VFButton onClick={()=> {console.log("test")}} themeUi="REGALBLAZE"  onHoverChild={<p>Helo</p>}>Hello</VFButton> );
    const button = screen.getByText("Hello");
    fireEvent.mouseOver(button);
    fireEvent.mouseOut(button);
  })
});
