import { OrderCoverageCellRendererWrapper, CoverageColorBox } from "./styles"

export const OrderCoverageCellRenderer = (params:any)=>{
        const getColor = () => {
            switch(params.data['c']){
                case 'Gap > 67%':
                    return '#9A0101';
                case '33% <= Gap <= 67%':
                    return '#EBBF2B';
                case 'Gap < 33%':
                    return '#418D18';
                default:
                    return '#ffffff';
            }
        }
    
        return(
            <OrderCoverageCellRendererWrapper>
                <CoverageColorBox color={getColor()} data-testid="coverage-color-box"/>
                <p>{params.data['c']}</p>
            </OrderCoverageCellRendererWrapper>
        )
}