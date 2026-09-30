import React from 'react';
import { render, screen } from '@testing-library/react';
import Note from '.';

describe('Note Component', () => {
  it('renders warning icon for type="danger"', () => {
    render(
      <Note
        type="danger"
        message={<div>Test Warning Message</div>}
      />
    );

    const warningIcon = screen.getByAltText('warning-icon');
    expect(warningIcon).toBeInTheDocument();
  });

  it('displays the message correctly', () => {
    render(
      <Note
        type="danger"
        message={<div>Test Warning Message</div>}
      />
    );

    const messageElement = screen.getByText('Test Warning Message');
    expect(messageElement).toBeInTheDocument();
  });
});
