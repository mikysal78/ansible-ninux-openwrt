pipeline {
    agent any

    parameters {
        string(
            name: 'OPENWRT_ORG',
            defaultValue: 'basilicata',
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
