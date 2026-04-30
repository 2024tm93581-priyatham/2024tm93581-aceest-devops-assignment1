# 2024tm93581-aceest-devops-assignment1

ACEest Fitness CI/CD Pipeline - DevOps Assignment 1 (CSIZG514)

Student: 2024TM93581 | S2-25

Tech stack: Python/Flask, Docker, pytest, GitHub Actions, Jenkins

## Application overview

This is a Flask-based fitness management application with:

- Program selection for workout and nutrition plans
- Client save/load APIs backed by SQLite
- Weekly adherence logging and progress charting
- Unit tests for UI and API behavior

## Local setup and run

```bash
python -m venv .venv
```

### Activate virtual environment

- Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

- macOS/Linux:

```bash
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the app

```bash
python app.py
```

Open: [http://localhost:5000](http://localhost:5000)

## Run tests manually

```bash
python -m pytest -q
```

## Jenkins build and quality gate

This project includes a `Jenkinsfile` for a clean CI build from GitHub with a
quality gate.

Pipeline stages:

- Clean workspace + checkout from GitHub
- Create isolated Python virtual environment (clean environment build in Jenkins)
- Install dependencies from `requirements.txt`
- Build validation via `python -m compileall -q .`
- Quality gate via `python -m pytest -q` (build fails if tests fail)

Note: The assignment document requires Docker primarily for the Docker containerization phase and for the GitHub Actions workflow. This Jenkins pipeline focuses on the clean-build + quality-gate validation described in the “Jenkins BUILD & Quality Gate” section.

### Jenkins job setup (http://localhost:8080)

1. Open Jenkins dashboard and click **New Item**.
2. Enter job name (example: `aceest-flask-build`) and choose **Pipeline**.
3. In **Pipeline** section:
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: your GitHub repository URL
   - Branch Specifier: `*/main` (or your feature branch)
   - Script Path: `Jenkinsfile`
4. Save and click **Build Now**.

Expected successful result:

- Console shows all stages green.
- Final message: `Build and quality gate passed.`

## Docker containerization

The Flask application is containerized so it can run consistently across local,
test, and production-like environments without dependency drift.

Docker efficiency and security notes:

- Uses lightweight base image: `python:3.13-slim`
- Uses `pip --no-cache-dir` to reduce image bloat
- Runs app as non-root user (`appuser`)
- Uses `.dockerignore` to exclude caches/build artifacts
- `WORKDIR /app` is `chown`’d to `appuser` so SQLite can create `aceest_fitness.db` and journal files (avoids `readonly database` errors)

### Build Docker image

```bash
docker build -t aceest-fitness-app:latest .
```

### Run Docker container

```bash
docker run --rm -p 5000:5000 --name aceest-fitness aceest-fitness-app:latest
```

Application URL:

- [http://localhost:5000](http://localhost:5000)

### Stop container

```bash
docker stop aceest-fitness
```

## GitHub Actions CI pipeline

This repository includes a GitHub Actions workflow at `.github/workflows/main.yml`.
It runs on every `push` and `pull_request` and performs:

- **Build & Lint**: `python -m compileall -q .` (syntax compilation check)
- **Docker Image Assembly**: `docker build` using the project `Dockerfile`
- **Automated Testing**: `pytest` executed inside the built Docker container

## CI/CD integration summary

- **Jenkins** handles a clean build + quality gate from GitHub checkout.
- **GitHub Actions** enforces build, Docker assembly, and containerized tests on every push/PR.

## Kubernetes (local) deployment using Minikube

Prerequisites:

- Minikube installed
- kubectl installed
- Docker installed

### Start Minikube

```powershell
minikube start
```

### Build the Docker image inside Minikube

This avoids pushing to any external registry (Minikube can use the locally built image).

```powershell
& minikube -p minikube docker-env --shell powershell | Invoke-Expression
docker build -t aceest-fitness-app:latest .
```

### Deploy to Kubernetes

```powershell
kubectl apply -f k8s/
kubectl rollout status deployment/aceest-fitness
```

### Access the application

```powershell
minikube service aceest-fitness --url
```

### Clean up

```powershell
kubectl delete -f k8s/
```
