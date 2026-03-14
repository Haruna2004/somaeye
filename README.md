# ai surveillance system

this is a smart security system that uses yolo for real-time tracking and gemini for behavioral reasoning. it lets you set security rules using plain english prompts.

## how it works
1. **webcam feed**: the frontend grabs your camera and streams frames to the server.
2. **yolo tracking**: the backend tracks people and objects locally.
3. **gemini reasoning**: if a person is seen, the system asks gemini if any of your rules are being broken.
4. **audio alerts**: if an alert triggers, the system speaks to you using the macOS `say` command.

## setup
1. get a gemini api key.
2. put it in a `.env` file: `GEMINI_API_KEY=your_key_here`
3. install the requirements (fastapi, uvicorn, ultralytics, opencv-python, google-generativeai).
4. run the app: `python app.py`
5. open `http://localhost:8000` in your browser.

## docs
we've put together some detailed guides in the `docs/` folder:
- [vision & purpose](docs/vision.md)
- [how the system is built](docs/architecture.md)
- [coding principles](docs/principles.md)
- [how to contribute](docs/contribution.md)
- [what's next](docs/roadmap.md)

## blackbox
all technical details and latencies are recorded in the `blackbox/` directory. check `audit.log` if you need to debug something or see how fast the system is running.
