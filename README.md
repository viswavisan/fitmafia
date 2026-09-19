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

### 5. 🦆 DuckDNS Domain Setup
> **Note:** OCI assigns a **Static Reserved Public IP** (`140.245.230.89`). Dynamic cron updates are **not required**. You only need a one-time DNS mapping.

* **Domain Name:** `your-domain.duckdns.org`
* **Static OCI Public IP:** `140.245.230.89`
* **One-Time Setup Command:**
  ```bash
  curl "https://www.duckdns.org/update?domains=your-domain&token=your-duckdns-token&ip=140.245.230.89"
  ```

### 6. 🌐 Nginx Reverse Proxy Setup
* **Configuration File:** `/etc/nginx/conf.d/fitmafia.conf`
* **Sample Reverse Proxy Configuration:**
  ```nginx
  server {
      listen 80;
      server_name your-domain.duckdns.org;

      location / {
          proxy_pass http://127.0.0.1:5000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }
  }
  ```

### 7. 🔒 SSL / TLS Certificate Setup (Let's Encrypt & Certbot)
* **Certbot Package Installation:**
  ```bash
  # Oracle Linux / RHEL:
  sudo dnf install certbot python3-certbot-nginx -y

  # Ubuntu / Debian:
  sudo apt update && sudo apt install certbot python3-certbot-nginx -y
  ```
* **Obtain SSL Certificate & Update Nginx Automatically:**
  ```bash
  sudo certbot --nginx -d your-domain.duckdns.org
  ```
* **Test SSL Auto-Renewal:**
  ```bash
  sudo certbot renew --dry-run
  ```

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
├── service/              # Automated Linux systemd service & deployment scripts
│   ├── register_service.sh # 1-Command service installer, dependency manager & systemd setup
│   └── README.md
├── requirements.txt      # Python dependencies
└── sonar-project.properties # SonarQube quality analysis config
```

---

## 🚀 Getting Started & Production Deployment

### ⚡ Option A: Automated Linux / OCI Service Deployment (Recommended)

Run the automated service registration script [`service/register_service.sh`](file:///c:/Linux/fitmafia/service/register_service.sh). It automatically performs git updates, creates/activates `.venv`, installs `requirements.txt`, configures `dashboard.service` under systemd, and starts/monitors the background service!

```bash
# Make script executable & run setup
chmod +x service/register_service.sh
./service/register_service.sh
```

**Managing `dashboard.service`:**
```bash
# Check status
sudo systemctl status dashboard.service

# View live service logs
sudo journalctl -u dashboard.service -f

# Restart / Stop service
sudo systemctl restart dashboard.service
sudo systemctl stop dashboard.service
```

---

### 💻 Option B: Manual Setup (Local / Windows Development)

#### 1. Setup Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Running the Application
```bash
# Development Mode
python main.py

# Production Mode (Waitress WSGI)
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
