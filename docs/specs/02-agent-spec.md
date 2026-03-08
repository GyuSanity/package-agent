# Agent Spec

## 개요

디바이스에서 실행되는 Python Agent. Control Plane을 polling하여 desired state를 확인하고, Docker 이미지 pull / .env 업데이트 / systemd 서비스 재시작을 수행한다.

## State Machine

```
                    ┌──────────┐
                    │   IDLE   │
                    └────┬─────┘
                         │ polling interval 도래
                         ▼
                    ┌──────────┐
                    │ CHECKING │ ← desired-release 조회 & 비교
                    └────┬─────┘
                         │ 변경 감지
                         ▼
                  ┌──────────────┐
                  │ DOWNLOADING  │ ← docker pull (all services)
                  └──────┬───────┘
                         │ 전체 pull 성공
                         ▼
               ┌──────────────────┐
               │ READY_TO_APPLY   │
               └────────┬─────────┘
                        │
                        ▼
                  ┌──────────┐
                  │ APPLYING │ ← .env 백업 → .env 업데이트 → systemctl restart
                  └────┬─────┘
                       │
                       ▼
                 ┌───────────┐
                 │ VERIFYING │ ← healthcheck per service
                 └─────┬─────┘
                       │
              ┌────────┴────────┐
              │                 │
        성공  ▼           실패  ▼
      ┌───────────┐    ┌──────────────┐
      │ SUCCEEDED │    │ ROLLING_BACK │ ← .env 복원 → systemctl restart
      └───────────┘    └──────┬───────┘
                              │
                              ▼
                       ┌─────────────┐
                       │ ROLLED_BACK │
                       └─────────────┘

  * DOWNLOADING 실패 시 → FAILED (rollback 불필요, 아직 적용 전)
  * ROLLING_BACK 실패 시 → FAILED
```

### 상태 전이 요약

| From | To | 조건 |
|------|----|------|
| IDLE | CHECKING | polling interval 도래 |
| CHECKING | IDLE | desired == current (변경 없음) |
| CHECKING | DOWNLOADING | desired != current |
| DOWNLOADING | READY_TO_APPLY | 모든 서비스 이미지 pull 성공 |
| DOWNLOADING | FAILED | 하나라도 pull 실패 |
| READY_TO_APPLY | APPLYING | 즉시 전이 |
| APPLYING | VERIFYING | .env 업데이트 + systemctl restart 완료 |
| VERIFYING | SUCCEEDED | 모든 서비스 healthcheck 통과 |
| VERIFYING | ROLLING_BACK | healthcheck 실패 |
| ROLLING_BACK | ROLLED_BACK | .env 복원 + restart 성공 |
| ROLLING_BACK | FAILED | 복원 실패 |

## Reconciliation Logic

### 1. Desired State 조회 및 비교
```
GET /api/v1/agent/desired-release
Headers: X-Device-Auth-Key: <key>
```
- 응답의 `release_id`를 로컬 `state.json`의 `current_release_id`와 비교
- 동일하면 IDLE로 복귀

### 2. 이미지 Pre-pull (DOWNLOADING)
- 모든 서비스 이미지를 순차적으로 `docker pull`
- 이미지 참조 형식: `<registry>/<service>:<tag>@<digest>`
- 하나라도 실패 시 → FAILED, Control Plane에 error report

### 3. .env 백업 및 업데이트 (APPLYING)
- 현재 .env 파일을 `.env.backup.<timestamp>`로 백업
- SERVICE_ENV_MAP에 따라 환경변수 업데이트:
  ```
  # SERVICE_ENV_MAP 매핑
  rise        → RISE_IMAGE
  rise-dashboard → RISE_DASHBOARD_IMAGE
  ```
- .env 파일 내 해당 변수를 새 이미지 참조로 교체:
  ```
  RISE_IMAGE=samsung-humanoid-docker-remote.bart.sec.samsung.net/rise:v2.1.0@sha256:abc123...
  ```

### 4. 서비스 재시작 (APPLYING)
- 각 서비스에 대해 `systemctl restart <service>-container.service` 실행
- 예: `systemctl restart rise-container.service`

### 5. Healthcheck (VERIFYING)
- release_services의 healthcheck_profile에 따라 검증
- 지원 유형: http, tcp, exec, docker_health
- 모든 서비스 healthcheck 통과 시 → SUCCEEDED

### 6. Rollback (ROLLING_BACK)
- healthcheck 실패 시:
  1. 백업된 .env 파일 복원
  2. `systemctl restart <service>-container.service`
  3. ROLLED_BACK 상태로 전이
  4. Control Plane에 report

## containner-runner 호환성

Agent는 기존 `containner-runner`가 생성한 구조를 그대로 활용한다:
- **compose fragments**: `${RISE_IMAGE}` 등의 변수 참조는 변경하지 않음
- **systemd units**: `<service>-container.service` 유닛은 변경하지 않음
- **Agent의 역할**: .env 파일 내 이미지 참조만 업데이트

## 설정 파일

### Agent 설정: `/etc/robot-deploy-agent/agent.yaml`

```yaml
control_plane_url: "https://control-plane.example.com"
device_name: "robot-01"
robot_model: "humanoid-v2"
auth_key: "device-auth-key"
polling_interval: 30  # seconds
heartbeat_interval: 60  # seconds
service_config_dir: "/etc/container-runner"
```

### 로컬 상태: `/var/lib/robot-deploy-agent/state.json`

```json
{
  "current_release_id": "uuid-or-null",
  "agent_state": "IDLE",
  "last_applied_at": "2026-03-08T10:00:00Z",
  "env_backups": {
    "rise": "/etc/container-runner/.env.backup.1709888000"
  }
}
```

## 기본값

| 항목 | 기본값 |
|------|--------|
| Polling interval | 30초 |
| Heartbeat interval | 60초 |
