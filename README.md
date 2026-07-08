# SouTm — Self-Scaling CS:GO Tournament Platform

SouTm is a Django-powered esports tournament management platform for **Counter-Strike: Global Offensive**. Its core value isn't the bracket UI — it's the **backend that provisions, controls, and tears down real CS:GO game servers on AWS EC2 automatically**, scaling capacity up for each match and reclaiming it the moment the match is over.

Organizers create a tournament, register teams, and request N game servers. SouTm spins up N cloud instances on demand, boots a CS:GO server on each, hands out connect IPs, streams live server/player status back into the dashboard, and — when the finals conclude — terminates every instance so nothing keeps billing.

---

## Why this exists

Running a CS:GO tournament traditionally means renting fixed game servers by the month and hoping you provisioned the right number. SouTm treats game servers as **ephemeral, per-match infrastructure**:

- **Scale on demand** — request exactly as many servers as the round needs.
- **Pay only while playing** — instances are stopped between matches and terminated at the end.
- **Zero manual SSH** — starting a server, launching CS:GO, running RCON commands, and reading player counts are all driven from the web UI.

---

## Backend & Cloud Automation (the heart of the project)

All cloud orchestration lives in [`main/aws.py`](main/aws.py) and [`main/rcon_service.py`](main/rcon_service.py), surfaced to the app through the `Server` model in [`main/models.py`](main/models.py).

### 1. Elastic EC2 provisioning — scaling CS servers up

`CreateServers(count)` launches `count` EC2 instances from a **pre-baked CS:GO AMI** in a single API call, waits for each to reach the running state, tags it, and returns its public IP + game port:

```python
# main/aws.py
def CreateServers(servers, port=27015):
    servers = ec2r.create_instances(
        ImageId='ami-0252cd2abfc64e91e',   # golden CS:GO image
        MaxCount=servers, MinCount=servers,
        InstanceType='t2.micro',
        KeyName='Testkey1',
        SecurityGroupIds=['sg-0a1fa41aa4a15bf19'],
    )
    ...
    return data   # [{'instance': id, 'ip': 'x.x.x.x:27015'}, ...]
```

The web layer ([`get_servers` view](main/views.py)) persists each instance as a `Server` row tied to the tournament, then immediately **stops** it — servers are created cold and only powered on when a match is scheduled onto them.

### 2. Full instance lifecycle control

Each `Server` model instance is a thin, safe wrapper over the AWS SDK, with EC2 dry-run permission checks before every state change:

| Action | Backend call | What it does |
| --- | --- | --- |
| Start | `StartAserver()` → `ec2.start_instances` | Boots the instance, waits until running, resolves fresh public IP |
| Stop | `StopAserver()` → `ec2.stop_instances` | Halts billing for compute between matches |
| Terminate | `Terminate()` → `ec2.terminate_instances` | Permanently reclaims the instance |
| State | `ServerState()` | Live `running` / `stopped` / `terminated` status |

On boot, public IPs are re-resolved automatically (`Server.SetIp()`), so ephemeral instances always report a reachable address.

### 3. Remote game-server orchestration over SSH

