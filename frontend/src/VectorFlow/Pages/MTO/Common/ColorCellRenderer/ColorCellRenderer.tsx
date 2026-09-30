
import { BPRColorCellRendererWrapper } from '../../../MTA/SupplyChainIntelligenceHub/BPR/styles';
import { ColorsMTO } from '../Colors';

const colorMapper = (color: string) => {

    switch (color) {
        case 'White':
            return { bg: "#A8A8A8", text: ColorsMTO.Black.code };
        case 'Green':
            return { bg: ColorsMTO.Green.code, text: ColorsMTO.White.code };
        case 'Yellow':
            return { bg: ColorsMTO.Yellow.code, text: ColorsMTO.White.code };
        case 'Red':
            return { bg: ColorsMTO.Red.code, text: ColorsMTO.White.code };
        case 'Black':
            return { bg: ColorsMTO.Black.code, text: ColorsMTO.White.code };
        case 'Blue':
            return { bg: ColorsMTO.Blue.code, text: ColorsMTO.White.code }
        case "Overloaded":
            return { bg: ColorsMTO.Red.code, text: ColorsMTO.White.code }
        case "Underloaded":
            return { bg: ColorsMTO.Orange.code, text: ColorsMTO.White.code }
        case "Balanced":
            return { bg: "#A8A8A8", text: ColorsMTO.White.code }
        default:
            return { bg: ColorsMTO.White.code, text: ColorsMTO.Black.code };

    }
};

const ColorCellRenderer = (params: any) => {
    // const color = params.data?.cp;
    const color = params.value;
    const cellColor = colorMapper(color);

    return (
        <>
            {color && <BPRColorCellRendererWrapper
                style={{ backgroundColor: cellColor.bg, color: cellColor.text, maxWidth: '80px' }}
                data-testid='color-cell'>
                {color}
            </BPRColorCellRendererWrapper>}
        
        </>
    );
}

export default ColorCellRenderer;
