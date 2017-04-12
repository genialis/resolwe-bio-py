node {
    def workspace_dir = pwd()
    def genialis_base_dir = "genialis-base"
    def junit_report_file = "${genialis_base_dir}/.reports/resdk_e2e_report.xml"

    try {
        stage("Checkout") {
            // check out the same revision as this script is loaded from
            checkout scm
        }

        stage("Prepare (E2E)") {
            // remove JUnit report from the previous run (if it exists)
            if (fileExists(junit_report_file)) {
                sh "rm ${junit_report_file}"
            }

            // check if we trust the author who has submitted this change
            // NOTE: This is necessary since we don't want to expose Genialis Base code base to
            // unauthorized people.
            // NOTE: This is a work-around until the GitHub Branch Source Plugin authors implement
            // a way to configure which pull requests from forked repositories are trusted and
            // which not. More info at:
            // https://github.com/jenkinsci/github-branch-source-plugin/pull/96
            // https://issues.jenkins-ci.org/browse/JENKINS-36240
            def trusted_authors = [
                "dblenkus",
                "kostko",
                "JenkoB",
                "jkokosar",
                "JureZmrzlikar",
                "mstajdohar",
                "tjanez"
            ]
            if (! trusted_authors.contains(env.CHANGE_AUTHOR)) {
                error "User '${env.CHANGE_AUTHOR}' is not yet trusted to build pull requests. \
                    Please, contact maintainers!"
            }

            // check out the given branch of Genialis Base
            dir(genialis_base_dir) {
                git (
                    [url: "https://github.com/genialis/genialis-base.git",
                     branch:"master",
                     credentialsId: "c89baeb1-9818-4627-95fd-50eeb3677a39",
                     changelog: false,
                     poll: false]
                )
            }

            // create an empty configuration schema file to avoid an error about it not being
            // available when calling manage.py
            dir(genialis_base_dir) {
                sh "mkdir -p frontend/genjs/schema && \
                    touch frontend/genjs/schema/configuration.json"
            }

            // prepare a clean Python virtual environment
            sh "rm -rf venv"
            sh "virtualenv venv"
            withEnv(["PATH+VIRUALENV=${workspace_dir}/venv/bin"]) {
                // NOTE: The pip command is never called directly since it could fail due to
                // exceeding the maximum shabang lenght which can occur due to very long paths
                // of Jenkins builds.
                // The issue is tracked at: https://github.com/pypa/pip/issues/1773
                sh "echo 'Environment:' && python --version && python -m pip --version"
            }

            // install Genialis Base into Python virtual environment
            withEnv(["PATH+VIRUALENV=${workspace_dir}/venv/bin"]) {
                sh "python -m pip install --process-dependency-links -r \
                    ${genialis_base_dir}/requirements.txt"
            }

            // install ReSDK and its testing requirements into Python virtual environment
            withEnv(["PATH+VIRUALENV=${workspace_dir}/venv/bin"]) {
                sh "python -m pip install .[test]"
            }
        }

        stage("Test (E2E)") {
            // run End-to-End tests
            dir(genialis_base_dir) {
                withEnv(["PATH+VIRUALENV=${workspace_dir}/venv/bin",
                         "GENESIS_POSTGRESQL_USER=postgres",
                         "GENESIS_POSTGRESQL_PORT=55440",
                         // set database name to a unique value
                         "GENESIS_POSTGRESQL_NAME=${env.BUILD_TAG}",
                         "GENESIS_ES_PORT=59210",
                         // NOTE: Genialis Base's Django settings automatically set the
                         // ELASTICSEARCH_INDEX_PREFIX to 'test_' if the 'manage.py test' command
                         // is run. Additionally, 'resolwe.elastic' app's logic also automatically
                         // appends a random ID to test index prefixes to avoid index name clashes.
                         "GENESIS_REDIS_PORT=56390",
                         "GENESIS_RESDK_PATH=${workspace_dir}"]) {
                    lock (resource: "resolwe-bio-py-e2e-lock-redis10-liveserver8090") {
                        withEnv(["GENESIS_REDIS_DATABASE=10",
                                 "GENESIS_TEST_LIVESERVER_PORT=8090"]) {
                            // NOTE: End-to-End tests could hang unexpectedly and lock the
                            // "resolwe-bio-py-e2e-lock" indefinitely thus we have to set a timeout
                            // on their execution time.
                            timeout(time: 15, unit: "MINUTES") {
                                sh "./manage.py test --no-input --pattern e2e_test_resdk.py"
                            }
                        }
                    }
                }
            }
            if (! fileExists(junit_report_file)) {
                error "JUnit report not found at '${junit_report_file}'."
            }
        }

    } catch (e) {
        currentBuild.result = "FAILED"
        // report failures only when testing the "master" branch
        if (env.BRANCH_NAME == "master") {
            notifyFailed()
        }
        throw e
    } finally {
        // record JUnit report
        if (fileExists(junit_report_file)) {
            junit junit_report_file
        }
    }
}

def notifyFailed() {
    slackSend(
        color: "#FF0000",
        message: "FAILED: Job ${env.JOB_NAME} (build #${env.BUILD_NUMBER}) ${env.BUILD_URL}"
    )
}
