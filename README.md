# ANVAYA SAṂHATI

### AI-Powered Hospital Operating System
**Connecting every part of a hospital into one intelligent system.**

ANVAYA SAṂHATI is an AI-enabled Hospital Operating System designed to connect major hospital workflows through a unified platform. It brings together clinical, operational, administrative, and intelligent decision-support capabilities into a common architecture.

---

## Overview

Modern hospitals often operate through disconnected systems for patient records, laboratory services, pharmacy, ICU operations, insurance, and government healthcare workflows.

**ANVAYA SAṂHATI** aims to provide a unified operating layer that connects these components and enables intelligent coordination between them.

The platform is designed around:

- Unified hospital workflows
- AI-assisted clinical and operational intelligence
- Multi-agent coordination
- Secure role-based access
- Structured healthcare interoperability
- Predictive analytics
- Auditability and traceability

---

## Core Modules

### 🏥 Electronic Health Records
Centralized patient and clinical information management for hospital workflows.

### 🧪 Laboratory Integration
Connects laboratory workflows and diagnostic information with the broader patient record.

### 💊 Pharmacy Intelligence
Supports pharmacy workflows and demand-oriented analytics.

### 🏨 ICU & Hospital Operations
Provides operational intelligence for critical-care and hospital resource management.

### 🤖 AI / Multi-Agent Coordination
AI components coordinate information and tasks across different hospital domains.

### 📊 Predictive Analytics
The project includes trained ML components for areas such as:

- Patient risk prediction
- Readmission risk
- Length-of-stay prediction
- Bed occupancy prediction
- Pharmacy demand prediction
- Patient deterioration prediction

### 🛡️ Security & Access Control
The architecture includes:

- RBAC
- JWT/OAuth-based authentication
- Audit logging
- Environment-based configuration

### 🔗 Healthcare Interoperability
The architecture is designed around healthcare standards and integrations including:

- HL7 FHIR
- DICOM
- ABDM / ABHA

---

## System Architecture

```text
                    ┌──────────────────────────┐
                    │      ANVAYA SAṂHATI      │
                    │     Hospital OS Layer    │
                    └────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
   ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
   │     EHR     │       │ Laboratory  │       │  Pharmacy   │
   └─────────────┘       └─────────────┘       └─────────────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     AI / ML Layer       │
                    │ Prediction & Intelligence│
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ Multi-Agent Coordination │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
         ICU / Beds          Insurance          Government
         Operations          Workflows          Healthcare
```

---

## Technology Stack

### Frontend
- React
- Vite
- TypeScript
- Tailwind CSS

### Backend
- Python
- FastAPI
- PostgreSQL
- Alembic

### Data & Infrastructure
- PostgreSQL
- Redis
- Object Storage
- Docker / Docker Compose

### AI / Machine Learning
- Pandas
- NumPy
- XGBoost
- Random Forest
- Isolation Forest
- NLP / LLM components
- Embeddings
- Vector database / RAG architecture

### Healthcare Standards
- HL7 FHIR
- DICOM
- ABDM / ABHA

---

## Project Structure

```text
anvaya-samhati/
│
├── backend/
│   ├── app/
│   ├── alembic/
│   ├── ml/
│   └── ...
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── ...
│
├── TRAINED MODEL/
│   ├── models/
│   ├── datasets/
│   └── notebooks/
│
├── database/
│
├── docker-compose.yml
├── start_anvaya.ps1
├── PHASE_STATUS.md
├── .env.example
├── .gitignore
└── README.md
```

> Large trained model binaries are intentionally excluded from Git version control where required by GitHub file-size limits. The source code and project structure remain in the repository.

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Gigabyteofshlok/anvaya-samhati.git
cd anvaya-samhati
```

### 2. Configure environment variables

Copy the example configuration:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Update `.env` with your local PostgreSQL credentials and application configuration.

**Never commit `.env` or real secrets to GitHub.**

---

## Backend Setup

Create/activate your Python environment and install the backend dependencies used by the project.

Then start the FastAPI application.

A typical development server is:

```bash
uvicorn backend.app.main:app --reload
```

The exact entry point may depend on the current backend configuration.

---

## Frontend Setup

Install dependencies:

```bash
cd frontend
npm install
```

Start the Vite development server:

```bash
npm run dev
```

The frontend development server is configured around the Vite development workflow.

---

## Docker

The repository includes:

```text
docker-compose.yml
```

Docker Compose can be used to orchestrate the project's supporting services according to the configuration in that file.

---

## AI / ML Models

The project contains trained ML components for hospital intelligence use cases including:

| Model | Purpose |
|---|---|
| Patient Risk | Patient risk prediction |
| Readmission Risk | Readmission prediction |
| Length of Stay | Hospital stay prediction |
| Bed Occupancy | Occupancy forecasting |
| Pharmacy Demand | Demand forecasting |
| Deterioration | Patient deterioration prediction |

Large binary model artifacts are not committed to the public repository when they exceed GitHub's normal file-size limits.

---

## Security

ANVAYA SAṂHATI is designed with security-oriented components including:

- Role-Based Access Control (RBAC)
- JWT/OAuth authentication
- Audit logging
- Environment-based secrets
- Database-backed application architecture

For deployment, replace development credentials and placeholder secrets with securely generated production values.

---

## Development Status

This repository contains the ongoing implementation of **ANVAYA SAṂHATI — Hospital OS**.

The project is being developed as a modular healthcare platform combining:

**Hospital Operations + Healthcare Data + AI/ML + Multi-Agent Coordination**

See [`PHASE_STATUS.md`](PHASE_STATUS.md) for the current implementation status.

---

## Vision

> **One hospital. One intelligent operating layer.**

ANVAYA SAṂHATI aims to reduce fragmentation between hospital departments and transform disconnected healthcare workflows into a coordinated, intelligent system.

---

## Author

**SHLOK KULKARNI**

GitHub: [@Gigabyteofshlok](https://github.com/Gigabyteofshlok)

---

## License

License information will be added to this repository separately.
