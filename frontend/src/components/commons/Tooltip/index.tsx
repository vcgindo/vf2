import './styles.css'
const Tooltip = () => {
  return (
    <div
      style={{
        textAlign: 'center'
      }}
    >
      <div className="custom-tooltip">
        <img
          src="/assets/img/nav/btnTooltip.svg"
          alt="tooltip"
          style={{ padding: '5px' }}
        />
        <div className="custom-tooltip-text">this is tooltip</div>
      </div>
    </div>
  )
}

export default Tooltip
