# architecture

the system has three main parts that talk to each other. 

### 1. the frontend (the dashboard)
built with html, css, and vanilla javascript. it uses your browser to grab the webcam feed and sends it to the server through a websocket. we kept it simple so it's fast and doesn't have much lag. 

### 2. the perception engine (yolo)
this runs locally on your machine using vision_worker.py. it's the sentry. it tracks people and objects in real-time. it tells us *where* things are and *who* is moving. 

### 3. the reasoning core (gemini)
this is the brain. it only wakes up when the perception engine sees a person. it takes the tracking logs and occasionally an image to figure out if your rules are being broken. 

### major decisions
- **websockets over http**: we needed speed. websockets let us stream video frames without the overhead of repeating requests. 
- **blackbox logging**: we added a system that saves everything to a folder called "blackbox". it rotates every 30 minutes so we don't end up with one massive file that's impossible to read. 
- **macOS core**: we use the native `say` command for audio alerts. it's fast and works offline. 
