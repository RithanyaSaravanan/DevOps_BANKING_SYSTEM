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
                sh 'sleep 40'
            }
        }

        stage('Health Check') {
    steps {
        sh '''
        docker ps
        curl -f http://$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' banking-ci-cd-gateway-1):8000/health
        '''
    }
}
    }

    post {
        always {
            sh 'docker-compose down || true'
        }
        success {
            echo '✅ Deployment Successful!'
        }
        failure {
            echo '❌ Pipeline Failed!'
        }
    }
}