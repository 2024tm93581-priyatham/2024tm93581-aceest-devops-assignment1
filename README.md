# 2024tm93581-aceest-devops-assignment1

ACEest Fitness CI/CD Pipeline - DevOps Assignment 1 (CSIZG514)

Student: 2024TM93581 | S2-25

Tech stack: Python/Flask, Docker, pytest, GitHub Actions, Jenkins

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
