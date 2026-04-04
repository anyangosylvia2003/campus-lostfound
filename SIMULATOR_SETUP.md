# AT Simulator Setup — Demo Guide

Use this to show the system sending real OTPs to a phone screen during a demo,
without spending money or needing a real SIM card.

---

## Step 1 — Create a free Africa's Talking account

1. Go to https://africastalking.com and sign up
2. Verify your email and log in
3. You are automatically in **Sandbox** mode — no payment needed

---

## Step 2 — Get your Sandbox API key

1. In the AT dashboard, click **Settings → API Key**
2. Copy the **Sandbox API Key** (it looks like: `atsk_...`)

---

## Step 3 — Open the Simulator

**Option A — Web browser (easiest for a demo):**
1. In the AT dashboard, click **Sandbox → Simulator**
2. A phone screen appears in your browser
3. Note the phone number shown on the simulator (e.g. `+254700000000`)

**Option B — Android app:**
1. Install the **Africa's Talking Simulator** app from the Play Store
2. Log in with your AT account
3. Note the phone number shown in the app

---

## Step 4 — Configure your .env

Open your `.env` file and set:

```
DEBUG=True
SMS_BACKEND=simulator
AT_USERNAME=sandbox
AT_API_KEY=atsk_your_sandbox_key_here
AT_PHONE=+254700000000
```

> `AT_PHONE` must match **exactly** the number shown in your AT simulator.
> All SMS will be redirected to this number so they appear on the simulator screen.

Restart the Django server after saving:
```bash
python manage.py runserver
```

---

## Step 5 — Test it

1. Open your browser to `http://127.0.0.1:8000`
2. Go to **Login → Forgot Password**
3. Enter any registered phone number and submit
4. Watch the OTP appear on the AT simulator screen
5. Copy the code and enter it in the browser to complete the reset

---

## What the demo looks like

```
Browser                          AT Simulator (web/app)
──────────────────────           ──────────────────────────────────────
Enter phone: 0712345678    →     📱 Incoming SMS from CAMPUSLF:
[Send Code]                          "Your Campus Lost & Found
                                      password reset code is: 483921
                                      Expires in 10 minutes."

Enter code: 483921
[Verify]
✅ Password updated!
```

---

## Switching back to console mode

When you're done with the demo, set `SMS_BACKEND=console` in `.env`
to go back to printing OTPs in the terminal (no network needed).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| SMS doesn't appear on simulator | Check `AT_PHONE` matches the simulator number exactly, including `+254` prefix |
| `AT_API_KEY is not set` error | Copy the sandbox key from AT dashboard → Settings → API Key |
| `NameResolutionError` | Your network is blocking the AT API — switch to `SMS_BACKEND=console` |
| Simulator shows wrong number | Make sure `AT_USERNAME=sandbox` (not your real username) |
