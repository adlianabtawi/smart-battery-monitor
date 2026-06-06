# ⚡ Smart Battery Monitor

A lightweight Windows app that automatically controls a **Tuya smart plug** based on your laptop's battery level — keeping your battery healthy by avoiding full charges and deep discharges.

> Built by [Adli Anabtawi](https://github.com/adlianabtawi) with the help of [Claude](https://claude.ai) by Anthropic

> 🛠️ **[Open the App Generator](https://adlianabtawi.github.io/smart-battery-monitor/)** — fill in your Tuya credentials and download a ready-to-run app in seconds

## 💡 Background

My laptop does not have any built-in software to limit charging, and since I did not want to damage the battery by keeping it at 100% all the time, I started using a Windows app called **Smart Battery Monitor**, which controlled a Deltaco smart plug, which is a Tuya rebranded smart plug, to automatically stop and start charging based on the battery level. It worked great, until one day it simply stopped working after Tuya updated their API, and the app was no longer maintained.

Rather than waiting for a fix that would never come, I decided to build my own, open source, so anyone can use it and build on top of it.

I also move my laptop between different locations and plugs regularly, so I needed a way to quickly switch between smart plugs without any hassle. That multi-plug support is built right in.

---

## ✨ Features

- 🔋 **Automatic plug control** — turns the plug on/off based on your battery level
- 🌍 **Multi-language** — Swedish, English, German, French, Spanish, Norwegian, Danish, Finnish
- 🔌 **Multiple plugs** — switch between several smart plugs easily
- 🪟 **System tray** — runs quietly in the background, minimizes to tray
- 🚀 **Start with Windows** — optional autostart toggle built in
- ⚙️ **Configurable limits** — set your own min/max battery thresholds
- 🛠️ **App Generator** — build your own personalized version via the web tool

---

## 🖥️ Screenshots

| Main window                           | System tray                   |
| ------------------------------------- | ----------------------------- |
| ![Main window](images/screenshot.png) | ![Tray icon](images/tray.png) |

---

## 🔌 Compatible Smart Plugs

This app works with any smart plug running on the **Tuya platform**, including a large number of rebranded products sold under different names. If your plug works with the **Smart Life** or **Tuya Smart** app on your phone, it will work here.

### Tuya-based brands (should be compatible)

| Brand                    | Notes                                                                   |
| ------------------------ | ----------------------------------------------------------------------- |
| **Deltaco Smart Home**   | Official Tuya partner — SH-P01, SH-P03USB2 and others confirmed working |
| **Nous**                 | Popular Tuya-based brand, widely used                                   |
| **Moes**                 | Tuya-based, available on Amazon                                         |
| **Woox**                 | Tuya-based smart home brand                                             |
| **Nedis SmartLife**      | Uses Tuya platform under the hood                                       |
| **Lidl Silvercrest**     | Many models are Tuya-based                                              |
| **Immax**                | Tuya-based, common in Europe                                            |
| **BlitzWolf**            | Popular Tuya-based brand                                                |
| **Gosund**               | Tuya-based, widely available                                            |
| **Sonoff** (some models) | Some Wi-Fi models use Tuya                                              |
| **LSC Smart Connect**    | Action store brand, Tuya-based                                          |
| **Wesmartify**           | Official Tuya partner                                                   |

> **Not sure if your plug is compatible?**
> If it pairs with the **Smart Life** or **Tuya Smart** app, it will work. You can also check [the Tuya developer portal](https://iot.tuya.com) — if your device shows up there after linking your Smart Life account, you're good to go.

---

## 🚀 Quick Start

### 1. Install Python

Download from [python.org](https://www.python.org/downloads/) — make sure to check **"Add Python to PATH"** during installation.

### 2. Install dependencies

```bash
pip install tinytuya psutil pillow pystray
```

### 3. Set up a Tuya developer account

1. Go to [iot.tuya.com](https://iot.tuya.com) and create a free account
2. Click **Cloud → Development → Create Cloud Project**
3. Fill in:
    - **Industry:** Smart Home
    - **Development Method:** Smart Home
    - **Data Center:** Central Europe _(or your region)_
4. Authorize the default API services and click **Create**
5. Go to **Devices → Link Tuya App Account → Add App Account**
6. Scan the QR code with your **Smart Life app** on your phone
7. Copy your **Client ID** and **Client Secret** from the project Overview page
8. Copy the **Device ID** for your smart plug from the Devices tab

> ⚠️ **Important:** Make sure the Data Center in your Tuya project matches the region your Smart Life account is registered in. You can check your region in the Smart Life app under Me → Settings → Account and Security → Region.

### 4. Generate your app

Use the **[App Generator](https://adlianabtawi.github.io/smart-battery-monitor/)** to fill in your credentials and download a ready-to-run `battery_monitor.py`.

Or manually edit the `DEFAULT_CONFIG` section at the top of `battery_monitor.py`:

```python
DEFAULT_CONFIG = {
    "api_key":    "YOUR_CLIENT_ID",
    "api_secret": "YOUR_CLIENT_SECRET",
    "api_region": "eu",
    "devices": [
        {"id": "YOUR_DEVICE_ID", "name": "My Plug"},
    ],
    "min_level": 20,   # Turn plug ON when battery drops to this %
    "max_level": 80,   # Turn plug OFF when battery reaches this %
}
```

### 5. Run the app

Double-click `Start_Battery_Monitor.bat`, or run:

```bash
pythonw battery_monitor.py
```

---

## 🔧 How it works

The app polls your battery every **30 seconds**. When the battery drops below the minimum threshold and the plug is off, it turns the plug on to start charging. When the battery reaches the maximum threshold, it turns the plug off to stop charging.

```
Battery < min% and not charging  →  Turn plug ON  🟢
Battery ≥ max% and charging      →  Turn plug OFF 🔴
```

This keeps your battery in the optimal charge range, which helps extend its lifespan over time.

---

## 🌍 Supported Languages

| Code | Language |
| ---- | -------- |
| `sv` | Svenska  |
| `en` | English  |
| `de` | Deutsch  |
| `fr` | Français |
| `es` | Español  |
| `no` | Norsk    |
| `da` | Dansk    |
| `fi` | Suomi    |

---

## 📦 Dependencies

| Package                                            | Purpose                      |
| -------------------------------------------------- | ---------------------------- |
| [tinytuya](https://github.com/jasonacox/tinytuya)  | Tuya Cloud API communication |
| [psutil](https://github.com/giampaolo/psutil)      | Reading battery status       |
| [Pillow](https://python-pillow.org/)               | Generating tray icon         |
| [pystray](https://github.com/moses-palmer/pystray) | System tray support          |

---

## ❓ Troubleshooting

**The plug doesn't respond**

- Make sure your Tuya IoT Core subscription is active: iot.tuya.com → Cloud → My Services
- Check that the Data Center in your project matches your Smart Life account region
- Try clicking "Refresh now" in the app to force a poll

**"Data center is suspended" error**

- Go to iot.tuya.com → Cloud → My Services → IoT Core → Extend/Renew

**The tray icon doesn't appear**

- Make sure `pystray` and `pillow` are installed: `pip install pystray pillow`

**App doesn't start with Windows**

- Run the app once manually, then check the "Start with Windows" checkbox inside the app

---

## 📄 License

MIT License — free to use, modify and distribute.

---

## 🙏 Credits

- [tinytuya](https://github.com/jasonacox/tinytuya) by Jason Cox — Tuya Cloud API communication
- [psutil](https://github.com/giampaolo/psutil) by Giampaolo Rodolà — battery and system monitoring
- [Pillow](https://github.com/python-pillow/Pillow) by the Pillow contributors — image generation for tray icon
- [pystray](https://github.com/moses-palmer/pystray) by Moses Palmér — system tray support
