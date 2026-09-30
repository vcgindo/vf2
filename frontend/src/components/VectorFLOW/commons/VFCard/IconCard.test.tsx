import { render, fireEvent } from '@testing-library/react';
import IconCard from './IconCard';

// Mock the onClick function
const mockOnClick = jest.fn();

const cardText = 'Test Text'

describe('IconCard Component', () => {
  it('displays the text provided',()=>{
    const {getByText} = render(<IconCard themeUi="REGALBLAZE" text={cardText} iconOnMouseIn="path/to/icon-on-mouse-in.png" iconOnMouseOut="path/to/icon-on-mouse-out.png" onClick={mockOnClick}/>)
    const card = getByText(cardText)
    expect(card).toBeInTheDocument()
    })

    it('calls the onClick when the text is clicked',()=>{
        const {getByText} = render(<IconCard themeUi="REGALBLAZE" text={cardText} iconOnMouseIn="path/to/icon-on-mouse-in.png" iconOnMouseOut="path/to/icon-on-mouse-out.png" onClick={mockOnClick}/>)

        const textElement = getByText(cardText)
        fireEvent.click(textElement)
        expect(mockOnClick).toBeCalledTimes(1)
    })

});
