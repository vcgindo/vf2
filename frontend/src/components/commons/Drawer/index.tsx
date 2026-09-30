import { Dialog, Transition } from "@headlessui/react";
import { Fragment, ReactNode } from "react";

import "./styles.css";

interface DrawerProps {
  header?: any;
  children: ReactNode;
  isOpen: boolean;
  onClose: () => void;
}

const Drawer = (props: DrawerProps) => {
  const { header, children, isOpen, onClose } = props;

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="modal-box" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="transition"
          enterFrom="opa-0"
          enterTo="opa"
          leaveTo="opa-0"
        >
          <div className="modal-bg inset" />
        </Transition.Child>

        <div className="modal-content">
          <div className="content-wrapper">
            <Dialog.Panel className="drawer-content">
              {header && (
                <Dialog.Title as="div" className="drawer-title">
                  {header}
                </Dialog.Title>
              )}
              <div style={{ height: "calc(100% - 32px)" }}>{children}</div>
            </Dialog.Panel>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
};

export default Drawer;
