export default function Header({ isConnected }) {
  return (
    <header className="header">
      <div className="header-brand">
        <div className="header-mark">IS</div>
        <div>
          <div className="header-name">InsightSQL</div>
          <div className="header-sub">HPE GreenLake SAP Operations</div>
        </div>
      </div>
      <div className="header-status">
        <div className={`status-dot ${!isConnected ? 'off' : ''}`} />
        {isConnected ? 'Live' : 'Reconnecting…'}
      </div>
    </header>
  );
}
