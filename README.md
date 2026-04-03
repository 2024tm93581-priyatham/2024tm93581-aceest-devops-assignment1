# 2024tm93581-aceest-devops-assignment1

ACEest Fitness CI/CD Pipeline - DevOps Assignment 1 (CSIZG514)

Student: 2024TM93581 | S2-25

Tech stack: Python/Flask, Docker, pytest, GitHub Actions, Jenkins

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
