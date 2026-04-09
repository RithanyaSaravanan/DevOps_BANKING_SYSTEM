pipeline {
    agent any

    stages {

        stage('Checkout Code') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Images') {
            steps {
                sh 'docker compose build'
            }
        }

        stage('Start Services') {
            steps {
                sh 'docker compose up -d'
            }
        }

        stage('Wait for Services') {
            steps {
                sleep 20
            }
        }

        stage('Health Check') {
            steps {
                sh '''
                curl -f http://localhost:8001/health
                curl -f http://localhost:8002/health
                curl -f http://localhost:8003/health
                curl -f http://localhost:8004/health
                curl -f http://localhost:8005/health
                '''
            }
        }

        stage('Stop Services') {
            steps {
                sh 'docker compose down'
            }
        }
    }
}