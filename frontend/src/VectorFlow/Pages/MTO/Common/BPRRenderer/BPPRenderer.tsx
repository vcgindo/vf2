import React from 'react';
import { ColorsMTO } from '../Colors';
import _ from 'lodash';

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

const BPPRenderer = (props: any) => {
    const color = !_.isEmpty(props.data) && (props.data?.cl || props.data?.clr || props.data?.cp);
    const cellColor = colorMapper(color);
    
    return (
        <>
            {color && <div style={{ display: 'flex', width: '50%', height: '90%', backgroundColor: cellColor.bg, justifyContent: 'center', alignItems: 'center', boxShadow: '0px 6px 12px #8D8D8D29', position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)' }}>
                <span style={{ color: 'white' }}>{props?.data?.bpp}</span>
            </div>}
        </>
    )
}

export default BPPRenderer

