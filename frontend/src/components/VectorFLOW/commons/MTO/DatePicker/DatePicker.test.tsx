import React from 'react';
import { render, fireEvent } from '@testing-library/react';
import DatePicker from '.';

describe('DatePicker', () => {
    it('should update value when date changes', () => {
        const setDate = jest.fn();
        const { getByDisplayValue } = render(<DatePicker date="2024-06-26" setDate={setDate} type="date" />);

        const input = getByDisplayValue('2024-06-26');
        fireEvent.change(input, { target: { value: '2024-06-27' } });

        expect(setDate).toHaveBeenCalledWith('2024-06-27');
    });
});
