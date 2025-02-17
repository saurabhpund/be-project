function MobileMonitor() {
    const [warningCount, setWarningCount] = useState(0);
    const { sessionToken } = useParams();
  
    useEffect(() => {
      const sendHeartbeat = async () => {
        try {
          await fetch(`${baseURL}:5000/mobile/ping?token=${sessionToken}`, {
            method: 'POST'
          });
        } catch (error) {
          console.error('Heartbeat failed:', error);
        }
      };
  
      // Send heartbeat every 30 seconds
      const interval = setInterval(sendHeartbeat, 30000);
      
      // Handle visibility changes
      const handleVisibilityChange = () => {
        if (document.hidden) {
          setWarningCount(prev => prev + 1);
          if (warningCount >= 3) {
            // Trigger exam violation
            fetch(`${baseURL}:5000/exam/violation`, {
              method: 'POST',
              body: JSON.stringify({ sessionToken, violation: 'tab_switch' })
            });
          }
        }
      };
  
      document.addEventListener('visibilitychange', handleVisibilityChange);
      return () => {
        clearInterval(interval);
        document.removeEventListener('visibilitychange', handleVisibilityChange);
      };
    }, [sessionToken, warningCount]);
  
    return (
      <div style={{ pointerEvents: 'none' }}>
        {/* Existing UI */}
        {warningCount > 0 && (
          <div className="warning-banner">
            Warning: Tab must remain active ({3 - warningCount} remaining)
          </div>
        )}
      </div>
    );
  }