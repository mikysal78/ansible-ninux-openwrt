pipeline {
    agent any

    parameters {
        string(
            name: 'OPENWRT_ORG',
            defaultValue: 'default',
            description: 'Organizzazione Ninux'
        )
        string(
            name: 'OPENWRT_VERSION',
            defaultValue: 'v25.12.4',
            description: 'Tag OpenWrt'
        )
        choice(
            name: 'VPN_VARIANTS',
            choices: ['ALL', 'NO', 'ZeroTier', 'WireGuard', 'DualVPN'],
            description: 'Varianti VPN (ALL = tutte e 4)'
        )
        booleanParam(
            name: 'CAPTIVE_PORTAL_VARIANTS',
            defaultValue: false,
            description: 'Compila ogni variante sia con che senza Captive Portal'
        )
        booleanParam(
            name: 'SKIP_DEPS',
            defaultValue: false,
            description: 'Salta apt install (se gia fatto)'
        )
        booleanParam(
            name: 'TMPFS_ENABLED',
            defaultValue: true,
            description: 'Usa RAM disk per tmp/ build (8GB, +30% velocita)'
        )
        string(
            name: 'TMPFS_SIZE',
            defaultValue: '8G',
            description: 'Dimensione tmpfs. Container ha 24GB RAM.'
        )
        string(
            name: 'CCACHE_DIR',
            defaultValue: '/var/cache/openwrt-ccache',
            description: 'Directory ccache persistente (fuori workspace)'
        )
        string(
            name: 'CCACHE_SIZE',
            defaultValue: '20G',
            description: 'Dimensione max ccache'
        )
        booleanParam(
            name: 'OPENWISP_UPLOAD',
            defaultValue: false,
            description: 'Carica su OpenWISP Firmware Upgrader'
        )
        booleanParam(
            name: 'OPENWISP_TRIGGER_UPGRADE',
            defaultValue: false,
            description: 'Avvia batch upgrade su OpenWISP dopo upload'
        )
        string(
            name: 'OPENWISP_URL',
            defaultValue: '',
            description: 'URL OpenWISP Firmware Upgrader (vuoto = da group_vars)'
        )
        booleanParam(
            name: 'GITHUB_RELEASE',
            defaultValue: false,
            description: 'Crea release GitHub e carica i firmware come assets'
        )
        string(
            name: 'GITHUB_REPO',
            defaultValue: 'mikysal78/ansible-ninux-openwrt',
            description: 'Repository GitHub (owner/repo)'
        )
    }

    environment {
        ANSIBLE_FORCE_COLOR       = 'true'
        ANSIBLE_HOST_KEY_CHECKING = 'false'
        VAULT_PASS_FILE           = "${JENKINS_HOME}/.vault_pass"
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Discover devices') {
            steps {
                script {
                    def configDir = "${WORKSPACE}/config/organizations/${params.OPENWRT_ORG}"
                    if (!fileExists(configDir)) error "Manca: ${configDir}"
                    def configs = sh(
                        script: "ls ${configDir}/*.config 2>/dev/null | xargs -I{} basename {} .config | sort",
                        returnStdout: true
                    ).trim()
                    if (!configs) error "Nessun .config in ${configDir}"
                    def nDev  = configs.split('\n').size()
                    def nVpn  = params.VPN_VARIANTS == 'ALL' ? 4 : 1
                    def nCp   = params.CAPTIVE_PORTAL_VARIANTS ? 2 : 1
                    def total = nDev * nVpn * nCp
                    echo """
=== Piano di build ===
Device    : ${configs.replaceAll('\n', ', ')}
Totale    : ${total} firmware (${nDev} dev x ${nVpn} VPN x ${nCp} CP)
Workspace : ${WORKSPACE}
"""
                    env.DISCOVERED_DEVICES = configs.replaceAll('\n', ', ')
                    env.TOTAL_BUILDS = total.toString()
                }
            }
        }

        stage('Disk & RAM (before)') {
            steps {
                sh 'df -h ${WORKSPACE} | tail -1'
                sh 'free -h | grep Mem'
                sh "CCACHE_DIR=${params.CCACHE_DIR} ccache --show-stats 2>/dev/null || echo 'ccache vuota'"
            }
        }

        stage('Install dependencies') {
            when { expression { !params.SKIP_DEPS } }
            steps {
                script {
                    sh "ansible-playbook playbooks/build_all.yml -e openwrt_work_dir=${WORKSPACE} -e openwrt_org=${params.OPENWRT_ORG} -e openwrt_version=${params.OPENWRT_VERSION} --tags deps --vault-password-file ${VAULT_PASS_FILE}"
                }
            }
        }

        stage('Build firmware') {
            steps {
                script {
                    def args = [
                        "ansible-playbook playbooks/build_all.yml",
                        "-e openwrt_work_dir=${WORKSPACE}",
                        "-e openwrt_org=${params.OPENWRT_ORG}",
                        "-e openwrt_version=${params.OPENWRT_VERSION}",
                        "-e openwrt_tmpfs_enabled=${params.TMPFS_ENABLED}",
                        "-e openwrt_tmpfs_size=${params.TMPFS_SIZE}",
                        "-e openwrt_ccache_dir=${params.CCACHE_DIR}",
                        "-e openwrt_ccache_maxsize=${params.CCACHE_SIZE}",
                        "--skip-tags deps"
                    ]
                    if (params.VPN_VARIANTS != 'ALL') {
                        args << "-e '{\"openwrt_vpn_variants\": [\"${params.VPN_VARIANTS}\"]}'"
                    }
                    if (params.CAPTIVE_PORTAL_VARIANTS) {
                        args << "-e openwrt_cp_variants=true"
                    }
                    if (params.OPENWISP_UPLOAD) {
                        args << "-e openwisp_upload_enabled=true"
                        if (params.OPENWISP_TRIGGER_UPGRADE) args << "-e openwisp_trigger_upgrade=true"
                        if (params.OPENWISP_URL)             args << "-e openwisp_url=${params.OPENWISP_URL}"
                    }
                    args << "--vault-password-file ${VAULT_PASS_FILE}"
                    sh args.join(' ')
                }
            }
        }

        stage('Archive artifacts') {
            steps {
                script {
                    // Debug: mostra struttura workspace dopo la build
                    sh """
                        echo '=== Struttura output/ ==='
                        find ${WORKSPACE}/output -type f 2>/dev/null | sort || echo 'output/ assente o vuota'
                        echo '=== Log varianti (ultimi 30 righe) ==='
                        find ${WORKSPACE}/build -name 'log-*.log' 2>/dev/null | while read f; do
                            echo "--- \$f ---"
                            tail -30 "\$f"
                        done || echo 'Nessun log trovato'
                    """

                    def firmwareCount = sh(
                        script: "find ${WORKSPACE}/output -type f \\( -name '*.bin' -o -name '*-sysupgrade*' -o -name '*.img.gz' \\) 2>/dev/null | wc -l",
                        returnStdout: true
                    ).trim().toInteger()

                    if (firmwareCount == 0) {
                        error "Nessun firmware in output/ - controlla i log sopra"
                    }

                    echo "Firmware trovati: ${firmwareCount}"
                    archiveArtifacts(
                        artifacts: 'output/**/*.bin,output/**/*-sysupgrade*,output/**/*-factory*,output/**/*.img.gz,output/**/sha256sums',
                        fingerprint: true,
                        allowEmptyArchive: false
                    )
                }
            }
        }

        stage('GitHub Release') {
            when {
                expression {
                    params.GITHUB_RELEASE || sh(
                        script: "grep -qE '^github_release_enabled:\\s*true' ${WORKSPACE}/ninux.yml && echo yes || echo no",
                        returnStdout: true
                    ).trim() == 'yes'
                }
            }
            steps {
                script {
                    withCredentials([string(credentialsId: 'github-release-token', variable: 'GH_TOKEN')]) {
                        def version = params.OPENWRT_VERSION
                        def org     = params.OPENWRT_ORG
                        def tag     = "${version}-${org}-build${env.BUILD_NUMBER}"
                        def repo    = sh(
                            script: "grep -E '^github_repo:' ${WORKSPACE}/ninux.yml | awk '{print \$2}' | tr -d '\"'",
                            returnStdout: true
                        ).trim() ?: 'mikysal78/ansible-ninux-openwrt'
                        def prerel  = sh(
                            script: "grep -qE '^github_prerelease:\\s*true' ${WORKSPACE}/ninux.yml && echo true || echo false",
                            returnStdout: true
                        ).trim()
                        def inclSha = sh(
                            script: "grep -qE '^github_release_include_sha256:\\s*false' ${WORKSPACE}/ninux.yml && echo false || echo true",
                            returnStdout: true
                        ).trim()

                        // Crea release via API GitHub
                        def notes = "Build automatica Jenkins #${env.BUILD_NUMBER}" +
                                    " | Org: ${org}" +
                                    " | OpenWrt: ${version}" +
                                    " | VPN: ${params.VPN_VARIANTS}" +
                                    " | CP: ${params.CAPTIVE_PORTAL_VARIANTS}"

                        def createScript = """
curl -sf -X POST \\
  -H "Authorization: Bearer \$GH_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"tag_name":"${tag}","name":"Ninux OpenWrt ${version} - ${org} #${env.BUILD_NUMBER}","body":"${notes}","draft":false,"prerelease":${prerel}}' \\
  "https://api.github.com/repos/${repo}/releases" \\
| python3 -c "import sys,json; print(json.load(sys.stdin)['id'])"
"""
                        def releaseId = sh(script: createScript, returnStdout: true).trim()
                        echo "Release creata: ID=${releaseId}  tag=${tag}"

                        // Upload assets
                        def shaFilter = inclSha == 'true' ? "-o -name 'sha256sums'" : ""
                        def files = sh(
                            script: "find ${WORKSPACE}/output -type f \\( -name '*.bin' -o -name '*.img.gz' ${shaFilter} \\) | sort",
                            returnStdout: true
                        ).trim()

                        if (!files) { echo "Nessun firmware trovato per upload GitHub"; return }

                        files.split('\n').each { fp ->
                            fp = fp.trim()
                            if (!fp) return
                            def assetName = fp
                                .replace("${WORKSPACE}/output/${version}/${org}/", '')
                                .replaceAll('/', '_')
                            def code = sh(
                                script: """curl -s -o /dev/null -w "%{http_code}" \\
  -X POST \\
  -H "Authorization: Bearer \$GH_TOKEN" \\
  -H "Content-Type: application/octet-stream" \\
  --data-binary @"${fp}" \\
  "https://uploads.github.com/repos/${repo}/releases/${releaseId}/assets?name=${assetName}" """,
                                returnStdout: true
                            ).trim()
                            echo "${code == '201' ? '[OK]' : '[WARN ' + code + ']'} ${assetName}"
                        }

                        echo "Release: https://github.com/${repo}/releases/tag/${tag}"
                    }
                }
            }
        }

        stage('Disk & RAM (after)') {
            steps {
                sh 'df -h ${WORKSPACE} | tail -1'
                sh 'free -h | grep Mem'
                sh "du -sh ${WORKSPACE}/build ${params.CCACHE_DIR} ${WORKSPACE}/output 2>/dev/null || true"
                sh "CCACHE_DIR=${params.CCACHE_DIR} ccache --show-stats 2>/dev/null || true"
            }
        }
    }

    post {
        always {
            echo "org=${params.OPENWRT_ORG} ver=${params.OPENWRT_VERSION} firmware=${env.TOTAL_BUILDS} device=${env.DISCOVERED_DEVICES}"
        }
        cleanup {
            script {
                sh "ansible-playbook playbooks/cleanup.yml -e openwrt_work_dir=${WORKSPACE} || true"
                sh "umount ${WORKSPACE}/build/openwrt/tmp 2>/dev/null || true"
            }
        }
    }
}
