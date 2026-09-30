import { useUserData } from '../context';

export const useThemeStyles = () => {
  const { user } = useUserData();
  const theme_ui = user.user.theme_ui;

  const styles = {
    option: (baseStyles: any, { isSelected }: any) => ({
      ...baseStyles,
      backgroundColor: isSelected
        ? theme_ui === "REGALBLAZE"
          ? "#FCA311"
          : "#BC3D80"
        : "white",
      fontSize: "14px",
      "&:hover": {
        color: "black",
        backgroundColor:
          theme_ui === "REGALBLAZE"
            ? "rgb(252, 163, 17,0.3) "
            : "#bc3d814d",
      },
    }),
    control: (baseStyles: any, { isFocused }: any) => ({
      ...baseStyles,
      borderColor: isFocused ? theme_ui === "REGALBLAZE"
        ? "#FCA311"
        : "#BC3D80" : "#c7c0c0ff",
      borderWidth: isFocused ? "2px" : "1px",
      borderRadius: "10px",
      fontSize: "14px",
      boxShadow: "none",
      minHeight: "40px",
      "&:hover": {
        borderColor: isFocused ? theme_ui === "REGALBLAZE"
          ? "#FCA311"
          : "#BC3D80" : "#c7c0c0ff",
      },
    }),
    input: (baseStyles: any) => ({
      ...baseStyles,
      fontSize: "14px", // Set input font size here
      fontFamily: "Roboto, sans-serif",
      margin: 0,
      padding: 0,
    }),
    menu: (baseStyles: any) => ({
      ...baseStyles,
      zIndex: 9999,
      position: "absolute",
      maxHeight: "none",
      overflow: "visible",
    }),
    menuList: (baseStyles: any) => ({
      ...baseStyles,
      maxHeight: "none",
      overflow: "visible",
    }),
    placeholder: (baseStyles: any) => ({
      ...baseStyles,
      fontSize: "14px",
      color: "#757575",
    }),
    singleValue: (baseStyles: any) => ({
      ...baseStyles,
      fontSize: "14px",
      color: "black",
    }),
  };

  return styles;
}

interface ColorThemeStylesProps {
  minHeight?: string;
  minWidth?: string;
  valueContainerPaddingLeft?: string;
  inputColor?: string;
  placeholderColor?: string;
  menuListMaxHeight?: string | number;
  menuWidth?: string;
  gridColumns?: 1 | 2;
  gridGap?: string;
  optionPadding?: string;
}

