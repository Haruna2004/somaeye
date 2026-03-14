const video = document.getElementById("webcam");
const processedImg = document.getElementById("processedFeed");
const connectionStatus = document.getElementById("connectionStatus");
const connectionDot = document.getElementById("connectionDot");
const systemStatus = document.getElementById("systemStatus");
const systemDot = document.getElementById("systemDot");
const log = document.getElementById("log");
const pauseBtn = document.getElementById("pauseBtn");
const promptInput = document.getElementById("promptInput");
const savePromptBtn = document.getElementById("savePromptBtn");

let ws;
let mediaStream = null;
const canvas = document.getElementById("captureCanvas");
const ctx = canvas.getContext("2d");
let isProcessing = false;

// Load persistent prompt
const savedPrompt = localStorage.getItem("ai_surveillance_prompt");
if (savedPrompt) {
    promptInput.value = savedPrompt;
    fetch("/set-prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: savedPrompt })
    });
}

async function startWebcam() {
    try {
        if (document.getElementById("aiOverlay").classList.contains("paused")) {
            return;
        }
        mediaStream = await navigator.mediaDevices.getUserMedia({
            video: { 
                width: { ideal: 1280 }, 
                height: { ideal: 720 },
                aspectRatio: 1.7777777778
            }
        });
        video.srcObject = mediaStream;
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            initWebSocket();
        }
    } catch (err) {
        console.error("Webcam error:", err);
    }
}

function stopWebcam() {
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        video.srcObject = null;
        mediaStream = null;
    }
}

function initWebSocket() {
    ws = new WebSocket("ws://" + window.location.host + "/ws");
    ws.onopen = () => {
        connectionStatus.innerText = "Sentry Connected";
        connectionDot.className = "status-dot dot-online";
        isProcessing = false;
        requestAnimationFrame(streamFrames);
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        isProcessing = false;

        if (data.image) {
            processedImg.src = "data:image/jpeg;base64," + data.image;
            requestAnimationFrame(streamFrames);
        } else if (data.status) {
            requestAnimationFrame(streamFrames);
        }

        if (data.alert) {
            const item = document.createElement('div');
            item.className = 'alert-item';
            item.innerHTML = `<strong>ALERT:</strong> ${data.alert}`;
            log.prepend(item);
        }
    };

    ws.onclose = () => {
        connectionStatus.innerText = "Sentry Offline";
        connectionDot.className = "status-dot dot-offline";
        setTimeout(initWebSocket, 2000);
    };
}

function streamFrames() {
    if (isProcessing || !ws || ws.readyState !== WebSocket.OPEN || document.getElementById("aiOverlay").classList.contains("paused")) {
        if (!document.getElementById("aiOverlay").classList.contains("paused")) {
            requestAnimationFrame(streamFrames);
        }
        return;
    }

    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    ctx.drawImage(video, 0, 0);

    const frame = canvas.toDataURL("image/jpeg", 0.5);
    isProcessing = true;
    ws.send(JSON.stringify({ image: frame.split(',')[1] }));
}

savePromptBtn.onclick = async () => {
    const p = promptInput.value;
    savePromptBtn.disabled = true;
    savePromptBtn.innerText = "Deploying...";

    localStorage.setItem("ai_surveillance_prompt", p);
    try {
        await fetch("/set-prompt", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: p })
        });
    } finally {
        savePromptBtn.disabled = false;
        savePromptBtn.innerText = "Deploy";
    }
};

pauseBtn.onclick = async () => {
    pauseBtn.disabled = true;
    const isCurrentlyPaused = document.getElementById("aiOverlay").classList.contains("paused");

    await fetch("/toggle-pause", { method: "POST" });

    if (!isCurrentlyPaused) {
        stopWebcam();
    } else {
        await startWebcam();
    }
    location.reload();
};

startWebcam();
