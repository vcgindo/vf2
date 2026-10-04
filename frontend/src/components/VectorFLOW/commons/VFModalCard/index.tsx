import { Dialog, Transition } from "@headlessui/react";
import "./styles.css";
import { Fragment, ReactNode, CSSProperties} from "react";

import {
  SCModalContent,
  SCTextTitle,
  SCCloseModal,
  SCWrapperContent,
  VFHeaderWrapper,
  SCHeader
} from "./styles";  
import { noop } from "lodash";

interface VFModalProps {
  openModal: boolean;
  closeModal?: () => void;
  headerText?:string | ReactNode;
  headerIcon:string;
  children:ReactNode;
  paddingLeftAndRight?:number;
  headerBgColor?:string;
  headerTextColor?:string;
  closeIcon?:string;
  backgroundColor?:string;
  zoom?:string;
  absolute?: boolean;
  panelStyle?: CSSProperties;
  contentStyle?: CSSProperties;
}


const VFModalCard = ({
  openModal,
  closeModal,
  headerText,
  headerIcon,
  closeIcon,
  children,
  paddingLeftAndRight,
  headerBgColor,
  headerTextColor,
  backgroundColor,
  zoom = '1',
  absolute, panelStyle, contentStyle
}: VFModalProps) => {


  return (
    <>
      {
        <Transition appear show={openModal} as={Fragment}>
          <Dialog as="div" className="modal-box" onClose={noop}>
            <Transition.Child
              as={Fragment}
              enter="transition"
              enterFrom="opa-0"
              enterTo="opa"
              leave="leave-modal"
              leaveFrom="opa"
              leaveTo="opa-0"
            >
              <div className="modal-bg inset" />
            </Transition.Child>
            <SCModalContent style={{zoom:zoom}}>
              <div className="modal-content--box">
                <Transition.Child
                  as={Fragment}
                  enter="transition"
                  enterFrom="opa-0 tranlate "
                  enterTo="opa translate-y-0 "
                  leave="leave-modal"
                  leaveFrom="opa translate-y-0"
                  leaveTo="opacity-0 tranlate"
                >
                  <Dialog.Panel className="modal-forced--block" style={panelStyle}>
                    <Dialog.Title as="h3" className="modal-title-forced" style={{backgroundColor:headerBgColor, boxShadow:'0px 5px 10px 0px rgba(110, 107, 107,0.11)', position:'relative', zIndex:'10'}}>
                    <VFHeaderWrapper headerBgColor={headerBgColor} absolute={absolute}>
                      <SCHeader>
                        {headerIcon.length > 0 && <img src={headerIcon} height={20} width={20} data-testid='vfmodal-img'/>}
                        <SCTextTitle headerTextColor={headerTextColor}>{headerText}</SCTextTitle>
                      </SCHeader>
                      {
                        closeModal && (
                          <SCCloseModal onClick={closeModal} data-testid="close-modal-icon">
                            <img src={closeIcon} height={16} width={16} />
                          </SCCloseModal>
                        )
                      }
                      </VFHeaderWrapper>
                    </Dialog.Title>
                    <SCWrapperContent style={contentStyle} paddingLeftAndRight={paddingLeftAndRight} backgroundColor={backgroundColor} >
                       {children}
                    </SCWrapperContent>
                  </Dialog.Panel>
                </Transition.Child>
              </div>
            </SCModalContent>
          </Dialog>
        </Transition>
      }
    </>
  );

}

export default VFModalCard;


