import { useSpring, animated } from "react-spring";

const FilterCheckboxAccordian = ({
  filterType,
  filterKey,
  isOpen,
  handleToggleAccordian,
  children,
}: any) => {

    const handleAccordian = (key: string)=>{
        handleToggleAccordian(key)
    }

  const openAnimation = useSpring<any>({
    from: { opacity: "0", maxHeight: "25px" },
    to: { opacity: "1", maxHeight: isOpen ? "200px" : "25px" },
    config: { duration: "300" },
  });

  const closeAnimation = useSpring<any>({
    from: { opacity: "0", maxHeight: "0px" },
    to: { opacity: "1", maxHeight: isOpen ? "144px" : "0px" },
    config: { duration: "300" },
  });

  const iconAnimation = useSpring<any>({
    from: {
      transform: "rotate(0deg)",
    },
    to: {
      transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
    },
    config: { duration: "120" },
  });

  return (
    <animated.div className="filter-accordian" style={openAnimation}>
      <div
        className="accordian-header "
        onClick={() => {
            handleAccordian(filterKey);
        }}
        style={{ display: "flex", gap: "1rem" }}
      >
        <p
          className="accordian-title"
          style={{ fontWeight: isOpen ? "500" : "" }}
        >
          {filterType}
        </p>
        <animated.img
          style={iconAnimation}
          src="/assets/img/VectorFLOW/BPR/down-arrow.svg"
          data-testid="down-arrow"
        ></animated.img>
      </div>
      <animated.div
        className="accordian-body  custom-scrollbar"
        style={closeAnimation}
      >
        {children}
      </animated.div>
    </animated.div>
  );
};

export default FilterCheckboxAccordian;
