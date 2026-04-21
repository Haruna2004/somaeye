const connectionStatus = document.getElementById("connectionStatus");
const connectionDot = document.getElementById("connectionDot");
const systemStatus = document.getElementById("systemStatus");
const systemDot = document.getElementById("systemDot");
const log = document.getElementById("log");
const pauseBtn = document.getElementById("pauseBtn");
const promptInput = document.getElementById("promptInput");
const savePromptBtn = document.getElementById("savePromptBtn");

let ws;

// Tabs
const tabConfigBtn = document.getElementById("tabConfigBtn");
const tabMonitorBtn = document.getElementById("tabMonitorBtn");
const localConfigSection = document.getElementById("localConfigSection");
const monitorSection = document.getElementById("monitorSection");
const monitorGrid = document.getElementById("monitorGrid");
const emptyGridState = document.getElementById("emptyGridState");

function toggleEmptyState() {
    if (monitorGrid.children.length === 0) {
        monitorGrid.style.display = "none";
        emptyGridState.style.display = "block";
    } else {
        monitorGrid.style.display = "grid";
        emptyGridState.style.display = "none";
    }
}

tabConfigBtn.onclick = () => {
    tabConfigBtn.classList.add("active");
    tabMonitorBtn.classList.remove("active");
    localConfigSection.style.display = "grid";
    monitorSection.style.display = "none";
};

tabMonitorBtn.onclick = () => {
    tabMonitorBtn.classList.add("active");
    tabConfigBtn.classList.remove("active");
    monitorSection.style.display = "block";  // or whatever layout works
    localConfigSection.style.display = "none";
};

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

// Webcam handling is moved to sender.html/sender.js
// Dashboard now only acts as a remote stream viewer

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const viewerId = "viewer_" + Math.floor(Math.random() * 10000);
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/dashboard/${viewerId}`);
    ws.onopen = () => {
        connectionStatus.innerText = "Sentry Connected";
        connectionDot.className = "status-dot dot-online";
        isProcessing = false;
        requestAnimationFrame(streamFrames);
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        isProcessing = false;

        if (data.type === "camera_frame") {
            const camId = data.camera_id;
            
            // All cameras are now remote, push to monitor grid
            let remoteImg = document.getElementById("remote_" + camId);
            if (!remoteImg) {
                const card = document.createElement("div");
                card.className = "card";
                card.id = "card_" + camId;
                card.innerHTML = `
                    <div class="card-title">
                        <span class="inference-dot"></span>
                        Camera: ${camId}
                    </div>
                    <div class="video-wrapper">
                        <img id="remote_${camId}" src="data:image/jpeg;base64,${data.image}" alt="Remote feed" style="width: 100%; height: auto; border-radius: 8px;">
                    </div>
                `;
                monitorGrid.appendChild(card);
                toggleEmptyState();
            } else {
                remoteImg.src = "data:image/jpeg;base64," + data.image;
            }
        } else if (data.type === "camera_disconnected") {
            const camCard = document.getElementById("card_" + data.camera_id);
            if (camCard) {
                camCard.style.transition = "opacity 0.3s ease";
                camCard.style.opacity = "0";
                setTimeout(() => {
                    camCard.remove();
                    toggleEmptyState();
                }, 300);
            }
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

// No local streaming needed for dashboard

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
    await fetch("/toggle-pause", { method: "POST" });
    location.reload();
};

initWebSocket();
