
import { render, screen, fireEvent } from '@testing-library/react';
import BPRRemarkHistoryToolTip from './BPRRemarkHistoryToolTip';

describe('BPRRemarkHistoryToolTip Component', () => {
  const onCloseMock = jest.fn();

  const remarkHistoryData = [
    { rd: '2024-02-21', r: 'Some remark 1', un: 'Author 1' },
    { rd: '2024-02-22', r: 'Some remark 2', un: 'Author 2' },
  ];

  beforeEach(() => {
    render(<BPRRemarkHistoryToolTip style={{top:9}} remarkHistory={remarkHistoryData} onClose={onCloseMock} />);
  });

  it('renders remarks history properly', () => {
    expect(screen.getByText('Remarks History')).toBeInTheDocument();

    expect(screen.getByText('2024-02-21')).toBeInTheDocument();
    expect(screen.getByText('2024-02-22')).toBeInTheDocument();

    expect(screen.getByText('Name - Author 1')).toBeInTheDocument();
    expect(screen.getByText('Name - Author 2')).toBeInTheDocument();

    expect(screen.getByText('Some remark 1')).toBeInTheDocument();
    expect(screen.getByText('Some remark 2')).toBeInTheDocument();
  });

  it('calls onClose handler when close icon is clicked', () => {
    const closeIcon = screen.getByAltText('close-icon');
    fireEvent.click(closeIcon);

    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });
});
