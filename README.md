# Arkmaster123 Discord Bot

## 🚀 Overview
Welcome to **Arkmaster123 Discord Bot**, a feature-rich, containerised Discord bot designed for **seamless automation and interaction**. This bot integrates with **Flowise AI** and **Make.com**, leverages **MongoDB for persistent chat history**, and provides **real-time trade summaries** for users.

## 🏗️ Project Structure
```
arkmaster123-discordbot/
├── Dockerfile
├── main.py
├── renderdockerfile
└── requirements.txt
```

### 🔹 `Dockerfile`
A production-ready **Docker setup** optimised for a lightweight **Python 3.10 Slim** environment.

### 🔹 `main.py`
The heart of the bot – handling **Discord interactions**, **Flask web server**, **MongoDB logging**, and **API requests** to external services.

### 🔹 `renderdockerfile`
A variation of `Dockerfile` specifically optimised for **deployment on Render.com**.

### 🔹 `requirements.txt`
Dependency list for the bot’s environment, ensuring smooth execution of all required libraries.

---

## ⚡ Features & Functionality
✅ **Discord Bot Integration** – Handles **private messaging**, **trade summaries**, and **interactive buttons**.
✅ **Flask Web Server** – Keeps the bot **alive** and accessible.
✅ **MongoDB Integration** – Logs and retrieves **chat histories**.
✅ **Flowise AI & Make.com Integration** – Fetches responses and checks user **subscription status**.
✅ **Trade Summary Button** – Allows users to fetch their latest trade summaries with a click.
✅ **Docker Support** – Fully containerised for **quick deployment**.
✅ **Optimised for Render.com** – Pre-configured for **Render hosting**.

---

## 🔧 Installation & Setup
### **1️⃣ Clone the Repository**
```bash
git clone https://github.com/yourusername/arkmaster123-discordbot.git
cd arkmaster123-discordbot
```

### **2️⃣ Set Up Virtual Environment (Optional but Recommended)**
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

### **3️⃣ Install Dependencies**
```bash
pip install -r requirements.txt
```

### **4️⃣ Set Up Environment Variables**
Create a `.env` file and populate it with:
```ini
DISCORD_BOT_TOKEN=your_bot_token
FLOWISE_API_URL=your_flowise_api_url
FLOWISE_API_KEY=your_flowise_api_key
MAKE_WEBHOOK_URL=your_make_webhook_url
TRADE_SUMMARY_WEBHOOK_URL=your_trade_summary_webhook_url
MONGO_URI=your_mongodb_uri
```

### **5️⃣ Run the Bot**
```bash
python main.py
```

---

## 🐳 Running in Docker
### **Build the Image**
```bash
docker build -t arkmaster123-discordbot .
```

### **Run the Container**
```bash
docker run -d -p 8080:8080 --env-file .env arkmaster123-discordbot
```

---

## 🌍 Deployment on Render
1. **Push your repository to GitHub**.
2. **Connect to Render.com**, create a new **web service**, and select the repository.
3. **Use the `renderdockerfile` for deployment**.
4. Set **environment variables** in the Render dashboard.
5. Deploy! 🚀

---

## 📜 License
This project is licensed under the **MIT License** – feel free to modify and distribute! 🎉

---

## 🤝 Contributing
Pull requests and suggestions are welcome! Open an issue if you find bugs or have feature requests. 💡

---

## 📬 Contact
Got questions? Reach out via Discord or open an issue on GitHub! 📨

