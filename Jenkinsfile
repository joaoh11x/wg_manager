pipeline {
    agent any
    
    environment {
        remoteServer = "186.224.0.10:8001"
        remoteDir = "/srv/wireguard-manager"
        remoteUser = "jenkins"
        containerName = "wireguard-manager"
    }
    
    stages {
        stage('Deploy') {
            steps {
                withCredentials([sshUserPrivateKey(credentialsId: 'WGMANAGER', keyFileVariable: 'keyFile')]) {
                    script {
                        sh """
                        if ! which rsync >/dev/null 2>&1; then
                            echo "rsync could not be found, please install it."
                            exit 1
                        fi

                        /usr/bin/rsync --checksum -avz -e "ssh -i \$keyFile" --delete --exclude '.github' --exclude '.git' --exclude '.env' --exclude='__pycache__' ${WORKSPACE}/ ${remoteUser}@${remoteServer}:${remoteDir}
                        """            
                    }
                }
            }
        }

        stage('Rebuild Docker Container') {
            steps {
                echo 'Rebuilding Docker container...'
                withCredentials([sshUserPrivateKey(credentialsId: 'WGMANAGER', keyFileVariable: 'keyFile')]) {
                    sh """
                    ssh -i \$keyFile ${remoteUser}@${remoteServer} '
                        cd ${remoteDir} && 
                        docker compose -f docker-compose.yml down || echo "No running containers to stop" && 
                        docker compose -f docker-compose.yml build --no-cache && 
                        docker compose -f docker-compose.yml up -d
                    '
                    """
                }
            }
        }
    }
    
    post {
        success {
            echo 'Deployment completed successfully!'
        }
        failure {
            echo 'Deployment failed!'
        }
    }
}
