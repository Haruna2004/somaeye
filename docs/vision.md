# vision

the goal is simple: build a security system that actually understands what it sees. 

we aren't just motion tracking. plenty of cameras do that and give you too many false alerts. our vision is to combine fast, local tracking with the reasoning of a large language model. 

here is what we want to achieve:
- **natural rules**: you should be able to tell your camera what to look for in plain english. 
- **broad input sources**: moving beyond webcams to support cctv, ip cameras, and even satellite imagery or multimedia recording logs.
- **situational intelligence**: the system should act as a "third eye," identifying complex scenarios and providing real-time, prompt-based reports rather than just simple alerts.
- **investigative capacity**: extending the underlying reasoning to historical footage through a dedicated interface for forensic search and analysis.
- **zero-cost standby**: the system shouldn't cost anything when nothing is happening. that's why we use yolo to "gate" the more expensive ai calls.
- **real privacy**: when you click pause, the camera should actually turn off. 

basically, we want to make surveillance smart enough to know the difference between a person lingering by your door and just a branch moving in the wind—providing actionable intelligence for security, management, and investigation.