export const useColorThemeStyles = (props?: ColorThemeStylesProps) => {
  const { user } = useUserData();
  const theme_ui = user.user.theme_ui;

  const {
    minHeight = "40px",
    minWidth = "250px",
    valueContainerPaddingLeft,
    inputColor,
    placeholderColor,
    menuListMaxHeight,
    menuWidth,
    gridColumns = 1,
    gridGap = "8px",
    optionPadding = "0 12px"
  } = props || {};

  const styles = {
    control: (baseStyles: any, { isFocused }: any) => ({
      ...baseStyles,
      borderColor: isFocused
        ? (theme_ui === "REGALBLAZE" ? "#FCA311" : "#BC3D80")
        : "#c7c0c0ff",
      borderWidth: isFocused ? "2px" : "1px",
      borderRadius: "10px",
      fontSize: "14px",
      minHeight: minHeight,
      boxSizing: "border-box",
      boxShadow: "none",
      width: "100%",
      minWidth: minWidth,
      maxWidth: "360px",
      overflow: "hidden",
      "&:hover": {
        borderColor: isFocused
          ? (theme_ui === "REGALBLAZE" ? "#FCA311" : "#BC3D80")
          : "#c7c0c0ff",
      },
    }),
    menu: (baseStyles: any) => ({
      ...baseStyles,
      zIndex: 9999,
      position: "absolute",
      width: "100%",
      minWidth: menuWidth || minWidth,
      maxWidth: "360px",
    }),
    menuList: (baseStyles: any) => ({
      ...baseStyles,
      maxHeight: menuListMaxHeight || "none",
      overflowY: menuListMaxHeight ? "auto" : "visible",
      scrollbarWidth: "thin", 
      scrollbarColor: "#888 transparent",

      ...(gridColumns === 2 && {
        display: "grid",
        gridTemplateColumns: "repeat(2, 1fr)",
        gap: gridGap,
        padding: gridGap,
      }),
      "&::-webkit-scrollbar": {
        width: "6px",
      },
      "&::-webkit-scrollbar-thumb": {
        backgroundColor: "#888",
        borderRadius: "4px",
      },
      "&::-webkit-scrollbar-thumb:hover": {
        backgroundColor: "#555",
      },
    }),
    option: (baseStyles: any, { isSelected, isFocused }: any) => ({
      ...baseStyles,
      backgroundColor: isSelected
        ? (theme_ui === "REGALBLAZE" ? "#FCA311" : "#BC3D80")
        : "white",
      fontSize: "14px",
      cursor: "pointer",
      minHeight: minHeight,
      display: "flex",
      alignItems: "center",
      ...(gridColumns === 2 && {
        gridColumn: "span 1",
        margin: 0,
        borderRadius: "6px",
        padding: optionPadding,
        border: isFocused ? `1px solid ${theme_ui === "REGALBLAZE" ? "#FCA311" : "#BC3D80"}` : "1px solid #f0f0f0",
      }),
      "&:hover": {
        color: "black",
        backgroundColor: theme_ui === "REGALBLAZE"
          ? "rgb(252, 163, 17,0.3)"
          : "#bc3d814d",
        ...(gridColumns === 2 && {
          borderColor: theme_ui === "REGALBLAZE" ? "#FCA311" : "#BC3D80"
        }),
      },
    }),
    placeholder: (baseStyles: any) => ({
      ...baseStyles,
      fontSize: "14px",
      color: placeholderColor || "#757575",
    }),
    multiValue: (baseStyles: any) => ({
      ...baseStyles,
      borderRadius: "6px",
      padding: "2px",
      backgroundColor: theme_ui === "REGALBLAZE"
        ? "rgb(252, 163, 17,0.1)"
        : "rgba(188, 61, 128, 0.1)",
      flexShrink: 0,
      minWidth: "fit-content",
      maxWidth: "120px",
    }),
    multiValueLabel: (baseStyles: any) => ({
      ...baseStyles,
      color: theme_ui === "REGALBLAZE" ? "#FCA311" : "#BC3D80",
      fontSize: "14px",
      whiteSpace: "nowrap",
      overflow: "hidden",
      textOverflow: "ellipsis",
      maxWidth: "100px",
    }),
    multiValueRemove: (baseStyles: any) => ({
      ...baseStyles,
      color: theme_ui === "REGALBLAZE" ? "#FCA311" : "#BC3D80",
      flexShrink: 0,
      "&:hover": {
        backgroundColor: theme_ui === "REGALBLAZE" ? "#FCA311" : "#BC3D80",
        color: "white",
      },
    }),
    valueContainer: (baseStyles: any) => ({
      ...baseStyles,
      display: 'flex',
      alignItems: 'center',
      flexWrap: 'nowrap',
      overflowX: 'auto',
      overflowY: 'hidden',
      width: "calc(100% - 40px)",
      maxWidth: "calc(100% - 40px)",
      minWidth: "0",
      flex: "1 1 auto",
      scrollbarWidth: "none",
      scrollbarColor: "none",
      gap: "4px",
      padding: valueContainerPaddingLeft ? `2px 8px 2px ${valueContainerPaddingLeft}` : "2px 8px",
    }),
    input: (baseStyles: any) => ({
      ...baseStyles,
      fontSize: "14px",
      fontFamily: "Roboto, sans-serif",
      margin: 0,
      padding: 0,
      width: "0px",
      minWidth: "0px",
      maxWidth: "0px",
      border: "none",
      outline: "none",
      background: "transparent",
      opacity: 0,
      color: inputColor || "inherit",
    }),
    indicatorsContainer: (baseStyles: any) => ({
      ...baseStyles,
      flexShrink: 0,
    }),
  };

  return styles;
};

export const useColorOptionStyles = () => {
  const { user } = useUserData();
  const theme_ui = user.user.theme_ui;
  const themeColor = theme_ui === "REGALBLAZE" ? "#FCA311" : "#BC3D80";

  return {
    checkbox: {
      width: "16px",
      height: "16px",
      accentColor: themeColor,
      cursor: "pointer",
      flexShrink: 0,
    },
    colorPanel: {
      width: "20px",
      height: "20px",
      borderRadius: "4px",
      border: "1px solid #ddd",
      flexShrink: 0,
      boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
      order: 2,
    },
    colorName: {
      fontSize: "14px",
      fontFamily: "Roboto, sans-serif",
      fontWeight: "400",
      color: "#333",
      flex: 1,
      textAlign: "left" as const,
      order: 1,
    },
    optionContainer: {
      display: "flex",
      alignItems: "center",
      gap: "10px",
      width: "100%",
      padding: "4px 0",
    }
  };
};