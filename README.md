# ZenoMyID Telegram Bot 🤖

ZenoMyID 4.0 Android App ကို Telegram Bot အနေနဲ့ ပြောင်းရေးထားသော Bot

## Features ✨

| Feature | App Activity | Bot Command |
|---------|-------------|-------------|
| Login (OTP) | LoginActivity + OtpActivity | `/start` |
| Dashboard | DashboardActivity | `/dashboard` |
| Loyalty Points | PointsExchangeActivity | `/loyalty` |
| Points History | PointsHistoryActivity | `/history` |
| Points Exchange | PointsExchangeActivity | `/exchange` |
| Extend Expiry | PointsExtendDialog | `/extend` |
| Account Info | AccountsActivity | `/account` |
| MyID GO Game | MyIDGoActivity | `/myidgo` |
| Daily Quest | DailyClaimActivity | `/dailyquest` |
| Daily Claim | DailyClaimActivity | `/dailyclaim` |
| Data Packages | DataPackagesActivity | `/datapackages` |
| Multi-Account | AccountManager | Inline buttons |

## API Endpoints (apis.mytel.com.mm) 🌐

- **Auth**: `/myid/authen/v1.0/...`
- **Customer**: `/cpm/v1.0/api/customer`
- **Loyalty**: `/loyalty/api/v3.1/...`
- **Data Packages**: `/csm/v1.0/api/vas-package/...`
- **Daily Quest**: `/daily-quest-v3/api/v3/daily-quest/...`
- **MyID GO**: `pubapi-mygov2.mtgmm.co/v1/engine/...`
- **Account Detail**: `/account-detail/api/v1.2/...`

## Setup 🚀

### 1. Requirements Install
```bash
pip install -r requirements.txt
```

### 2. .env ဖိုင် ဖန်တီးပါ
```bash
cp .env.example .env
```
`.env` ဖိုင် ဖွင့်ပြီး BOT_TOKEN ထည့်ပါ:
```
BOT_TOKEN=12345678:ABCdefGhijklMNOpqrstUVWxyz
```

### 3. Bot Run
```bash
python bot.py
```

## Bot Commands 📋

```
/start          - Login / Welcome
/login          - Login (alias)
/addaccount     - Add another account
/dashboard      - Main dashboard
/loyalty        - Loyalty points info
/history        - Points transaction history
/exchange       - Exchange points for packs
/extend         - Extend points expiry
/account        - Account profile
/myidgo         - MyID GO game
/dailyquest     - Daily quest status
/dailyclaim     - Claim daily reward
/datapackages   - Browse data packages
/cancel         - Cancel current action
```

## Login Flow 🔐

```
/start
  → Phone input (09xxxxxxxx)
  → check-account API
      ├── Registered → get-otp → OTP input → validate-otp → Dashboard
      └── New user   → register-request → OTP input → validate-otp → Dashboard
```

## Multi-Account Support 👥

- `/addaccount` ဖြင့် account များ ထပ်ထည့်နိုင်သည်
- Dashboard မှ account switch လုပ်နိုင်သည်
- Data is saved in `./data/sessions.json`

## Project Structure 📁

```
bot/
├── bot.py              # Main entry point
├── requirements.txt
├── .env.example
├── api/
│   └── client.py       # ApiClient.java replica
├── session/
│   └── manager.py      # SessionManager + AccountManager replica
└── handlers/
    ├── auth.py          # Login + OTP flow
    ├── dashboard.py     # Main screen
    ├── loyalty.py       # Points management
    ├── account.py       # Profile management
    ├── myidgo.py        # MyID GO game
    ├── daily_quest.py   # Daily quests
    └── data_packages.py # VAS packages
```

## Notes ⚠️

- Bot သည် Mytel Myanmar ၏ APIs ကို တိုက်ရိုက် ချိတ်ဆက်သည်
- SSL verification disabled ရှိသည် (Mytel API compatibility)
- Session data သည် local `data/sessions.json` တွင် သိမ်းဆည်းသည်
- MyID GO game token အတွက် app မှ တစ်ကြိမ် login ဝင်ရပါမည်
