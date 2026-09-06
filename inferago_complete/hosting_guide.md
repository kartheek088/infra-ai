# Free Cloud Hosting Guide: Supabase + Render + Vercel

This guide walks through deploying Inferago 100% free using:
- **Database**: [Supabase](https://supabase.com) (Free Tier Managed PostgreSQL)
- **Backend API**: [Render](https://render.com) (Free Tier Web Service with HTTPS)
- **Frontend App**: [Vercel](https://vercel.com) (Free Tier Edge CDN & Hosting)

---

## Step 1: Database on Supabase (Free)

1. Create a free account on [Supabase](https://supabase.com) and click **"New project"**.
2. Set your **Database Password** (remember this password).
3. Once created, go to **Project Settings** → **Database** → **Connection String** → **URI**.
4. Select **Session Pooler (IPv4)** or **Direct Connection**:
   ```
   postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
   ```
   *(Inferago automatically handles converting this to `postgresql+asyncpg://` behind the scenes).*

---

## Step 2: Backend on Render (Free)

1. Push your project to a GitHub repository (e.g. `github.com/your-user/inferago`).
2. Log into [Render](https://render.com) and click **"New" → "Web Service"**.
3. Connect your GitHub repository.
4. Configure the Web Service settings:
   - **Name**: `inferago-backend`
   - **Region**: Same region as your Supabase DB (e.g., Frankfurt / Ohio / Singapore)
   - **Root Directory**: `inferago_complete/backend` (or `backend` if pushed from backend folder)
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt && alembic upgrade head
     ```
   - **Start Command**:
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type**: `Free`

5. Under **Environment Variables**, add:
   | Key | Value | Notes |
   | :--- | :--- | :--- |
   | `DATABASE_URL` | `postgresql://postgres...` | Your Supabase connection string from Step 1 |
   | `SECRET_KEY` | *(Click 'Generate' or enter a 32+ char random string)* | Used for JWT signing |
   | `CORS_ORIGINS` | `*` | Or your Vercel URL: `https://inferago.vercel.app` |
   | `PYTHON_VERSION` | `3.11.9` | Recommended Python version |

6. Click **"Deploy Web Service"**.
   - Render will build the app, run Alembic migrations against Supabase, and start FastAPI.
   - Your backend URL will be: `https://inferago-backend.onrender.com`
   - Test it at: `https://inferago-backend.onrender.com/docs`

---

## Step 3: Frontend on Vercel (Free)

1. Go to [Vercel](https://vercel.com) and click **"Add New..." → "Project"**.
2. Import the same GitHub repository.
3. Configure the project:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click `Edit` and select `inferago_complete/frontend` (or `frontend`).
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Expand **Environment Variables** and add:
   | Key | Value |
   | :--- | :--- |
   | `VITE_API_URL` | `https://inferago-backend.onrender.com` (Your Render URL from Step 2) |
5. Click **"Deploy"**.
   - Vercel will build and assign you a live HTTPS domain (e.g., `https://inferago-frontend.vercel.app`).

---

## Step 4: Webhook Configuration for Automation Platforms

Once deployed, point your automation platforms to your live Render backend URL:

- **n8n**: `https://inferago-backend.onrender.com/api/webhook/n8n?api_key=inf_live_YOUR_KEY`
- **Make**: `https://inferago-backend.onrender.com/api/webhook/make?api_key=inf_live_YOUR_KEY`
- **Zapier**: `https://inferago-backend.onrender.com/api/webhook/zapier?api_key=inf_live_YOUR_KEY`
- **Custom**: `POST https://inferago-backend.onrender.com/api/webhook/custom?api_key=inf_live_YOUR_KEY`
