import React from 'react';
import { render, fireEvent, screen } from '@testing-library/react';
import VFCapsule from './';
import { UserDataContext } from '../../../../context'; // assuming the context name is UserDataContext
import '@testing-library/jest-dom';

// Mock context value

const mockFn = jest.fn()
const mockContextValue = {
    user: {
        id: 0,
        email: '',
        name: '',
        is_admin: false,
        role: '',
        user:{
            theme_ui:'some'
        }
      },
      changeColorTheme: jest.fn(),
      isSideBarOpen:false,
      toggleSideBar:jest.fn()
};

describe('VFCapsule Component', () => {
    // Mock data for the component props
    const mockProps = {
        activeBtn: { label: 'Label 1', value: 'Value 1' },
        capsules: [
            { label: 'Label 1', value: 'Value 1' },
            { label: 'Label 2', value: 'Value 2' },
        ] 
    };
    
    it('renders without crashing', () => {
        render(
            <UserDataContext.Provider value={mockContextValue}>
                <VFCapsule {...mockProps}  handleClick={mockFn}/>
            </UserDataContext.Provider>
        );
        // Ensure that the capsule buttons are rendered
        expect(screen.getByText('Label 1')).toBeInTheDocument();
        expect(screen.getByText('Label 2')).toBeInTheDocument();
    });

    // Test 2: Button Click Handling
    it('updates active button state and invokes handleClick', () => {
        render(
            <UserDataContext.Provider value={mockContextValue}>
                <VFCapsule {...mockProps} handleClick={mockFn}/>
            </UserDataContext.Provider>
        );
        fireEvent.click(screen.getByText('Label 2'));
        expect(mockFn).toHaveBeenCalledWith({ label: 'Label 2', value: 'Value 2' });
    });

    it('handles optional props',()=>{
        render(
            <UserDataContext.Provider value={mockContextValue}>
                <VFCapsule {...mockProps} handleClick={mockFn}/>
            </UserDataContext.Provider>
        )
        fireEvent.click(screen.getByText('Label 2'));
        fireEvent.click(screen.getByText('Label 1'));
    })
});
