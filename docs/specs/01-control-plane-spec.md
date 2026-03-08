# Control Plane Spec

## 개요

FastAPI 기반 Control Plane. PostgreSQL을 사용하여 디바이스, Release, Deployment 상태를 관리한다.

## DB Schema

### `devices`

| Column | Type | 설명 |
|--------|------|------|
| id | UUID (PK) | 디바이스 고유 ID |
| device_name | VARCHAR (UNIQUE) | 디바이스 이름 (hostname) |
| robot_model | VARCHAR | 로봇 모델명 |
| status | ENUM(`online`, `offline`) | 디바이스 상태 |
| current_release_id | UUID (FK → releases.id, nullable) | 현재 적용된 Release |
| desired_release_id | UUID (FK → releases.id, nullable) | 적용 대상 Release |
| auth_key_hash | VARCHAR | 인증 키 해시 |
| last_seen_at | TIMESTAMP | 마지막 heartbeat 시각 |
| created_at | TIMESTAMP | 생성 시각 |
| updated_at | TIMESTAMP | 수정 시각 |

### `releases`

| Column | Type | 설명 |
|--------|------|------|
| id | UUID (PK) | Release 고유 ID |
| release_name | VARCHAR | Release 이름 (예: v2.1.0-rc1) |
| robot_model | VARCHAR | 대상 로봇 모델 |
| status | ENUM(`draft`, `active`, `deprecated`) | Release 상태 |
| created_by | VARCHAR | 생성자 |
| created_at | TIMESTAMP | 생성 시각 |

### `release_services`

| Column | Type | 설명 |
|--------|------|------|
| id | UUID (PK) | 서비스 항목 ID |
| release_id | UUID (FK → releases.id) | 소속 Release |
| service_name | VARCHAR | 서비스 이름 (예: rise, rise-dashboard) |
| image_repo | VARCHAR | 이미지 레포지토리 |
| image_tag | VARCHAR | 이미지 태그 |
| image_digest | VARCHAR | 이미지 digest (sha256) |
| healthcheck_profile | JSONB | 헬스체크 프로파일 |
| created_at | TIMESTAMP | 생성 시각 |

### `deployments`

| Column | Type | 설명 |
|--------|------|------|
| id | UUID (PK) | Deployment 고유 ID |
| release_id | UUID (FK → releases.id) | 배포할 Release |
| deployment_name | VARCHAR | Deployment 이름 |
| target_type | ENUM(`model`, `device_list`) | 대상 유형 |
| target_selector | JSONB | 대상 선택자 (모델명 또는 디바이스 ID 목록) |
| strategy | VARCHAR | 배포 전략 (기본: `all_at_once`) |
| status | ENUM(`pending`, `in_progress`, `completed`, `failed`, `cancelled`) | 배포 상태 |
| created_by | VARCHAR | 생성자 |
| created_at | TIMESTAMP | 생성 시각 |
| started_at | TIMESTAMP (nullable) | 시작 시각 |
| finished_at | TIMESTAMP (nullable) | 완료 시각 |

### `deployment_targets`

| Column | Type | 설명 |
|--------|------|------|
| id | UUID (PK) | 대상 항목 ID |
| deployment_id | UUID (FK → deployments.id) | 소속 Deployment |
| device_id | UUID (FK → devices.id) | 대상 디바이스 |
| desired_release_id | UUID (FK → releases.id) | 적용할 Release |
| state | ENUM(`pending`, `downloading`, `applying`, `verifying`, `succeeded`, `failed`, `rolled_back`) | 개별 디바이스 배포 상태 |
| attempt_count | INTEGER | 시도 횟수 |
| last_error | TEXT (nullable) | 마지막 에러 메시지 |
| updated_at | TIMESTAMP | 수정 시각 |

### `agent_reports`

| Column | Type | 설명 |
|--------|------|------|
| id | UUID (PK) | 리포트 ID |
| device_id | UUID (FK → devices.id) | 리포트 출처 디바이스 |
| report_type | ENUM(`heartbeat`, `state_change`, `error`) | 리포트 유형 |
| agent_state | VARCHAR | Agent 상태 |
| payload | JSONB | 리포트 상세 데이터 |
| created_at | TIMESTAMP | 생성 시각 |

## API Endpoints

### 인증

모든 Agent 요청은 `X-Device-Auth-Key` 헤더로 인증한다.

### Device API

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/devices` | 디바이스 등록 |
| GET | `/api/v1/devices` | 디바이스 목록 조회 |
| GET | `/api/v1/devices/{id}` | 디바이스 상세 조회 |

**POST /api/v1/devices** Request:
```json
{
  "device_name": "robot-01",
  "robot_model": "humanoid-v2",
  "auth_key": "random-secret-key"
}
```

### Release API

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/releases` | Release 생성 (multi-service) |
| GET | `/api/v1/releases` | Release 목록 조회 |
| GET | `/api/v1/releases/{id}` | Release 상세 조회 |

**POST /api/v1/releases** Request:
```json
{
  "release_name": "v2.1.0-rc1",
  "robot_model": "humanoid-v2",
  "created_by": "deployer",
  "services": [
    {
      "service_name": "rise",
      "image_repo": "samsung-humanoid-docker-remote.bart.sec.samsung.net/rise",
      "image_tag": "v2.1.0",
      "image_digest": "sha256:abc123...",
      "healthcheck_profile": {
        "type": "http",
        "url": "http://localhost:8080/health",
        "interval": 5,
        "timeout": 10,
        "success_threshold": 3
      }
    },
    {
      "service_name": "rise-dashboard",
      "image_repo": "samsung-humanoid-docker-remote.bart.sec.samsung.net/rise-dashboard",
      "image_tag": "v2.1.0",
      "image_digest": "sha256:def456...",
      "healthcheck_profile": {
        "type": "tcp",
        "host": "localhost",
        "port": 3000
      }
    }
  ]
}
```

### Deployment API

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/deployments` | Deployment 생성 |
| GET | `/api/v1/deployments` | Deployment 목록 조회 |
| GET | `/api/v1/deployments/{id}` | Deployment 상세 조회 (targets 포함) |

**POST /api/v1/deployments** Request:
```json
{
  "deployment_name": "deploy-v2.1.0-rc1",
  "release_id": "uuid-of-release",
  "target_type": "model",
  "target_selector": { "robot_model": "humanoid-v2" },
  "strategy": "all_at_once",
  "created_by": "deployer"
}
```

### Agent API

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/agent/heartbeat` | Heartbeat 전송 |
| GET | `/api/v1/agent/desired-release` | Desired Release 조회 |
| POST | `/api/v1/agent/report` | 상태 변경/에러 리포트 전송 |

**POST /api/v1/agent/heartbeat** Request:
```json
{
  "device_name": "robot-01",
  "agent_state": "IDLE",
  "current_release_id": "uuid-or-null"
}
```

**GET /api/v1/agent/desired-release** Response:
```json
{
  "release_id": "uuid",
  "release_name": "v2.1.0-rc1",
  "services": [
    {
      "service_name": "rise",
      "image_ref": "samsung-humanoid-docker-remote.bart.sec.samsung.net/rise:v2.1.0@sha256:abc123...",
      "healthcheck_profile": { "type": "http", "url": "http://localhost:8080/health", "interval": 5, "timeout": 10, "success_threshold": 3 }
    }
  ]
}
```

**POST /api/v1/agent/report** Request:
```json
{
  "device_name": "robot-01",
  "report_type": "state_change",
  "agent_state": "SUCCEEDED",
  "payload": {
    "release_id": "uuid",
    "services_applied": ["rise", "rise-dashboard"]
  }
}
```
