# contribution guide

whether you're a human developer or an ai agent, here is how you can help improve the system.

### for everyone
- **test first**: before you change how yolo or gemini works, run the current system to make sure it's stable. 
- **follow the principles**: read `docs/principles.md`. we care about clean logs and simple code. 
- **one change at a time**: don't bundle a css fix with a change to the reasoning engine. keep your updates focused.

### adding new features
1. **propose a plan**: if you're an ai, write an implementation plan. if you're human, just a quick outline in a new doc is fine. 
2. **backend first**: get the logic working in `app.py` or the specific worker before you touch the frontend. 
3. **verify**: make sure the blackbox logs show your new feature working as expected. 

### for ai agents
- be proactive but don't overreach. 
- if you're refactoring, explain *why* it helps maintainability. 
- don't ignore the style guides in `docs/principles.md`. 
