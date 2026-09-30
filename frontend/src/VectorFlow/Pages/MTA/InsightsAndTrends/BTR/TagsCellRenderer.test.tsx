import { render } from '@testing-library/react';
import TagsCellRenderer from './TagsCellRenderer';

describe('TagsCellRenderer', () => {
  it('renders with the correct tags', () => {
    const mockParams = {
      value:'tag1, tag2, tag3',
    };

    const { getByText } = render(<TagsCellRenderer {...mockParams} />);
    const tagsElement = getByText('tag1, tag2, tag3');

    expect(tagsElement).toBeInTheDocument();
  });

  // Add more test cases as needed
});
