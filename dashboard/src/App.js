import React, { useState, useEffect } from 'react';
import './App.css';

// The URL of your FastAPI backend
const API_URL = 'http://127.0.0.1:8000';
// The WebSocket URL
const WS_URL = 'ws://127.0.0.1:8000/ws';

function App() {
  const [detections, setDetections] = useState([]);
  const [barrierStatus, setBarrierStatus] = useState('UNKNOWN');

  // --- Effect to fetch initial data and connect to WebSocket ---
  useEffect(() => {
    // 1. Fetch all historical data on component mount
    fetch(`${API_URL}/`) 
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => {
        if (Array.isArray(data)) {
          // Sort data by timestamp, newest first
          const sortedData = data.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
          setDetections(sortedData);
        } else {
          console.error("Fetched data is not an array:", data);
        }
      })
      .catch(error => console.error("Error fetching initial data:", error));

    // 2. Fetch initial barrier status
    updateBarrierStatus();

    // 3. Connect to WebSocket
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    // This is where the "sync" happens!
    ws.onmessage = (event) => {
      try {
        const newDetection = JSON.parse(event.data);
        console.log('New detection from WebSocket:', newDetection);
      
        setDetections(prevDetections => [newDetection, ...prevDetections]);
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected. Attempting to reconnect...');
      
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    
    return () => {
      ws.close();
    };
  }, []); 

  // --- Handler Functions for Barrier Control ---
  // These functions are already integrated with the buttons below.
  const updateBarrierStatus = () => {
    console.log("Fetching barrier status...");
    fetch(`${API_URL}/barrier/status`)
      .then(res => res.json())
      .then(data => {
        console.log("Status:", data);
        setBarrierStatus(data.status || 'ERROR');
      })
      .catch((err) => {
        console.error("Fetch status error:", err);
        setBarrierStatus('OFFLINE');
      });
  };

  const handleOpenBarrier = () => {
    console.log("Sending OPEN command...");
    fetch(`${API_URL}/barrier/open`, { method: 'GET' })
      .then(res => res.json())
      .then(data => {
        console.log("Open response:", data);
        setTimeout(updateBarrierStatus, 500); 
      })
      .catch(err => console.error("Open error:", err));
  };

  const handleCloseBarrier = () => {
    console.log("Sending CLOSE command...");
    fetch(`${API_URL}/barrier/close`, { method: 'GET' })
      .then(res => res.json())
      .then(data => {
        console.log("Close response:", data);
        setTimeout(updateBarrierStatus, 500);
      })
      .catch(err => console.error("Close error:", err));
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Admin Dashboard</h1>
      </header>
      
      <main className="container">
        
        {/* --- Left Column (Video + Controls) --- */}
        <div className="column-left">
          
          {/* --- Video Feed Card --- */}
          <section className="card video-card">
            <h2>Live Camera Feed</h2>
            <div className="video-container">
              <img 
                src={`${API_URL}/video_feed`} 
                alt="Live ANPR Feed"
                onError={(e) => { 
                  e.target.style.display = 'none'; 
                  console.error("Video stream error or not available"); 
                
                }}
              />
            </div>
          </section>

          {/* --- Barrier Controls Card --- */}
          <section className="card controls-card">
            <h2>Barrier Controls</h2>
            <div className="status-display">
              Current Status: <strong>{barrierStatus}</strong>
            </div>
            <div className="button-group">
              <button className="control-button open" onClick={handleOpenBarrier}>
                Open Barrier
              </button>
              <button className="control-button close" onClick={handleCloseBarrier}>
                Close Barrier
              </button>
              <button className="control-button status" onClick={updateBarrierStatus}>
                Refresh Status
              </button>
            </div>
          </section>
        </div>

        {/* --- Right Column (Logs) --- */}
        <div className="column-right">
          <section className="card log-card">
            <h2>Real-Time Detections Log</h2>
            <div className="log-table-container">
              <table className="log-table">
                <thead>
                  <tr>
                    <th>Number Plate</th>
                    <th>Status</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {detections.map((det, index) => (
                    <tr key={det._id || index} className={det.status === 'UNAUTHORIZED' ? 'unauthorized' : 'authorized'}>
                      <td>{det.number_plate}</td>
                      <td>{det.status}</td>
                      <td>{new Date(det.timestamp).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>

      </main>
    </div>
  );
}

export default App;

