pipeline {
    agent any

    environment {
        REPO_URL = 'git@github.com:wirenboard/website.git'
        HABR_SCRIPT = 'changed-habr-articles/changed-habr-articles.py'
    }

    triggers {
        cron('H 0 * * 3,6') // Запуск по расписанию: по средам и субботам в полночь
    }

    stages {
        stage('Checkout Repository') {
            steps {
                // Клонирование репозитория с кодом скрипта
                checkout([$class: 'GitSCM', branches: [[name: '*/main']], 
                          userRemoteConfigs: [[url: env.REPO_URL]]])
            }
        }

        stage('Setup Python Environment') {
            steps {
                // Установка необходимых пакетов
                sh 'pip install requests transliterate pillow'
            }
        }

        stage('Run Script') {
            steps {
                script {
                    def args = ""
                    if (params.DRY_RUN) {
                        args += "--dry-run "
                    }
                    if (params.DEBUG) {
                        args += "--debug"
                    }

                    // Запуск основного скрипта с опциями dry-run и debug
                    sh "python ${env.HABR_SCRIPT} ${args}"
                }
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully.'
        }
        failure {
            echo 'Pipeline failed.'
        }
    }
}

parameters {
    booleanParam(name: 'DRY_RUN', defaultValue: true, description: 'Запуск в режиме эмуляции')
    booleanParam(name: 'DEBUG', defaultValue: false, description: 'Запуск в режиме отладки')
}
