<div align="center">

# 🏥 ANVAYA SAṂHATI

### AI-Powered Hospital Operating System

**Connecting every part of a hospital into one intelligent system.**

<br>

[![Project](https://img.shields.io/badge/Project-ANVAYA%20SA%E1%B9%82HATI-4F46E5?style=for-the-badge)](https://github.com/Gigabyteofshlok/anvaya-samhati)
[![Status](https://img.shields.io/badge/Status-Active%20Development-16A34A?style=for-the-badge)](https://github.com/Gigabyteofshlok/anvaya-samhati)
[![License](https://img.shields.io/badge/License-To%20Be%20Added-64748B?style=for-the-badge)](https://github.com/Gigabyteofshlok/anvaya-samhati)
[![GitHub](https://img.shields.io/badge/GitHub-Gigabyteofshlok-181717?style=for-the-badge&logo=github)](https://github.com/Gigabyteofshlok)

<br>

> **One hospital. One intelligent operating layer.**

</div>

---

## 🏥 About ANVAYA SAṂHATI

**ANVAYA SAṂHATI** is an AI-enabled **Hospital Operating System** designed to connect clinical, administrative, operational, and intelligent decision-support workflows through a unified platform.

Instead of treating hospital departments as isolated systems, ANVAYA SAṂHATI provides a common operating layer for:

**EHR → Laboratory → Pharmacy → ICU → Radiology → Billing & Insurance → Inventory → Analytics → AI Agents**

The platform combines **real-time hospital workflows, predictive machine learning, LLM/RAG capabilities, multi-agent coordination, healthcare interoperability, and secure access control**.

---

## 🏥 Project Sponsorship

<div align="center">

### **Supported by Morya Multispeciality Hospital, Pune**

**Real-world healthcare context • Hospital workflow validation • Practical deployment perspective**

</div>

ANVAYA SAṂHATI is developed with support from **Morya Multispeciality Hospital, Pune**, providing a real-world healthcare context for designing and validating hospital workflow and AI-assisted operational capabilities.

---

## ✨ What Makes It Different

| 🏥 Unified | 🤖 Intelligent | 🔗 Interoperable | 🛡️ Secure | 📈 Predictive |
|:---:|:---:|:---:|:---:|:---:|
| Connects hospital departments | AI & multi-agent coordination | HL7 FHIR / DICOM / ABDM | RBAC + JWT/OAuth + audit logs | ML-driven hospital analytics |

### Core principles

- **Unified Hospital Platform** — connect departments through a common system.
- **AI-Native Architecture** — integrate ML, LLM, RAG and specialized AI agents.
- **Real-Time Intelligence** — turn operational data into actionable insights.
- **Healthcare Interoperability** — support healthcare standards and ecosystem integration.
- **Security by Design** — role-based access, authentication and auditability.
- **Modular Architecture** — independently extensible hospital services.
- **Deployment Ready** — designed around Docker, APIs and scalable backend services.

---

# 🧩 Hospital Modules

<div align="center">

| 👤 Patient Management | 📅 Appointments | 🧾 EHR | 🧪 Laboratory |
|---|---|---|---|
| Patient records & workflows | Scheduling & coordination | Electronic health records | Lab workflows & reports |

| 💊 Pharmacy | 🩻 Radiology | 💳 Billing & Insurance | ❤️ ICU |
|---|---|---|---|
| Pharmacy management | Imaging workflows / PACS | Financial & insurance workflows | Critical-care operations |

| 📦 Inventory | 📊 Analytics | 🧠 AI Assistant | 🔐 Administration |
|---|---|---|---|
| Inventory & supply chain | Dashboards & reporting | Intelligent assistance | RBAC & audit controls |

</div>

---

# 🤖 AI & Intelligence Layer

ANVAYA SAṂHATI is designed as an **AI-first hospital platform**, rather than a traditional hospital information system with AI added later.

### 🧠 Predictive Machine Learning

Current ML-oriented capabilities include:

- **Patient Risk Prediction**
- **Readmission Risk Prediction**
- **Length-of-Stay Prediction**
- **Bed Occupancy Prediction**
- **Pharmacy Demand Forecasting**
- **Patient Deterioration Prediction**

### 🕵️ Anomaly Detection

Identify unusual patterns across hospital operations and clinical/operational data.

### 💬 NLP + LLM

Designed for:

- Clinical note understanding
- Report summarization
- Natural-language interaction
- Healthcare knowledge assistance

### 📚 RAG Pipeline

A retrieval-augmented architecture for connecting AI responses with hospital knowledge, guidelines and structured information.

### 🤝 Multi-Agent Coordination

Specialized agents can collaborate across hospital functions:

```text
                    ┌─────────────────────┐
                    │   AI Orchestrator   │
                    └──────────┬──────────┘
                               │
       ┌───────────┬───────────┼───────────┬───────────┐
       ▼           ▼           ▼           ▼           ▼
   Clinical     Operations   Pharmacy   Insurance   Analytics
     Agent        Agent       Agent       Agent       Agent
       │           │           │           │           │
       └───────────┴───────────┼───────────┴───────────┘
                               ▼
                     Hospital Service Layer
```

---

# 🏗️ Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                         FRONTEND                             │
│              React + Vite + TypeScript + Tailwind            │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                       API GATEWAY                            │
│                         FastAPI                              │
└──────────────────────────────┬───────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
       ┌─────────────┐  ┌─────────────┐  ┌──────────────┐
       │ Hospital    │  │ Multi-Agent │  │ AI / ML      │
       │ Services    │  │ Coordination│  │ Intelligence │
       └──────┬──────┘  └──────┬──────┘  └──────┬───────┘
              │                │                 │
              └────────────────┼─────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    DATA & STORAGE LAYER                      │
│ PostgreSQL • Redis • Object Storage • Vector Database        │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    EXTERNAL ECOSYSTEM                        │
│        HL7 FHIR • DICOM • ABDM/ABHA • Insurance              │
└──────────────────────────────────────────────────────────────┘
```

---

# 🛠️ Technology Stack

<div align="center">

### Frontend

[![React](https://skillicons.dev/icons?i=react)](https://react.dev/)
[![Vite](https://skillicons.dev/icons?i=vite)](https://vite.dev/)
[![TypeScript](https://skillicons.dev/icons?i=typescript)](https://www.typescriptlang.org/)
[![Tailwind](https://skillicons.dev/icons?i=tailwind)](https://tailwindcss.com/)

### Backend & Data

[![Python](https://skillicons.dev/icons?i=python)](https://www.python.org/)
[![FastAPI](https://skillicons.dev/icons?i=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://skillicons.dev/icons?i=postgres)](https://www.postgresql.org/)
[![Redis](https://skillicons.dev/icons?i=redis)](https://redis.io/)
[![Docker](https://skillicons.dev/icons?i=docker)](https://www.docker.com/)

### AI / ML / Healthcare

![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-EC4E20?style=for-the-badge)
![Random Forest](https://img.shields.io/badge/Random%20Forest-16A34A?style=for-the-badge)
![RAG](https://img.shields.io/badge/RAG-7C3AED?style=for-the-badge)
![LLM](https://img.shields.io/badge/LLM-2563EB?style=for-the-badge)
![HL7 FHIR](https://img.shields.io/badge/HL7-FHIR-0EA5E9?style=for-the-badge)
![DICOM](https://img.shields.io/badge/DICOM-0891B2?style=for-the-badge)
![ABDM](https://img.shields.io/badge/ABDM%2FABHA-FF6B00?style=for-the-badge)

</div>

---

# 📁 Project Structure

```text
anvaya-samhati/
│
├── backend/                 # FastAPI backend
│   ├── app/                 # API, services & application logic
│   ├── alembic/             # Database migrations
│   └── ml/                  # ML services & model integration
│
├── frontend/                # React + Vite frontend
│   ├── src/
│   ├── public/
│   └── ...
│
├── TRAINED MODEL/           # Training datasets, notebooks & artifacts
│
├── database/                # Database-related resources
│
├── docker-compose.yml       # Container orchestration
├── start_anvaya.ps1         # Windows startup script
├── PHASE_STATUS.md          # Implementation status
├── .env.example             # Safe environment template
├── .gitignore
└── README.md
```

> 🔒 Large trained model binaries are intentionally excluded from Git version control where required by GitHub's file-size limits. Local model files are not deleted by this repository configuration.

---

# 🚀 Getting Started

## 1️⃣ Clone

```bash
git clone https://github.com/Gigabyteofshlok/anvaya-samhati.git
cd anvaya-samhati
```

## 2️⃣ Configure environment

```powershell
Copy-Item .env.example .env
```

Update `.env` with your local PostgreSQL credentials and other development settings.

> ⚠️ **Never commit `.env` or real API keys, passwords, tokens or production secrets.**

## 3️⃣ Backend

Create/activate your Python environment and install the project's backend dependencies.

Example development server:

```bash
uvicorn backend.app.main:app --reload
```

## 4️⃣ Frontend

```bash
cd frontend
npm install
npm run dev
```

## 5️⃣ Docker

From the project root:

```bash
docker compose up --build
```

---

# 🧪 ML Models

| Model | Purpose |
|---|---|
| 🧑‍⚕️ Patient Risk | Patient risk prediction |
| 🔄 Readmission Risk | Readmission prediction |
| 🛏️ Length of Stay | Hospital stay prediction |
| 🏥 Bed Occupancy | Occupancy forecasting |
| 💊 Pharmacy Demand | Demand forecasting |
| ⚠️ Deterioration | Patient deterioration prediction |

The repository keeps **source code, training resources and project structure** under version control while excluding oversized binary artifacts where necessary.

---

# 🔐 Security & Privacy

Healthcare software requires security to be treated as a core architectural concern.

ANVAYA SAṂHATI incorporates or is designed around:

- 🔑 JWT / OAuth authentication
- 👥 Role-Based Access Control
- 📝 Audit logging
- 🔒 Environment-based secrets
- 🗄️ Secure database architecture
- 🔗 Controlled API access
- 🏥 Healthcare interoperability standards

For production deployment, development credentials and placeholder secrets must be replaced with securely generated production configuration.

---

# 🗺️ Development Roadmap

```text
Phase 1  ████████████████████  Core System
Phase 2  ███████████████░░░░░  AI Integration
Phase 3  ███████████░░░░░░░░░  Hospital Deployment
Phase 4  ███████░░░░░░░░░░░░░  Multi-Hospital Scale
```

### Planned direction

- [x] Unified hospital platform foundation
- [x] Backend + frontend architecture
- [x] ML model integration structure
- [x] Healthcare interoperability architecture
- [ ] Expand multi-agent orchestration
- [ ] Expand RAG / knowledge services
- [ ] Strengthen hospital deployment workflows
- [ ] Multi-hospital scalability
- [ ] Production-grade observability and MLOps

---

# 📊 Project Vision

ANVAYA SAṂHATI aims to evolve from a collection of hospital modules into an **intelligent operating layer for healthcare organizations**.

```text
                 DATA
                  │
                  ▼
        ┌──────────────────┐
        │  Hospital OS     │
        │ ANVAYA SAṂHATI   │
        └────────┬─────────┘
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
     AI        Agents    Analytics
       │         │         │
       └─────────┼─────────┘
                 ▼
       Better Hospital Decisions
                 │
                 ▼
       Better Patient Outcomes
```

> **From disconnected hospital systems → to one intelligent healthcare ecosystem.**

---

# 🤝 Contributing

Contributions, ideas, issues and technical discussions are welcome.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Open a pull request

---

# 👨‍💻 Author

<div align="center">

### SHLOK KULKARNI

AI & Data Science • Healthcare AI • Machine Learning • Full-Stack Development

[![GitHub](https://img.shields.io/badge/GitHub-Gigabyteofshlok-181717?style=for-the-badge&logo=github)](https://github.com/Gigabyteofshlok)

</div>

---

<div align="center">

### 🏥 Sponsored by Morya Multispeciality Hospital, Pune

**Built for a smarter, connected healthcare future.**

<br>

⭐ **Star the repository if you find the project interesting.**

</div>
