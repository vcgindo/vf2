import { ReactElement } from 'react';
import { LogoWrapper, NoteWrapper } from './styles';

interface INoteProps {
    type: string;
    message:  ReactElement<any, any>;
}

const Note = (props: INoteProps) => {

    const { type, message } = props;
    return ( 
        <>
            <NoteWrapper data-testid='note'>
                <LogoWrapper>
                    {type === 'danger' && 
                        <img
                            src="/assets/img/warning-icon.svg"
                            alt="warning-icon"
                        />
                    }
                </LogoWrapper>
                {message}
            </NoteWrapper>
        </>
    )
}

export default Note;
