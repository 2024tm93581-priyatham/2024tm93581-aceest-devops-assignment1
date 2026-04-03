pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        VENV_DIR = ".venv"
    }

    stages {
        stage('Clean & Checkout') {
            steps {
                deleteDir()
                checkout scm
            }
        }

        stage('Setup Python Environment') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'python3 --version'
                        sh 'python3 -m venv ${VENV_DIR}'
                        sh '. ${VENV_DIR}/bin/activate && python -m pip install --upgrade pip'
                        sh '. ${VENV_DIR}/bin/activate && pip install -r requirements.txt'
                    } else {
                        bat 'python --version'
                        bat 'python -m venv %VENV_DIR%'
                        bat 'call %VENV_DIR%\\Scripts\\activate && python -m pip install --upgrade pip'
                        bat 'call %VENV_DIR%\\Scripts\\activate && pip install -r requirements.txt'
                    }
                }
            }
        }

        stage('Build Validation') {
            steps {
                script {
                    if (isUnix()) {
                        sh '. ${VENV_DIR}/bin/activate && python -m compileall -q .'
                    } else {
                        bat 'call %VENV_DIR%\\Scripts\\activate && python -m compileall -q .'
                    }
                }
            }
        }

        stage('Quality Gate - Unit Tests') {
            steps {
                script {
                    if (isUnix()) {
                        sh '. ${VENV_DIR}/bin/activate && python -m pytest -q'
                    } else {
                        bat 'call %VENV_DIR%\\Scripts\\activate && python -m pytest -q'
                    }
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: '.pytest_cache/**', allowEmptyArchive: true
        }
        success {
            echo 'Build and quality gate passed.'
        }
        failure {
            echo 'Build or quality gate failed. Check console logs.'
        }
    }
}

