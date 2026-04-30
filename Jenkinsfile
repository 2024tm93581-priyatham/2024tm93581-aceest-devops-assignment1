pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        VENV_DIR = ".venv"
        // SonarQube quality gate can take time on first runs or busy servers.
        // This timeout also protects the pipeline if the SonarQube->Jenkins webhook isn't configured/reachable.
        SONAR_QG_TIMEOUT_MIN = "30"
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
                        bat '''
                            @echo off
                            set PY_CMD=
                            where py >nul 2>&1 && set PY_CMD=py -3
                            if "%PY_CMD%"=="" where python >nul 2>&1 && set PY_CMD=python
                            if "%PY_CMD%"=="" (
                                echo ERROR: Python is not installed or not available in PATH on this Jenkins agent.
                                exit /b 1
                            )
                            %PY_CMD% --version
                            %PY_CMD% -m venv %VENV_DIR%
                            call %VENV_DIR%\\Scripts\\activate
                            python -m pip install --upgrade pip
                            pip install -r requirements.txt
                        '''
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

        stage('SonarQube Scan') {
            steps {
                script {
                    // Requires Jenkins configuration:
                    // 1) "Manage Jenkins" -> "System" -> "SonarQube servers" (name: SonarQube)
                    // 2) "Manage Jenkins" -> "Tools" -> "SonarScanner installations" (name: SonarScanner)
                    def scannerHome = tool 'SonarScanner'
                    withSonarQubeEnv('SonarQube') {
                        if (isUnix()) {
                            sh "${scannerHome}/bin/sonar-scanner"
                        } else {
                            bat "\"${scannerHome}\\\\bin\\\\sonar-scanner.bat\""
                        }
                    }
                }
            }
        }

        stage('Quality Gate - SonarQube') {
            steps {
                timeout(time: env.SONAR_QG_TIMEOUT_MIN.toInteger(), unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
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