Once an instance is running, SouTm drives the **CS:GO game server itself** via [Paramiko](https://www.paramiko.org/) SSH using the LinuxGSM `csgoserver` control script:

```python
def Start_cs(ip):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, port, host, password)
    ssh.exec_command('./csgoserver start')   # launch the match server
    ...
```

- `Start_cs` / `Stop_cs` — launch and shut down the CS:GO server process.
- `Command_to_server` — run arbitrary control commands, with automatic retry on transient SSH connection failures.
- `get_rcon` — scrape the server's live RCON password off the running instance so admins never handle it manually.

### 4. RCON & live match telemetry

- **RCON commands** ([`rcon_service.py`](main/rcon_service.py)) send admin commands into a running match over the Source RCON protocol, with a timeout-and-retry wrapper so flaky matches don't hang the request.
- **A2S queries** (`CurrentPlayerCount`) hit the Source server-query protocol to report `players/max` straight onto the server dashboard.
- **Server status** (`Csstatus`) reports whether the CS:GO process is up, right in the UI.

### 5. Automatic teardown — scaling back down

Scaling down is wired directly into tournament logic. When a match's winner is set, its server is freed for reuse; when the **finals** conclude, [`set_winner`](main/views.py) terminates and deletes **every** server the tournament ever provisioned:

```python
if match.stage == 'Finals':
    for server in tournament.servers.all():
        server.terminate()   # kill the EC2 instance
        server.delete()      # drop the DB record
```

No orphaned instances, no lingering AWS bill.

### Scaling model at a glance

```
Organizer requests N servers
        │
        ▼
CreateServers(N) ── launch N EC2 instances from CS:GO AMI ──▶ stop (cold standby)
        │
        ▼
Match scheduled ──▶ Start instance ──▶ SSH ./csgoserver start ──▶ hand out IP:port
        │
        ▼
Live match ──▶ RCON commands + A2S player counts streamed to dashboard
        │
        ▼
Match ends ──▶ free server   │   Finals end ──▶ terminate + delete ALL instances
```

---

## Application Features

Beyond the cloud backend, SouTm is a complete tournament manager:

- **Custom user accounts** — email-based auth with a custom `NewUser` model, in-game name, profile pictures, and organizer roles ([`login_signup`](login_signup/)).
- **Tournament lifecycle** — create/update tournaments with banners, logos, prize pools, sponsors, and automatic status (Upcoming → Registration → Ongoing → Finished).
- **Team management** — register teams with up to five players, tags, logos, and descriptions.
- **Automatic bracket generation** — `random_matches` / `FirstMatches` / `next_round` seed and advance rounds (Preliminary → Quarter → Semi → Finals) based on the number of teams remaining.
- **Match management** — assign servers to matches, set winners, and advance the bracket.
- **Search & discovery** — browse featured, active, and upcoming tournaments.
- **Password reset** — email-backed reset flow.

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| Web framework | Django 3.1 |
| Language | Python 3 |
| Database | PostgreSQL (uses `ArrayField`, so Postgres is required) |
| Cloud SDK | boto3 / botocore (AWS EC2) |
| Remote control | Paramiko (SSH) |
| Game protocols | python-valve (Source RCON + A2S queries) |
| Forms/UI | django-crispy-forms, HTML/CSS/JS templates |

---

## Architecture

```
SouTm/
├── project/          # Django project config (settings, urls, wsgi/asgi)
├── main/             # Core app: tournaments, teams, matches, servers
│   ├── aws.py            # ★ EC2 provisioning + SSH game-server control
│   ├── rcon_service.py   # ★ Source RCON command execution
│   ├── models.py         # Server / Team / Tournament / Match models
│   ├── views.py          # Tournament & server orchestration views
│   └── urls.py
├── login_signup/     # Custom user model + auth flows
├── templates/        # HTML templates (console, server, tournament, ...)
├── static/           # CSS / JS / images / fonts
├── media/            # Uploaded logos & banners
├── Screenshots/      # UI screenshots
└── manage.py
```

---

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL
- An AWS account with EC2 access
- A CS:GO server AMI (with the LinuxGSM `csgoserver` script installed) and an EC2 key pair
- An SSH private key (`.pem`) for the game-server instances

### Installation

```bash
# 1. Clone
git clone https://github.com/tirth252/soutm.git
cd soutm

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install django==3.1 boto3 paramiko python-valve psycopg2-binary django-crispy-forms

# 4. Configure PostgreSQL, then run migrations
python manage.py migrate

# 5. Create an admin user
python manage.py createsuperuser

# 6. Run the server
python manage.py runserver
```

Visit http://127.0.0.1:8000/.

### Cloud & environment configuration

The cloud backend needs a few things wired up before it can provision servers:

1. **AWS credentials** — configure via `aws configure`, environment variables, or an IAM role. boto3 picks them up automatically.
2. **Instance parameters** in [`main/aws.py`](main/aws.py) — set your own `ImageId` (CS:GO AMI), `InstanceType`, `KeyName`, and `SecurityGroupIds`.
3. **SSH key path** — update the `paramiko.RSAKey.from_private_key_file(...)` path to your `.pem`.

> ⚠️ **Security note:** The committed `settings.py` and `aws.py` contain hard-coded secrets, credentials, and file paths from development. **Before deploying, move `SECRET_KEY`, database credentials, email credentials, AWS keys, and SSH key paths into environment variables**, set `DEBUG = False`, and configure `ALLOWED_HOSTS`.

---

## Screenshots

UI screenshots live in the [`Screenshots/`](Screenshots/) directory.

---

## License

No license file is currently provided. Add one before public distribution.
