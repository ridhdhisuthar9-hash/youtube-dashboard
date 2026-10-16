# Put the dashboard online (optional)

You do **not** need this to present your project. `START_WEB_APP.py` runs the same web page on your own
laptop at `http://localhost:8000`, and that is the safest way to demo in front of a professor.

Do this part only if you want a public link that anyone can open from any phone or computer.

> **Honest note:** the app itself is fully tested. The hosting steps below follow Render.com's normal
> workflow, but I could not test them from my side because it needs your own accounts. Screens and button
> names on the website may differ slightly. If a step looks different, follow the website's wording.

## What you need (all free)

1. A **YouTube Data API key** (README, section 4).
2. A **GitHub** account: <https://github.com/signup>
3. A **Render** account: <https://render.com> (you can sign in with GitHub)

## Steps

**1. Put the project on GitHub**
1. On GitHub click **New repository**, name it `channel-dashboard`, keep it **Public**, click **Create repository**.
2. Click **uploading an existing file**.
3. Unzip the project on your computer, open the folder, select **everything inside it** and drag it into the GitHub page.
   Do **not** upload a file named `.env` (it holds your secret key). The `output` folder is not needed either.
4. Click **Commit changes**.

**2. Create the web service on Render**
1. In Render click **New → Web Service** and choose your `channel-dashboard` repository.
2. Fill in:
   - **Runtime / Language:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
   - **Instance type:** Free
3. Open **Environment** (or *Advanced → Add Environment Variable*) and add:
   - **Key:** `YOUTUBE_API_KEY`  **Value:** your API key
4. Click **Create Web Service** and wait a few minutes. Render shows your public address, for example
   `https://channel-dashboard-xxxx.onrender.com`.

**3. Use it**
Open the address, type a channel, press **Show dashboard**. Share the address with anyone.

## Good to know

- **Free services go to sleep** when nobody uses them. The first visit after a break can take about a minute to wake up.
- **Your key stays on the server.** Visitors never see it, and the page never asks them for one.
- **The free YouTube allowance is 10,000 units per day.** One channel costs about 4 units, and searching by plain
  name costs 100. The app remembers each result for an hour and limits each visitor to 12 new searches per
  10 minutes, so a classroom can use it without running out.
- **Never put the key in a file on GitHub.** Only in Render's *Environment* box.
- To switch it off, delete the service in Render.
