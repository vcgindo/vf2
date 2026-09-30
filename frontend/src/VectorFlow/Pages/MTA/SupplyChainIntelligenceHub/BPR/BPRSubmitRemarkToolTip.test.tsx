import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import BPRSubmiRemarkToolTip from './BPRSubmitRemarkToolTip';

describe('BPRSubmiRemarkToolTip Component', () => {
  const onCloseMock = jest.fn();
  const onSuccessMock = jest.fn();
  const setRemarkMock = jest.fn();

  beforeEach(() => {
    render(
      <BPRSubmiRemarkToolTip
        style={{
          top:0
        }}
        remark=""
        setRemark={setRemarkMock}
        onClose={onCloseMock}
        onSuccess={onSuccessMock}
        themeUi={"NOIRFUSION"}
      />
    );
  });

  it('renders submit remark tool tip properly', () => {
    expect(screen.getByPlaceholderText('Type your remark here')).toBeInTheDocument();
    expect(screen.getByText('Submit')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('calls setRemark function when typing in textarea', () => {
    const textarea = screen.getByPlaceholderText('Type your remark here');
    fireEvent.change(textarea, { target: { value: 'Test remark' } });

    expect(setRemarkMock).toHaveBeenCalledTimes(1);
  });

  it('calls onClose function when cancel button is clicked', () => {
    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });

  it('calls onSuccess function when submit button is clicked', () => {
    const submitButton = screen.getByText('Submit');
    fireEvent.click(submitButton);

    expect(onSuccessMock).toHaveBeenCalledTimes(1);
  });
});
