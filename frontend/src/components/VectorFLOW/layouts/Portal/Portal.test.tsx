import { render } from '@testing-library/react';
import PortalModal from './';

describe('PortalModal component', () => {
  it('renders without crashing', () => {
    render(
      <PortalModal wrapperId="test-wrapper">
        <div>Test Content</div>
      </PortalModal>
    );
  });

  it('creates and appends portal element when wrapperId is provided', () => {
    const { baseElement } = render(
      <PortalModal wrapperId="test-wrapper">
        <div>Test Content</div>
      </PortalModal>
    );

    const portalElement = baseElement.querySelector('#test-wrapper');
    expect(portalElement).toBeInTheDocument();
  });

  it('removes portal element when component is unmounted', () => {
    const { unmount } = render(
      <PortalModal wrapperId="test-wrapper">
        <div>Test Content</div>
      </PortalModal>
    );

    const portalElement = document.querySelector('#test-wrapper');
    expect(portalElement).toBeInTheDocument();

    unmount();

    const portalElementAfterUnmount = document.querySelector('#test-wrapper');
    expect(portalElementAfterUnmount).not.toBeInTheDocument();
  });
});
