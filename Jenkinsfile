pipeline {
    agent any

    stages {

        stage('Build Docker Images') {
            steps {
                sh 'docker-compose build'
            }
        }

        stage('Start Services') {
            steps {
                sh 'docker-compose up -d'
            }
        }

        stage('Wait for Services') {
            steps {
                sh 'sleep 20'
            }
        }

        stage('Health Check') {
            steps {
                sh 'curl http://localhost:8001/health'
                sh 'curl http://localhost:8002/health'
                sh 'curl http://localhost:8003/health'
                sh 'curl http://localhost:8004/health'
                sh 'curl http://localhost:8005/health'
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