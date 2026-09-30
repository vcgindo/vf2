import { ReactNode } from 'react';
import { render, fireEvent } from '@testing-library/react';
import VFRangeSlider from './';

import { UserDataContext } from '../../../../context';

const contextWrapperWithCustomTheme = (children: ReactNode,theme:string) => {
  return (

          <UserDataContext.Provider
            value={{
              user: { user: { theme_ui: theme } },
              changeColorTheme: (color) => {
                return color;
              },
              isSideBarOpen:true,toggleSideBar:jest.fn
            }}
          >
            {children}
          </UserDataContext.Provider>

  );
};

describe('VFRangeSlider', () => {
  it('renders with default props', () => {
    const { getByRole } = render(contextWrapperWithCustomTheme(<VFRangeSlider min={0} max={100} strictMode={false} width={300} defaultValue={50} handleChange={jest.fn()} showTriangle/>,"REGALBLAZE"));
    const inputRange = getByRole('slider');
    fireEvent.change(inputRange, { target: { value: '60' } });
    expect(inputRange).toHaveAttribute('value', '60');
    expect(inputRange).toBeInTheDocument();
    expect(inputRange).toHaveAttribute('min', '0');
    expect(inputRange).toHaveAttribute('max', '100');
    fireEvent.change(inputRange, { target: { value: '0' } });
   
  });

  it('updates value on slider change', () => {
    const { getByRole } = render(contextWrapperWithCustomTheme(<VFRangeSlider min={0} max={100} strictMode={true} width={300} defaultValue={50}milestones={[0,30,40,60,70,100]} handleChange={jest.fn()} showTriangle={false}/>,"NOIRFUSION"));
    const inputRange = getByRole('slider');

    fireEvent.change(inputRange, { target: { value: '75' } });
    fireEvent.change(inputRange, { target: { value: '62' } });
    fireEvent.change(inputRange, { target: { value: '69' } });
    fireEvent.change(inputRange, { target: { value: '25' } });
    fireEvent.change(inputRange, { target: { value: '' } });

  });
});
