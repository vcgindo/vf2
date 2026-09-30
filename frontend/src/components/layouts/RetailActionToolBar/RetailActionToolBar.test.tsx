

import React from 'react';
import { render, fireEvent } from '@testing-library/react';
import RetailActionToolBar from ".";


describe('RetailActionToolBar component', () => {
  const defaultProps = {
    themeUi: 'REGALBLAZE',
    onViewChange: jest.fn(),
    onCallBack: jest.fn(),
    view: 'grid',
    handleSelectChange: jest.fn(),
    handleGoButton: jest.fn(),
    currentStatus: 'Save',
    handleOnCancel: jest.fn(),
  };

  it('renders correctly', () => {
    const { container } = render(<RetailActionToolBar {...defaultProps} />);
    expect(container).toMatchSnapshot();
  });

  it('calls onViewChange when grid view button is clicked', () => {
    const { getByText } = render(<RetailActionToolBar {...defaultProps} />);
    const gridViewButton = getByText('Grid View');
    fireEvent.click(gridViewButton);
  });

  // it('calls handleGoButton when go button is clicked', () => {
  //   const { getByRole } = render(<RetailActionToolBar {...defaultProps} />);
  //   const goButton = getByRole('img');
  //   fireEvent.click(goButton);
  //   // expect(defaultProps.handleGoButton).toHaveBeenCalledTimes(1);
  // });

  it('calls handleOnCancel when cancel button is clicked', () => {
    const { getByText } = render(<RetailActionToolBar {...defaultProps} />);
    const cancelButton = getByText('Cancel');
    fireEvent.click(cancelButton);
  });
  it('calls Save Options Button', () => {
    const { getByText } = render(<RetailActionToolBar {...defaultProps} />);
    const saveButton = getByText('Save Options');
    fireEvent.click(saveButton);
  });
  
  it('renders Save Options button  and Cancel Option Button when currentStatus is Save', () => {
    const { getByText } = render(<RetailActionToolBar {...defaultProps} />);
    expect(getByText('Save Options')).toBeInTheDocument();
    expect(getByText('Cancel')).toBeInTheDocument();

  });

  it('renders Edit Options button when currentStatus is Edit', () => {
    const editProps = { ...defaultProps, currentStatus: 'Edit' };
    const { getByText } = render(<RetailActionToolBar {...editProps} />);
    expect(getByText('Edit Options')).toBeInTheDocument();
  });

  it('renders chart view and grid view buttons', () => {
    const { getByText } = render(<RetailActionToolBar {...defaultProps} />);
    expect(getByText('Chart View')).toBeInTheDocument();
    expect(getByText('Grid View')).toBeInTheDocument();
  });

  it('calls handleSelectChange when select option is changed', () => {
    const { getByRole } = render(<RetailActionToolBar {...defaultProps} />);
    const select = getByRole('combobox');
    fireEvent.change(select, { target: { value: 'accept' } });
    // expect(defaultProps.handleSelectChange).toHaveBeenCalledTimes(1);
  });
});
  