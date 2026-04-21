const video = document.getElementById("webcam");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const connectionStatus = document.getElementById("connectionStatus");
const connectionDot = document.getElementById("connectionDot");
const camLabel = document.getElementById("camLabel");

// Generate a random camera ID
const cameraId = "remote_cam_" + Math.floor(Math.random() * 1000);
camLabel.innerText = "Camera ID: " + cameraId;

let ws;
let mediaStream = null;
const canvas = document.getElementById("captureCanvas");
const ctx = canvas.getContext("2d");
let isProcessing = false;

async function startWebcam() {
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
            video: { 
                width: { ideal: 640 }, 
                height: { ideal: 480 },
                facingMode: "environment" // Prefer back camera on mobile
            }
        });
        video.srcObject = mediaStream;
        
        startBtn.disabled = true;
        stopBtn.disabled = false;
        
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            initWebSocket();
        }
    } catch (err) {
        console.error("Webcam error:", err);
        alert("Could not access camera. Please check permissions.");
    }
}

function stopWebcam() {
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        video.srcObject = null;
        mediaStream = null;
    }
    if (ws) {
        ws.close();
    }
    
    startBtn.disabled = false;
    stopBtn.disabled = true;
    connectionStatus.innerText = "Offline";
    connectionDot.className = "status-dot dot-offline";
}

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/camera/${cameraId}`);
    
    ws.onopen = () => {
        connectionStatus.innerText = "Transmitting to Server...";
        connectionDot.className = "status-dot dot-online";
        isProcessing = false;
        requestAnimationFrame(streamFrames);
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        isProcessing = false;

        // When the server successfully processes, we send the next frame
        if (data.status === "ok") {
            requestAnimationFrame(streamFrames);
        }
    };

    ws.onclose = () => {
        if (mediaStream) { // Only try to reconnect if we haven't manually stopped
            connectionStatus.innerText = "Reconnecting...";
            connectionDot.className = "status-dot dot-offline";
            setTimeout(initWebSocket, 2000);
        }
    };
}

function streamFrames() {
    if (isProcessing || !ws || ws.readyState !== WebSocket.OPEN || !mediaStream) {
        if (mediaStream) requestAnimationFrame(streamFrames);
        return;
    }

    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    ctx.drawImage(video, 0, 0);

    const frame = canvas.toDataURL("image/jpeg", 0.5); // 0.5 quality for better mobile performance
    isProcessing = true;
    ws.send(JSON.stringify({ image: frame.split(',')[1] }));
}

startBtn.onclick = startWebcam;
stopBtn.onclick = stopWebcam;
