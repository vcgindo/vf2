import { render, screen } from '@testing-library/react';
import VFStepper, { StepItem } from './index'; // Adjust the import path as per your project structure

describe('Stepper Component', () => {
  const stepItems:StepItem[] = [
    {
      label: 'Step 1',
      status: 'completed',
      description: 'Description for Step 1',
    },
    {
      label: 'Step 2',
      status: 'pending',
      description: 'Description for Step 2',
    },
    {
      label: 'Step 3',
      status: 'rejected',
      description: 'Description for Step 3',
    },
  ];

  it('Renders the Stepper component', () => {
    render(<VFStepper items={stepItems} width="500px" />);
    
    // You may want to add more specific assertions here
    const stepperElement = screen.getByTestId('stepper');
    expect(stepperElement).toBeInTheDocument();
  });

  it('Renders all step items', () => {
    render(<VFStepper items={stepItems} width="500px" />);
    
    // Assert that all step items are present
    stepItems.forEach((item) => {
      const stepLabel = screen.getByText(item.label);
      const stepDescription = screen.getByText(item.description);
      expect(stepLabel).toBeInTheDocument();
      expect(stepDescription).toBeInTheDocument();
    });
  });

  it('Renders correct step icons', () => {
    render(<VFStepper items={stepItems} width="500px" />);
    
    // You may want to add more specific assertions for the step icons
    const completedStepIcon = screen.getByAltText('completed');
    const pendingStepIcon = screen.getByAltText('pending');
    const rejectedStepIcon = screen.getByAltText('rejected');
    
    expect(completedStepIcon).toBeInTheDocument();
    expect(pendingStepIcon).toBeInTheDocument();
    expect(rejectedStepIcon).toBeInTheDocument();
  });

  // Add more test cases for other functionalities as needed
});
