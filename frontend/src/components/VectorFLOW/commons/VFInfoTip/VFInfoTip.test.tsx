import {screen,render} from "@testing-library/react";
import VFInfoTip from ".";

const dummyprops={
    text:["hello", "hi", "hiya"],
    singletext:['welcome']
  
}

describe("VFInfoTip Component", () => {
    it("renders the Info Tip component", () => {
      render(<VFInfoTip text={dummyprops.text}></VFInfoTip>)
      const txt = screen.getAllByText('hello')[0];
      expect(txt).toBeInTheDocument();
    })  

    it("renders the Info Tip component", () => {
        render(<VFInfoTip text={dummyprops.singletext}></VFInfoTip>)
        const single=screen.getByText('welcome');
      expect(single).toBeInTheDocument();
    })  
  
  })