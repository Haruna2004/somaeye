# roadmap & gaps

the system is solid, but it's not perfect. here is where we are lacking and what we want to do next.

### current gaps
- **no database**: right now, incidents are only stored in logs and the browser's current session. if you refresh, the incident log clears. 
- **single camera**: it only supports one webcam stream at a time. 
- **browser dependent**: the vision pipeline needs a browser tab open to "push" the video frames. it can't run in the background without the ui. 

### future ideas
- **persistent storage**: add a lightweight database (like sqlite) to keep a history of every alert. 
- **mobile alerts**: send a notification to a phone when a high-priority alert triggers. 
- **multi-camera support**: allow the server to handle multiple websocket feeds. 
- **cloud reasoning**: option to switch between local and cloud models based on battery or performance needs. 
