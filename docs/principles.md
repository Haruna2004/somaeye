# coding principles

we want this codebase to stay easy to work on. here is the standard we're following:

- **keep it simple**: don't add a library if you can write a few lines of clean python or javascript to do the job. 
- **clear logs**: every major action should be logged. info level for things that matter to the user, and debug level for technical telemetry that goes into the blackbox file. 
- **modular design**: if a file gets over 300 lines, it's probably time to break it up. `app.py` is the hub, but the logic for vision, reasoning, and audio belongs in their own files. 
- **fail loudly in logs, quietly in ui**: if a frame fails to process, log the error so we can fix it, but keep the video stream moving for the user. 
- **human-readable variables**: use names like `latest_frame_bytes` instead of `lfb`. we want the next developer to understand the code without a map. 
- **no placeholders**: if a feature isn't ready, don't put it in. we only ship things that actually work. 
