import { render, fireEvent } from '@testing-library/react';
import ButtonCard from './ButtonCard';


// Mock the onClick function
const mockOnClick = jest.fn();

describe('ButtonCard Component', () => {
  it('renders the component with the provided text', () => {
    const { getByText } = render(<ButtonCard themeUi="REGALBLAZE" text="Test Button" onClick={mockOnClick} />);
    
    const buttonElement = getByText('Test Button');
    
    expect(buttonElement).toBeInTheDocument();
  });

  it('calls the onClick function when the button is clicked', () => {
    const { getByText } = render(<ButtonCard themeUi="REGALBLAZE" text="Test Button" onClick={mockOnClick} />);
    
    const buttonElement = getByText('Test Button');
    fireEvent.click(buttonElement);
    
    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });
});



