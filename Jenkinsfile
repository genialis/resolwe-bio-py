throttle(["resolwe_bio_py"]) {

    // NOTE: Tests could hang unexpectedly and never release the Jenkins executor. Thus we set a
    // general timeout for tests' execution.
    timeout(time: 20, unit: "MINUTES") {

        node {
            def workspace_dir = pwd()
            // Genialis Base branch with which to run the End-to-End tests.
            def genialis_base_e2e_tests_branch = "master"
            // Directory where to check out the given branch of Genialis Base.
            def genialis_base_dir = "genialis-base"
            // NOTE: To avoid exceeding the maximum allowed shebang lenght when calling pip due
            // very long paths of Jenkins' workspaces, we need to set a shorter Tox's working
            // directory path.
            // More info: http://tox.readthedocs.io/en/latest/example/jenkins.html#avoiding-the-path-too-long-error-with-long-shebang-lines
            def tox_workdir = "${env.HOME}/.tox-${env.BUILD_TAG}"
            // Extra arguments passed to Tox.
            def tox_extra_args = ""
            if (genialis_base_e2e_tests_branch == "master") {
                // NOTE: If we are running End-to-End tests with Genialis Base's "master" branch,
                // we need to allow installing pre-releases with the pip command.
                tox_extra_args += "--pre"
            }
            // Path of the JUnit report.
            def junit_report_file = "${genialis_base_dir}/.reports/resdk_e2e_report.xml"
            def jenkins_credentials_id = "7430871b-c83b-4822-bcda-8602e5eb1b1d"

            try {
                stage("Checkout") {
                    // Clean up the workspace directory to ensure we will do a clean git check out.
                    deleteDir()

                    // Check out the same revision as this script is loaded from.
                    checkout scm

                    // Check if the pull request is up to date.
                    if (env.CHANGE_TARGET) {
                        git_change_target_merge_base = sh (
                            script: "git merge-base HEAD origin/${env.CHANGE_TARGET}",
                            returnStdout: true
                        ).trim()

                        git_change_target_sha = sh (
                            script: "git rev-parse origin/${env.CHANGE_TARGET}",
                            returnStdout: true
                        ).trim()

                        if (git_change_target_merge_base != git_change_target_sha) {
                            error(
                                """
                                Pull request is not up-to-date!

                                Please, rebase your pull request on top of '${env.CHANGE_TARGET}'
                                (commit: ${git_change_target_sha}).
                                """.stripIndent()
                            )
                        }
                    }
                }

                stage("Prepare (E2E)") {
                    // Check if we trust the author who has submitted this change or if a branch
                    // from the main repository is being built.
                    // NOTE: This is necessary since we don't want to expose Genialis Base code
                    // base to unauthorized people.
                    // NOTE: This is a work-around until the GitHub Branch Source Plugin authors
                    // implement a way to configure which pull requests from forked repositories
                    // are trusted and which not. More info at:
                    // https://github.com/jenkinsci/github-branch-source-plugin/pull/96
                    // https://issues.jenkins-ci.org/browse/JENKINS-36240
                    def change_author = env.CHANGE_AUTHOR
                    def trusted_authors = [
                        "AGregorc",
                        "JureZmrzlikar",
                        "acopar",
                        "dblenkus",
                        "gregorjerse",
                        "jkokosar",
                        "jvrakor",
                        "mstajdohar",
                        "mzganec",
                        "robertcv",
                        "romunov",
                    ]
                    if (change_author != null && ! trusted_authors.contains(change_author)) {
                        // NOTE: The change_author variable equals null if a branch from the main
                        // repository is being built.
                        error(
                            """
                            User '${change_author}' is not yet trusted to build pull requests!

                            Please, contact maintainers.
                            """.stripIndent()
                        )
                    }

                    // Check out the given branch of Genialis Base.
                    dir(genialis_base_dir) {
                        git (
                            [url: "https://github.com/genialis/genialis-base.git",
                            branch: "${genialis_base_e2e_tests_branch}",
                            credentialsId: jenkins_credentials_id,
                            changelog: false,
                            poll: false]
                        )
                    }

                    // Create an empty configuration schema to avoid an error about it not being
                    // available when calling manage.py.
                    dir(genialis_base_dir) {
                        sh "mkdir -p frontend/genjs/schema && \
                            echo '{}' > frontend/genjs/schema/configuration.json"
                    }
                }

                stage("Test (E2E)") {
                    // Run End-to-End tests.
                    dir(genialis_base_dir) {
                        withEnv([
                            "GENESIS_POSTGRESQL_USER=postgres",
                            // NOTE: These ports must correspond to project's services running on
                            // the Jenkins server.
                            "GENESIS_POSTGRESQL_PORT=55440",
                            "GENESIS_ES_PORT=59210",
                            "GENESIS_REDIS_PORT=56390",
                            // Set database name and Redis prefix to a unique value so multiple
                            // instances can run at the same time.
                            // NOTE: Genialis Base's Django settings automatically set the
                            // ELASTICSEARCH_INDEX_PREFIX to 'test_' if the 'manage.py test'
                            // command is run. Additionally, 'resolwe.elastic' app's logic also
                            // automatically appends a random ID to test index prefixes to avoid
                            // index name clashes.
                            "GENESIS_POSTGRESQL_NAME=${env.BUILD_TAG}",
                            "GENESIS_MANAGER_REDIS_PREFIX=genialis-base.manager.${env.BUILD_TAG}",
                            "GENESIS_RESDK_PATH=${workspace_dir}",
                            "TOX_WORKDIR=${tox_workdir}"
                        ]) {
                            lock (resource: "resolwe-bio-py-e2e-lock-redis10") {
                                withEnv([
                                    "GENESIS_REDIS_DATABASE=10"
                                ]) {
                                    // NOTE: End-to-End tests could hang unexpectedly and lock the
                                    // resource indefinitely thus we have to set a timeout on their
                                    // execution time.
                                    timeout(time: 15, unit: "MINUTES") {
                                        sh "tox -e py36-e2e-resdk ${tox_extra_args}"
                                    }
                                }
                            }
                        }
                    }
                    if (! fileExists(junit_report_file)) {
                        error "JUnit report not found at '${junit_report_file}'."
                    }
                }

                stage("Clean") {
                    // Clean up the workspace directory after a successful build to free the disk
                    // space.
                    deleteDir()
                }

            } catch (e) {
                currentBuild.result = "FAILED"
                // Report failures only when testing the "master" branch.
                if (env.BRANCH_NAME == "master") {
                    notifyFailed()
                }
                throw e
            } finally {
                // Record JUnit report.
                if (fileExists(junit_report_file)) {
                    junit junit_report_file
                }
                // Manually remove Tox's working directory since it is created outside Jenkins's
                // workspace.
                sh "rm -rf ${tox_workdir}"
            }
        }
    }
}

def notifyFailed() {
    slackSend(
        color: "#FF0000",
        message: "FAILED: Job ${env.JOB_NAME} (build #${env.BUILD_NUMBER}) ${env.BUILD_URL}"
    )
}
