import { screen, render, fireEvent } from "@testing-library/react"
import TaskPendingTaskBar from './TaskPendingTaskBar';
import { UserDataContext } from "../../../../../context";

const onSubmit = jest.fn();
const onCancel = jest.fn();

describe("RejectAllModal Component", () => {
  it("Renders Task Bar", () => {
    render(
        <UserDataContext.Provider
        value={{
          user: { user: { theme_ui: "NOIRFUSION" } },
          changeColorTheme: (color) => {
            return color;
          },
          isSideBarOpen:true,toggleSideBar:jest.fn
        }}
      >
        <TaskPendingTaskBar onSubmit={onSubmit} onCancel={onCancel} disableSubmit={false} isSideBarOpen={true}/>
        </UserDataContext.Provider>
    );
    fireEvent.click(screen.getByText("Submit"));
    expect(onSubmit).toBeCalled();
    fireEvent.click(screen.getByText("Cancel"));
    expect(onCancel).toBeCalled();

  })


})
