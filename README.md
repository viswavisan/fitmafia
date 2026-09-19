# FitMafia Application

**FitMafia** is a Python Flask backend service integrated with Oracle Cloud Infrastructure (OCI). It provides APIs for user/fitness management, database management (PostgreSQL & Oracle Autonomous Database), database schema/data migrations, health checking, and OCI Object Storage integration for media/file uploads.

---

## ☁️ OCI Instance & Infrastructure Information

> **Note:** Maintain your OCI compute instance and resource details in this section for quick operational reference.

### 1. Compute Instance Details
| Parameter | Value / Details |
| :--- | :--- |
| **Instance Name** | instance-20260416-1931 |
| **OCID** | `ocid1.instance.oc1.ap-hyderabad-1.anuhsljrt6jgmficn2pn6hj66zsc5c7mcdycucrjvyoy5ba6tpcbdpcqzmka` |
| **Region** | ap-hyderabad-1 |
| **Availability / Fault Domain** | FD-3 |
| **Shape** | VM.Standard.E2.1.Micro - 1 OCPU, 1GB RAM |
| **Operating System** | Oracle Linux |
| **Public IP Address** | `140.245.230.89` |
| **Private IP Address** | `10.0.0.71` |
| **SSH Key / Connection** | `ssh -i ~/.ssh/id_rsa opc@<PUBLIC_IP>` |

### 2. Network & Security Settings
* **VCN (Virtual Cloud Network):** *default route table for VCN*
* **Subnet:** *public subnet-VCN*
* **Ingress Rules / Open Ports:**
  * `22/TCP`: SSH Remote Access
  * `5000/TCP`: Flask Application (Waitress / Dev Server)
  * `80/443`: HTTP/HTTPS (via Nginx reverse proxy if configured)

### 3. OCI Object Storage Configuration
* **Namespace:** `os.getenv("namespace")`
* **Bucket Name:** `os.getenv("bucket_name")`
* **OCI Config Path:** `os.getenv("config")` (typically `~/.oci/config`)
* **OCI Profile:** `DEFAULT`

### 4. Oracle Database / Autonomous DB Setup
* **Database Type:** Oracle Autonomous DB / PostgreSQL
* **Wallet Path:** `os.getenv("ORACLE_WALLET_PATH")` (default: `./wallet`)
* **Wallet Password:** `os.getenv("DB_WALLET_PASSWORD")`

---

## ⚙️ Configuration Setup (`properties.ini` & `.env`)

The project separates non-sensitive operational properties from sensitive secret credentials:

### 1. `properties.ini` (Tracked in Version Control)
Contains non-sensitive operational configurations:
```ini
[oci]
config = C:/oracle/hyderabad/config
namespace = axebie7reex5
bucket_name = Obucket
region = ap-hyderabad-1

[database]
oracle_wallet_path = C:/oracle/hyderabad/Wallet
sqlite_database_url = sqlite:///C:/sqlite/fitmafia.db

[app]
host = 127.0.0.1
port = 5000
```

### 2. `.env` (Sensitive Credentials - `.gitignore`)
Contains sensitive credentials and active connection strings:
```ini
# Active Database Connection (Stored on C: Drive: C:/sqlite/fitmafia.db)
DATABASE_URL="sqlite:///C:/sqlite/fitmafia.db"

# Secret Keys & Credentials
SECRET_KEY="your_secret_key_here"
DB_WALLET_PASSWORD="30031990Viswa!"

# Optional PostgreSQL / Oracle Connections
PG_DATABASE_URL="postgresql://user:pass@host:5432/fitmafia"
OCI_DATABASE_URL="oracle+oracledb://admin:pass@db_service_name"
```

---

## 🏗️ Project Architecture & Components

```
fitmafia/
├── main.py               # Main Flask entrypoint & Swagger setup
├── wsgi.py               # WSGI entrypoint for production server
├── database.py           # SQLAlchemy DB manager, schema diffs & data migration tool
├── object_storage.py     # OCI Object Storage client wrapper (uploads, URL generation)
├── health_check.py       # Health check blueprint & monitoring endpoint
├── swagger.py            # Swagger API documentation generator (Flasgger)
├── fit_mafia/            # Core FitMafia application blueprint
│   ├── app.py            # Route handlers & API endpoints
│   ├── app_controller.py # Controller logic & database queries
│   ├── models.py         # SQLAlchemy database models
│   ├── schemas.py        # Marshmallow schemas for serialization/validation
│   ├── constants.py      # Application constants
│   ├── static/           # Static web assets
│   └── templates/        # HTML templates
├── requirements.txt      # Python dependencies
└── sonar-project.properties # SonarQube quality analysis config
```

---

## 🚀 Getting Started

### 1. Prerequisites & Virtual Environment

Ensure Python 3.9+ is installed:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Running the Application

**Development Server:**
```bash
python main.py
```
App runs at `http://127.0.0.1:5000` with Swagger UI documentation enabled.

**Production (Waitress WSGI):**
```bash
waitress-serve --port=5000 main:main_app
```

---

## 🗄️ Database & Alembic Migrations

### Generate Migration Script
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations
```bash
alembic upgrade head
```

### Run Data Migration Utility
To migrate data from PostgreSQL to Oracle Autonomous DB (or vice versa):
```bash
python database.py
```
