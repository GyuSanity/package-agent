# containner-runner Bootstrap Integration Spec

## 개요

기존 `containner-runner`의 `setup.sh` 끝에 Agent 설치/시작 단계를 추가하여, 초기 bootstrap 완료 후 자동으로 deployment agent가 활성화되도록 한다.

## Bootstrap 흐름 (기존 + 추가)

```
[기존 containner-runner bootstrap]
  models.yaml
    → generate_config.py
      → systemd units / docker-compose fragments / .env files
        → docker pull
          → systemctl start

[추가: Agent bootstrap]
  → Agent 바이너리/패키지 설치
    → agent.yaml 자동 생성 (ROBOT_MODEL + hostname 기반)
      → systemd unit 등록 (robot-deploy-agent.service)
        → systemctl enable --now robot-deploy-agent.service
```

## setup.sh 추가 내용

`setup.sh` 끝에 다음 단계를 추가한다:

### 1. Agent 설치

```bash
# Agent 패키지 설치 (pip 또는 deb)
pip install robot-deploy-agent
# 또는
# dpkg -i /opt/packages/robot-deploy-agent.deb
```

### 2. Agent 설정 자동 생성

`ROBOT_MODEL`과 `hostname`으로부터 `/etc/robot-deploy-agent/agent.yaml`을 자동 생성한다.

```bash
mkdir -p /etc/robot-deploy-agent
mkdir -p /var/lib/robot-deploy-agent

cat > /etc/robot-deploy-agent/agent.yaml <<EOF
control_plane_url: "${CONTROL_PLANE_URL:-https://control-plane.example.com}"
device_name: "$(hostname)"
robot_model: "${ROBOT_MODEL}"
auth_key: "${AGENT_AUTH_KEY}"
polling_interval: 30
heartbeat_interval: 60
service_config_dir: "/etc/container-runner"
EOF
```

### 3. systemd Unit 등록

`/etc/systemd/system/robot-deploy-agent.service`:

```ini
[Unit]
Description=Robot Deploy Agent
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/robot-deploy-agent --config /etc/robot-deploy-agent/agent.yaml
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### 4. Agent 시작

```bash
systemctl daemon-reload
systemctl enable --now robot-deploy-agent.service
```

## Agent 설정 항목

| 항목 | 출처 | 설명 |
|------|------|------|
| `control_plane_url` | 환경변수 `CONTROL_PLANE_URL` | Control Plane API URL |
| `device_name` | `$(hostname)` | 디바이스 식별자 (hostname) |
| `robot_model` | 환경변수 `ROBOT_MODEL` (models.yaml 유래) | 로봇 모델명 |
| `auth_key` | 환경변수 `AGENT_AUTH_KEY` | Control Plane 인증 키 |
| `polling_interval` | 기본값 30 | desired state polling 주기 (초) |
| `heartbeat_interval` | 기본값 60 | heartbeat 전송 주기 (초) |
| `service_config_dir` | `/etc/container-runner` | .env 파일이 위치하는 디렉토리 |

## 주의사항

- `containner-runner` 의 기존 동작에는 영향을 주지 않는다
- Agent는 `containner-runner`가 이미 생성한 .env / compose / systemd 구조를 그대로 사용한다
- `CONTROL_PLANE_URL`과 `AGENT_AUTH_KEY`가 설정되지 않은 경우, Agent는 기본값/placeholder로 생성되며 수동 설정이 필요하다
