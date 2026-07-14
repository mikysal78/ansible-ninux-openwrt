pipeline {
    agent any

    parameters {
        string(
            name: 'OPENWRT_ORG',
            defaultValue: 'basilicata',
            description: 'Organizzazione Ninux (default = org di esempio, non compilabile)'
        )
        string(
            name: 'OPENWRT_VERSION',
            defaultValue: 'v25.12.5',
            description: 'Tag OpenWrt'
        )
        choice(
            name: 'VPN_VARIANTS',
            choices: ['ALL', 'NONE', 'ZeroTier', 'WireGuard', 'Dual'],
            description: 'Varianti VPN (ALL = tutte e 4)'
        )
        booleanParam(
            name: 'CAPTIVE_PORTAL_VARIANTS',
            defaultValue: false,
            description: 'Compila ogni variante sia con che senza Captive Portal'
        )
        choice(
            name: 'CAPTIVE_PORTAL_ENGINE',
            choices: ['chilli', 'uspot', 'ALL'],
            description: 'Motore Captive Portal: build separate, mai chilli e uspot insieme (ALL = una build per motore)'
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
                    def nEng  = params.CAPTIVE_PORTAL_ENGINE == 'ALL' ? 2 : 1
                    def nCp   = params.CAPTIVE_PORTAL_VARIANTS ? 1 + nEng : 1
                    def total = nDev * nVpn * nCp
                    echo """
=== Piano di build ===
Device    : ${configs.replaceAll('\n', ', ')}
Totale    : ${total} firmware (${nDev} dev x ${nVpn} VPN x ${nCp} CP)
CP engine : ${params.CAPTIVE_PORTAL_VARIANTS ? params.CAPTIVE_PORTAL_ENGINE : 'nessuno'}
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
                        // svuota anche l'override per org, altrimenti vincerebbe sulla scelta esplicita
                        args << "-e '{\"openwrt_vpn_variants\": [\"${params.VPN_VARIANTS}\"], \"openwrt_org_vpn_variants\": {}}'"
                    }
                    args << "-e openwrt_cp_variants=${params.CAPTIVE_PORTAL_VARIANTS}"
                    if (params.CAPTIVE_PORTAL_VARIANTS) {
                        def engines = params.CAPTIVE_PORTAL_ENGINE == 'ALL' ? ['chilli', 'uspot'] : [params.CAPTIVE_PORTAL_ENGINE]
                        def enginesJson = engines.collect { "\"${it}\"" }.join(', ')
                        args << "-e '{\"openwrt_cp_engines\": [${enginesJson}], \"openwrt_org_cp_engines\": {}}'"
                    }
                    if (params.OPENWISP_UPLOAD) {
                        args << "-e openwisp_upload_enabled=true"
                        if (params.OPENWISP_TRIGGER_UPGRADE) args << "-e openwisp_trigger_upgrade=true"
                        if (params.OPENWISP_URL)             args << "-e openwisp_url=${params.OPENWISP_URL}"
                    }
                    args << "--vault-password-file ${VAULT_PASS_FILE}"
                    sh args.join(' ')

                    // Un upload OpenWISP fallito (es. controller irraggiungibile) non
                    // fa piu' fallire la build: il firmware resta compilato, archiviato
                    // e pubblicato. Qui la build diventa UNSTABLE (gialla) cosi' non
                    // passa inosservato che sul controller manca il firmware nuovo.
                    def uploadFailed = "${WORKSPACE}/output/.openwisp-upload-failed"
                    if (fileExists(uploadFailed)) {
                        currentBuild.result = 'UNSTABLE'
                        echo "=== ATTENZIONE: upload OpenWISP fallito per queste varianti ==="
                        echo readFile(uploadFailed).trim()
                        echo "I firmware sono stati compilati e archiviati: vanno ricaricati " +
                             "su ${params.OPENWISP_URL ?: 'OpenWISP'} quando il controller torna raggiungibile."
                    }
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

                        // Trova tutti i device (sottodirectory di output/<version>/<org>/)
                        def devicesRaw = sh(
                            script: "find ${WORKSPACE}/output/${version}/${org} -mindepth 1 -maxdepth 1 -type d | sort",
                            returnStdout: true
                        ).trim()

                        if (!devicesRaw) {
                            echo "Nessuna directory device trovata in output/${version}/${org}"
                            return
                        }

                        devicesRaw.split('\n').each { deviceDir ->
                            deviceDir = deviceDir.trim()
                            if (!deviceDir) return
                            def device = deviceDir.tokenize('/').last()

                            // Tag: v25.12.4-default-x86_64
                            def tag = "${version}-${org}-${device}"

                            // Varianti presenti nel device
                            def variantsRaw = sh(
                                script: "find ${deviceDir} -mindepth 2 -maxdepth 2 -type d | sort | xargs -I{} basename {} 2>/dev/null | sort -u",
                                returnStdout: true
                            ).trim()
                            def variants = variantsRaw ? variantsRaw.replaceAll('\n', ', ') : 'n/a'

                            def notes = "Build Jenkins #${env.BUILD_NUMBER}\\nOrg: ${org}\\nOpenWrt: ${version}\\nDevice: ${device}\\nVarianti: ${variants}"

                            // Crea release per questo device via python3 per gestire JSON
                            def releaseId = sh(
                                script: """python3 -c "
import urllib.request, json, os, sys
data = json.dumps({
    'tag_name': '${tag}',
    'name': 'Ninux OpenWrt ${version} | ${org} | ${device}',
    'body': '${notes}',
    'draft': False,
    'prerelease': '${prerel}' == 'true'
}).encode()
req = urllib.request.Request(
    'https://api.github.com/repos/${repo}/releases',
    data=data,
    headers={
        'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
        'Content-Type': 'application/json'
    }
)
resp = urllib.request.urlopen(req)
print(json.loads(resp.read())['id'])
" """,
                                returnStdout: true
                            ).trim()

                            echo "Release creata: ${tag}  (ID=${releaseId})"

                            // Upload firmware di questo device
                            // Struttura asset: Standard__VPN-NO__openwrt-x86-64-...-efi.img.gz
                            def shaArg = inclSha == 'true' ? "-o -name 'sha256sums'" : ""
                            def files = sh(
                                script: "find ${deviceDir} -type f \\( -name '*.bin' -o -name '*.img.gz' ${shaArg} \\) | sort",
                                returnStdout: true
                            ).trim()

                            if (!files) {
                                echo "Nessun firmware trovato per ${device}"
                                return
                            }

                            files.split('\n').each { fp ->
                                fp = fp.trim()
                                if (!fp) return

                                // Es: Standard__VPN-NO__openwrt-x86-64-generic-squashfs-combined-efi.img.gz
                                def assetName = fp
                                    .replace("${deviceDir}/", '')
                                    .replaceAll('/', '__')

                                def code = sh(
                                    script: """curl -s -o /dev/null -w "%{http_code}" \
  -X POST \
  -H "Authorization: Bearer \$GH_TOKEN" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @"${fp}" \
  "https://uploads.github.com/repos/${repo}/releases/${releaseId}/assets?name=${assetName}" """,
                                    returnStdout: true
                                ).trim()
                                echo "${code == '201' ? '[OK]' : '[WARN ' + code + ']'} ${assetName}"
                            }

                            echo "→ https://github.com/${repo}/releases/tag/${tag}"
                        }
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
