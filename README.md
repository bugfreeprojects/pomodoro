# FocusTomato - Pomodoro Timer with Rewards

A beautiful, modern Pomodoro timer with user accounts, reward system, and stunning visual design.

## Features

✨ **Stunning UI**
- Dark/light themes with real background images
- Smooth animations and glass-morphism design
- Responsive layout (desktop & mobile)

⏱️ **Pomodoro Timer**
- 25 min focus / 5 min short break / 15 min long break
- Task management with progress tracking
- Session history and statistics

🏆 **Reward System**
- Earn points for completed focus sessions
- Track streaks and achievements
- Level progression system
- Points saved to cloud

🎧 **Focus Tools**
- Binaural beat audio frequencies (Alpha, Beta, Gamma, Theta)
- Box breathing exercise (4-4-4-4)
- Daily motivation quotes

👤 **User Accounts**
- Secure login/register
- Per-user progress tracking
- Cloud sync of rewards and stats

---

## Quick Start

### 1. Backend Setup
```bash
cd backend
python server.py
```
Server runs on http://127.0.0.1:8000

### 2. Open the App
```bash
# Open in browser:
file:///path/to/pomodoro/pomodoro-timer.html

# Or serve it:
python -m http.server 8080
# Then visit http://localhost:8080/pomodoro-timer.html
```

### 3. Create Account
- Click "Create account"
- Fill username, email, password
- Start focusing!

---

## Technology Stack

**Frontend:**
- HTML5 + CSS3 + Vanilla JavaScript
- No frameworks - super lightweight
- Responsive design

**Backend:**
- Python 3.8+
- Built-in HTTP server (no external dependencies!)
- SQLite database
- RESTful API

---

## Project Structure

```
pomodoro/
├── pomodoro-timer.html   # Main app (frontend + UI)
├── backend/
│   ├── server.py         # Python backend server
│   └── rewards.db        # SQLite database (auto-created)
├── DEPLOYMENT.md         # Deployment guide
└── README.md            # This file
```

---

## API Endpoints

### Authentication
- `POST /api/register` - Create new account
- `POST /api/login` - Login user

### Rewards (require auth token)
- `GET /api/rewards` - Get user's reward data
- `POST /api/session/complete` - Record completed session

---

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Space | Play/Pause timer |
| R | Reset timer |
| N | New task |
| F | Toggle focus tools |
| T | Toggle themes |
| Esc | Close modals/panels |

---

## Customization

### Change Timer Durations
Edit in `pomodoro-timer.html`:
```javascript
const S={
  dur:{
    focus: 25*60,    // Change 25 to desired minutes
    short: 5*60,
    long: 15*60
  }
}
```

### Add Custom Themes
Add to `THEMES` array in HTML:
```javascript
{
  id: 'custom',
  name: 'My Theme',
  sub: 'Describe it',
  img: 'https://image-url.jpg',
  overlay: 'linear-gradient(...)',
  particle: '200,100,150',
  light: false,
  thumb: 'https://thumb-url.jpg'
}
```

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- **Vercel** - Quick frontend hosting
- **Heroku** - All-in-one deployment
- **Railway** - Python-optimized hosting
- **DigitalOcean** - Full control VPS
- **PythonAnywhere** - Python-specific hosting
- **Render** - Modern serverless

TL;DR: Push to GitHub → connect to Vercel/Railway/Render → done!

---

## Development

### Run backend in debug mode:
```bash
cd backend
python -u server.py  # -u for unbuffered output
```

### Test API:
```bash
curl -X POST http://127.0.0.1:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","password":"pass123"}'
```

---

## License

MIT - Feel free to use and modify!

---

## Tips for Best Experience

1. **Use headphones** for binaural beats
2. **Silence notifications** during sessions
3. **Save multiple tasks** for batching
4. **Check achievements** daily for motivation
5. **Back up data** before major changes

---

## Troubleshooting

**Backend won't start?**
- Check Python version: `python --version` (need 3.8+)
- Ensure port 8000 is free: `lsof -i :8000` (Mac/Linux)

**Frontend can't reach backend?**
- Make sure backend is running on 127.0.0.1:8000
- Check browser console for errors (F12)

**Login doesn't work?**
- Clear browser cache/cookies
- Check if backend is running
- Verify internet connection (for images)

**Timer keeps pausing?**
- Check browser sleep settings
- Disable power-saving mode
- Ensure tab stays active

---

## Contributing

Ideas? Improvements?
- Fork the repo
- Make your changes
- Submit a pull request!

---

Enjoy focusing! 🍅
