# 🛡️ IntelliGuard
### **Smart System Monitor & Optimization Suite**

IntelliGuard is a modern, full-featured **desktop system monitoring and optimization tool** built using **Python + PySide6**.  
It provides real-time system analytics, health predictions, cleanup tools, performance insights, and system stability tracking — all inside a minimal and elegant UI.

---

## 🚀 Features

### 🔥 **1. CPU & RAM Monitoring**
- Real-time CPU & RAM graphs  
- Peak usage detection  
- Top 3 CPU & RAM heavy processes  
- Application stability scoring  
- Updated every 5 seconds  

---

### 🔋 **2. Battery Health & Age Prediction**
- Reads:  
  - Design Capacity  
  - Full Charge Capacity  
  - Wear Level  
  - Cycle Count  
- Daily battery capacity logging  
- Predicts battery health for next 6 months using trendline  
- Machine-learning style slope calculation  
- Clean summary popup

---

### ♻️ **3. Smart Cleanup Center**
#### **Auto Cleanup**
- Automatically deletes old files from Downloads  
- User-defined retention period (ex: 15 days)  
- Runs daily at scheduled time

#### **Duplicate File Finder**
- Scans Downloads folder  
- Detects exact duplicates using SHA-256 hashing  
- Select + Delete duplicates  
- Clear selection UI

---

### 💾 **4. Storage Analyzer**
- Detects all system partitions  
- Shows Used vs Free space  
- Clean bar-graph visualization  
- Displays total GB + usage percentages  

---

### 🌐 **5. Network Activity Monitor**
- Real-time download & upload KB/s  
- Peak usage + timestamps  
- Shows adapter details (speed, MTU, IP, duplex)  
- Historical line graph  

---

### ⚙️ **6. Application Stability Analyzer**
- Scores apps using:  
  - CPU variance  
  - Memory spikes  
  - Runtime fluctuations  
  - Background behavior  
- Extracts window title (actual app name)  
- Highlights unstable applications  

---

### 📘 **7. Daily System Story**
A beautifully formatted daily summary including:

- CPU avg + peak  
- RAM avg + peak  
- Total network data usage  
- Busiest moment  
- Most used apps  
- Estimated system health score  
- Short human-readable system report  

---

## 🖼️ Screenshots

### 🏠 Home Screen  
<img width="1172" height="772" alt="Home Page" src="https://github.com/user-attachments/assets/9ac2f9ff-5005-4f50-9bf3-39e7b66baf08" />

### 🧹 Auto Cleanup  
<img width="1172" height="772" alt="Auto-Cleanup" src="https://github.com/user-attachments/assets/071b3725-7580-470a-8151-057e9eac5bd0" />

### 🗂️ Duplicate File Finder  
<img width="1172" height="772" alt="Duplicate Files in dowload" src="https://github.com/user-attachments/assets/1f8687c6-2b78-480f-aa98-c55797084c38" />

### 🔋 Battery Health  
<img width="565" height="612" alt="Battery Health Summary" src="https://github.com/user-attachments/assets/30d96424-40ba-45be-9fdd-70d3a1bae935" />

### 📡 Network Monitor  
<img width="1172" height="772" alt="Network Details" src="https://github.com/user-attachments/assets/30521b04-74f8-43e5-9045-0bd5f224232f" />

### 💾 Storage Overview  
<img width="1172" height="772" alt="Storage Details" src="https://github.com/user-attachments/assets/47a57727-c67d-41ae-b114-e0d3dcf56b6d" />

### 🔧 Stability Analyzer  
<img width="1065" height="602" alt="App stability Check" src="https://github.com/user-attachments/assets/4c2f415a-9adf-4b8b-bae2-3f5fa04ec6f5" />

### 📘 Daily System Story  
<img width="581" height="702" alt="Daily Summary" src="https://github.com/user-attachments/assets/12051525-615a-4b42-ad84-cd6041395f32" />

---

## 🏗️ Project Structure

IntelliGuard/
│
├── backend/
│   ├── monitors/
│   │   ├── system_monitor.py
│   │   ├── battery_monitor.py
│   │   ├── disk_monitor.py
│   │   └── network_monitor.py
│   ├── analytics/
│   │   ├── battery_predictor.py
│   │   ├── stability_analyzer.py
│   │   └── daily_story.py
│   ├── cleaners/
│   │   ├── downloads_cleaner.py
│   │   └── duplicate_finder.py
│   ├── config.py
│   ├── logger.py
│   └── data_store.py
│
├── ui/
│   ├── main_window.ui
│   ├── main_window.py
│   └── icons/
│
├── reports/
│
├── main.py
├── requirements.txt
└── README.md

---

## ⚙️ Tech Stack

| Component        | Technology     |
|------------------|----------------|
| UI Framework     | PySide6        |
| Plotting         | Matplotlib     |
| System Metrics   | psutil         |
| Data Logs        | JSON           |
| Trend Analysis   | numpy (optional)|

---

## 📦 Installation

### 1️⃣ Clone the Repository
git clone https://github.com/prakash0067/IntelliGuard.git
cd IntelliGuard

### 2️⃣ (Optional) Create Virtual Environment
python -m venv venv
venv\Scripts\activate     # On Windows

### 3️⃣ Install Requirements
pip install -r requirements.txt

### 4️⃣ Run the Application
python main.py

---

## 📁 Where Data is Stored

| Type | File | Purpose |
|------|------|---------|
| Battery logs | reports/battery_health_log.json | Daily battery health entries |
| Daily story logs | reports/YYYY-MM-DD.json | Used for Daily System Story |
| System logs | system.log | Logs for debugging & history |

---

## 🤝 Developed By

- **Archita Mishra**  
- **Himaksh Yadav**  
- **Anush Kulal**  
- **Md. Smir Alam**  
- **Prakash Sirvi**

---

## 🌟 Why IntelliGuard?

IntelliGuard is a complete system-monitoring toolkit designed to:

✔ Optimize storage  
✔ Predict battery health  
✔ Track real-time performance  
✔ Detect unstable applications  
✔ Monitor network activity  
✔ Provide daily system stories  
✔ Deliver a modern and clean UI  

A powerful choice for students, developers, and anyone who wants deeper insights into their system.

---


