import { render, screen, fireEvent } from '@testing-library/react';
import BPRViewTableRowCellWithReadMore from './BPRViewTableRowCellWithReadMore';

describe('BPRViewTableRowCellWithReadMore Component', () => {
  it('renders cell with truncated value and read more link', () => {
    const value = 'This is a long text to be truncated for testing purposes';

    render(<BPRViewTableRowCellWithReadMore value={value} />);

    const truncatedText = screen.getByText('This is a long ...');
    const readMoreLink = screen.getByText('Read full');

    expect(truncatedText).toBeInTheDocument();
    expect(readMoreLink).toBeInTheDocument();
  });

  it('displays tooltip with full value on mouse hover', () => {
    const value = 'This is a long text to be truncated for testing purposes';

    render(<BPRViewTableRowCellWithReadMore value={value} />);

    const readMoreLink = screen.getByText('Read full');

    fireEvent.mouseEnter(readMoreLink);

    const tooltip = screen.getByText(value);
    expect(tooltip).toBeInTheDocument();

    fireEvent.mouseEnter(tooltip)
    fireEvent.mouseLeave(tooltip)
    fireEvent.mouseLeave(readMoreLink);

    expect(tooltip).not.toBeInTheDocument();
  });
});
