import { render,screen, fireEvent, waitFor } from '@testing-library/react';
import WarningCell from '.';

const props:any = {
    value:'dummy',
    data:{warning:"SKU Code has pipe and comma"}

}

describe("Renders Error Cell",() => {

    it("Render the component when message is more than 25 char",()=>{
        render(<WarningCell {...props}/>);
        expect(screen.getByText('SKU Code has pipe and com...')).toBeInTheDocument();
        
    })

    it("Renders the component with message is less than 25 char",()=>{
        const message = "dummydumm"
        props.data.warning = message;
        render(<WarningCell {...props}/>);
        expect(screen.getByText('dummydumm')).toBeInTheDocument();
        
    })
    it("Renders an Empty fragment when message is undefined",()=>{
        props.data.warning = undefined;
        render(<WarningCell {...props}/>);
        
    })
    it("Handles mouse event", async () => {
        const message = "dummydumm";
        props.data.warning = message;
        render(<WarningCell {...props} />);
        
        const warningIcon = screen.getByTestId('warningImage');
        
        fireEvent.mouseEnter(warningIcon);
        await waitFor(() => {
            expect(screen.getByTestId('tooltip-wrapper')).toBeInTheDocument();
        });
    
        fireEvent.mouseLeave(warningIcon);
        await waitFor(() => {
            expect(screen.queryByTestId('tooltip-wrapper')).not.toBeInTheDocument();
        });
    });
    
})