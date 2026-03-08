# System Overview — Robot Edge Deployment Platform

## 목적

Cloud Control Plane과 Device Agent를 통해 로봇 엣지 디바이스에 desired-state 기반 자동 배포/롤백을 수행하는 플랫폼.

기존 `containner-runner`의 bootstrap 흐름(models.yaml → generate_config.py → systemd/docker-compose/.env → docker pull → systemctl start) 위에 desired-state 기반 배포 레이어를 추가한다.

## 용어 정의

| 용어 | 설명 |
|------|------|
| **Release** | 다중 서비스 이미지 조합. 하나의 Release = N개 서비스 이미지 (예: rise + rise-dashboard) |
| **Deployment** | Release를 대상 디바이스(들)에 배포하는 작업 단위 |
| **Device** | 배포 대상 로봇 엣지 디바이스 |
| **Agent** | 디바이스에서 실행되는 Python 에이전트. Control Plane을 polling하여 desired state를 수신하고 적용 |
| **Desired State** | Control Plane이 디바이스에 적용하기를 원하는 Release 상태 |
| **Actual State** | 디바이스에서 현재 실행 중인 실제 서비스 상태 |

## 컴포넌트 관계

```
┌─────────────────────┐         HTTPS Polling         ┌──────────────────────┐
│   Control Plane     │◄──────────────────────────────►│      Agent           │
│   (FastAPI)         │   heartbeat / desired-state    │   (Python)           │
│                     │   report                       │                      │
│   - PostgreSQL DB   │                                │   - Docker pull      │
│   - REST API        │                                │   - .env 업데이트     │
│   - Release 관리     │                                │   - systemctl restart│
│   - Deployment 관리  │                                │   - Healthcheck      │
└─────────────────────┘                                └──────────────────────┘
```

- **Control Plane → Agent**: Agent가 HTTPS polling으로 desired release를 조회
- **Agent → Control Plane**: heartbeat, state_change, error report 전송
- **Agent → Docker/systemd**: 이미지 pull, .env 업데이트, 서비스 재시작

## Multi-service Release

하나의 Release는 N개의 서비스 이미지 조합을 포함한다.

예시:
```
Release "v2.1.0-rc1"
├── rise: samsung-humanoid-docker-remote.bart.sec.samsung.net/rise:v2.1.0@sha256:abc...
└── rise-dashboard: samsung-humanoid-docker-remote.bart.sec.samsung.net/rise-dashboard:v2.1.0@sha256:def...
```

## Phase 계획

| Phase | 범위 | 주요 내용 |
|-------|------|-----------|
| **Phase 1 (POC)** | 핵심 기능 구현 | Control Plane API, Agent 기본 동작, 단일 디바이스 배포 |
| **Phase 2 (Operations)** | 운영 기능 | 다중 디바이스 배포, 모니터링, 배포 전략 확장 |
| **Phase 3 (Production Hardening)** | 안정화 | 인증 강화, 감사 로그, 고가용성, 성능 최적화 |
