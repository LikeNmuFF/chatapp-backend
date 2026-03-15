# 🚀 Deploying Blip to Render.com

No credit card needed. Takes about 10 minutes.

---

## Your Final Folder Structure

Before uploading, make sure your project looks like this:

```
chatapp/
├── app.py               ← use the updated one from this package
├── requirements.txt     ← use the one from this package
├── render.yaml          ← use the one from this package
└── templates/
    ├── chat.html
    ├── login.html
    └── register.html
```

---

## Step 1 — Push your code to GitHub

Render deploys from GitHub. If you haven't used Git before:

```bash
# Inside your chatapp/ folder:
git init
git add .
git commit -m "first commit"
```

Then go to https://github.com/new and create a **new public repo** called `blip-chat`.

```bash
git remote add origin https://github.com/YOUR_USERNAME/blip-chat.git
git branch -M main
git push -u origin main
```

---

## Step 2 — Sign up on Render

1. Go to **https://render.com**
2. Click **Get Started for Free**
3. Sign up with your **GitHub account** (easiest — links your repos automatically)

---

## Step 3 — Create a New Web Service

1. From your Render dashboard click **+ New → Web Service**
2. Click **Connect** next to your `blip-chat` GitHub repo
3. Fill in the form:

| Field | Value |
|---|---|
| **Name** | `blip-chat` |
| **Region** | `Singapore` (closest to Philippines 🇵🇭) |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT --timeout 120 app:app` |
| **Plan** | `Free` |

4. Scroll down to **Environment Variables** and add:

| Key | Value |
|---|---|
| `SECRET_KEY` | any long random string, e.g. `blip-super-secret-2024-xkq9` |

5. Click **Create Web Service**

---

## Step 4 — Wait for the build (~2 mins)

Render will:
- Pull your code from GitHub
- Install dependencies
- Start your app with Gunicorn + eventlet

Watch the logs — you should see:
```
==> Starting service with 'gunicorn --worker-class eventlet ...'
[INFO] Starting gunicorn
[INFO] Listening at: http://0.0.0.0:10000
```

---

## Step 5 — Open your app 🎉

Your app is live at:
```
https://blip-chat.onrender.com
```
(or whatever name you chose)

---

## Redeploying after changes

Every time you push to GitHub, Render **auto-redeploys**:

```bash
git add .
git commit -m "update something"
git push
```

That's it — Render detects the push and redeploys automatically.

---

## ⚠️ Important: Free Plan Limitations

### App goes to sleep after 15 minutes of inactivity
When someone visits after a long idle period, it takes ~50 seconds to wake up.
This is normal on the free plan. Paid plans ($7/month) keep the app always-on.

### Chat history resets on redeploy
SQLite lives inside Render's filesystem which resets on every deploy.
To persist data, upgrade to a paid plan and use Render's persistent disk,
or migrate to PostgreSQL (Render offers a free Postgres instance).

### One worker only
The start command uses `-w 1` (one worker). Do NOT change this to more
workers — it will break WebSocket sessions.

---

## Troubleshooting

**"ModuleNotFoundError: No module named eventlet"**
→ Make sure your `requirements.txt` includes `eventlet>=0.35.0`

**WebSockets not connecting**
→ Check that your start command includes `--worker-class eventlet`

**App crashes on start**
→ Check Render logs. Most likely a missing package in requirements.txt

**"Application failed to respond"**
→ The free app is waking up — wait 60 seconds and refresh
