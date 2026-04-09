pipeline {
    agent any

    stages {

        stage('Checkout Code') {
            steps {
                git branch: 'main', url: 'https://github.com/YOUR_USERNAME/YOUR_REPO.git'
            }
        }

        stage('Build Docker Images') {
            steps {
                bat 'docker-compose build'
            }
        }

        stage('Start Services') {
            steps {
                bat 'docker-compose up -d'
            }
        }

        stage('Wait for Services') {
            steps {
                bat 'timeout /t 20'
            }
        }

        stage('Health Check') {
            steps {
                bat 'curl http://localhost:8001/health'
                bat 'curl http://localhost:8002/health'
                bat 'curl http://localhost:8003/health'
                bat 'curl http://localhost:8004/health'
                bat 'curl http://localhost:8005/health'
            }
        }
    }

    post {
        success {
            echo '✅ Deployment Successful!'
        }
        failure {
            echo '❌ Pipeline Failed!'
        }
    }
}