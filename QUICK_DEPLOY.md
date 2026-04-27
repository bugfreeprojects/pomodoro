# FocusTomato - Quick Deployment Guide

## Option 1: Railway.app (EASIEST - Recommended) ⭐

1. Go to https://railway.app
2. Sign up with GitHub
3. Create new project → "Deploy from GitHub repo"
4. Select `pomodoro` repository
5. Railway auto-detects Python and deploys automatically
6. Get your free URL instantly!

**That's it!** Your app will be live.

---

## Option 2: Render.com

1. Go to https://render.com
2. Sign up with GitHub
3. Create new "Web Service"
4. Connect your GitHub repo
5. Settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python backend/server.py`
6. Deploy!

Free tier gives you 750 hours/month.

---

## Option 3: Vercel (Frontend Only)

Works if you deploy backend separately:

1. Go to https://vercel.com
2. Import your GitHub repo
3. Deploy frontend instantly
4. Point to separate backend URL

---

## Option 4: Heroku (Deprecated but still works)

```bash
# Install Heroku CLI, then:
git init
heroku login
heroku create your-app-name
git push heroku main
```

---

## Before Deploying

Make sure these files exist:

1. **Create `requirements.txt`** in root:
```
# (optional - platforms auto-detect if needed)
```

2. **Create `Procfile`** in root:
```
web: cd backend && python server.py
```

3. **Commit to GitHub:**
```bash
git add .gitignore Procfile
git commit -m "Add deployment files"
git push origin main
```

---

## Recommended: Use Railway 🚀

It's the **easiest and fastest**:
1. Visit railway.app
2. Click "New Project" 
3. Connect your GitHub
4. Select `pomodoro` repo
5. Auto-deploys!

You get a live URL immediately.

---

Need help with a specific platform?
