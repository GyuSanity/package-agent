# Robot Edge Deployment Platform - Handoff Document

## 작업 요약

로봇 엣지 디바이스에 desired-state 기반 자동 배포/롤백을 수행하는 POC 플랫폼을 구현했다.
기존 `containner-runner`의 bootstrap 흐름 위에 Control Plane(FastAPI) + Agent(Python)를 추가했다.

---

## 완료된 작업

### Phase 0: 스펙 문서 (6/6 완료)

| 파일 | 상태 |
|------|------|
| `docs/specs/00-overview.md` | 완료 |
| `docs/specs/01-control-plane-spec.md` | 완료 |
| `docs/specs/02-agent-spec.md` | 완료 |
| `docs/specs/03-container-runner-bootstrap-spec.md` | 완료 |
| `docs/specs/04-release-manifest-spec.md` | 완료 |
| `docs/specs/05-integration-test-plan.md` | 완료 |

### Phase 1-1: Control Plane (`control-plane/`) - 완료

FastAPI + PostgreSQL + Alembic 기반 백엔드.

**구조:**
```
control-plane/
├── app/
│   ├── main.py                    # FastAPI 앱 + 라우터 등록
│   ├── config.py                  # pydantic-settings (DATABASE_URL)
│   ├── database.py                # AsyncSession (asyncpg)
│   ├── models/models.py           # 6개 테이블 (Device, Release, ReleaseService, Deployment, DeploymentTarget, AgentReport)
│   ├── schemas/schemas.py         # Pydantic v2 request/response
│   ├── routers/
│   │   ├── devices.py             # POST/GET /api/v1/devices
│   │   ├── releases.py            # POST/GET /api/v1/releases (multi-service)
│   │   ├── deployments.py         # POST/GET /api/v1/deployments
│   │   └── agent.py               # heartbeat, desired-release, report + X-Device-Auth-Key 인증
│   ├── services/
│   │   ├── device_service.py      # 등록/목록/조회, sha256 auth key hash
│   │   ├── release_service.py     # multi-service release 생성
│   │   ├── deployment_service.py  # 대상 디바이스 자동 계산 (model/device_list), targets 생성
│   │   └── agent_service.py       # heartbeat 갱신, desired vs current 비교, deployment 완료 판정
│   └── repositories/base.py       # 공통 get_by_id/get_all
├── alembic/
│   ├── env.py                     # sync DB URL로 migration
│   ├── script.mako
│   └── versions/001_initial.py    # 6개 테이블 초기 migration
├── docker-compose.yml             # PostgreSQL 16 + FastAPI app
├── Dockerfile                     # python:3.11-slim + uvicorn
├── alembic.ini
└── requirements.txt
```

**API 엔드포인트:**
| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/devices` | 디바이스 등록 |
| GET | `/api/v1/devices` | 디바이스 목록 (robot_model/status 필터) |
| GET | `/api/v1/devices/{id}` | 디바이스 상세 |
| POST | `/api/v1/releases` | Multi-service Release 생성 |
| GET | `/api/v1/releases` | Release 목록 |
| GET | `/api/v1/releases/{id}` | Release 상세 |
| POST | `/api/v1/deployments` | Deployment 생성 + 대상 자동 계산 |
| GET | `/api/v1/deployments` | Deployment 목록 |
| GET | `/api/v1/deployments/{id}` | Deployment 상세 (targets 포함) |
| POST | `/api/v1/agent/heartbeat` | Agent heartbeat (last_seen_at 갱신) |
| GET | `/api/v1/agent/desired-release` | desired release 조회 |
| POST | `/api/v1/agent/report` | Agent 상태/결과 보고 |

**인증:** `X-Device-Auth-Key` 헤더 → SHA256 hash 비교

**DB 스키마:** 6개 테이블
- `devices` — device_name, robot_model, current/desired_release_id, auth_key_hash
- `releases` — release_name, robot_model, status (draft/active/deprecated)
- `release_services` — release_id, service_name, image_repo/tag/digest, healthcheck_profile (JSON)
- `deployments` — release_id, target_type/selector, strategy, status
- `deployment_targets` — deployment_id, device_id, state (pending→downloading→...→succeeded/failed/rolled_back)
- `agent_reports` — device_id, report_type, agent_state, payload

### Phase 1-2: Agent (`robot-deploy-agent/`) - 완료

Python 에이전트. Control Plane을 polling하여 desired state 기반 배포/롤백을 수행한다.

**구조:**
```
robot-deploy-agent/
├── agent/
│   ├── main.py              # 진입점 + polling loop + reconcile()
│   ├── config.py             # YAML config 로드 (dataclass)
│   ├── state_machine.py      # 10개 상태 enum + 전이 규칙 검증
│   ├── api_client.py         # HTTP client (requests + retry/backoff)
│   ├── docker_manager.py     # docker pull subprocess
│   ├── systemd_manager.py    # systemctl restart/is-active
│   ├── healthcheck.py        # tcp/http/docker_health 검증
│   ├── rollback.py           # .env 백업/복원 + restart
│   ├── meta_renderer.py      # .env 이미지 참조 갱신 (SERVICE_ENV_MAP 호환)
│   └── local_state.py        # JSON state 저장/로드
├── config/agent.yaml.example
├── systemd/robot-deploy-agent.service
└── requirements.txt
```

**상태머신:** `IDLE → CHECKING → DOWNLOADING → READY_TO_APPLY → APPLYING → VERIFYING → SUCCEEDED / ROLLING_BACK → ROLLED_BACK / FAILED`

**Reconciliation 흐름:**
1. desired release 조회 → 현재와 비교
2. 모든 서비스 이미지 pre-pull (`docker pull <repo>@<digest>`)
3. `.env` 백업 → 새 digest로 `.env` 갱신
4. `systemctl restart <service>-container.service`
5. healthcheck profile에 따라 검증 (http/tcp/docker_health)
6. 성공 → SUCCEEDED, 실패 → `.env.bak` 복원 + restart (rollback)

**container-runner 호환:**
- `SERVICE_ENV_MAP` 동일 사용 (rise→RISE_IMAGE, rise-dashboard→RISE_DASHBOARD_IMAGE)
- `.env` 파일 형식: `<ENV_KEY>=<registry>/<service>:<tag>@<digest>`
- compose fragment/systemd unit은 container-runner가 생성한 것을 그대로 사용

### Phase 1-3: Container-Runner Bootstrap 수정 - 완료

`containner-runner/scripts/setup.sh`에 agent 설치/시작 단계 추가:
- `/opt/robot-deploy-agent` 존재 시 agent 설정 자동 생성
- hostname 기반 device_name, ROBOT_MODEL 자동 설정
- systemd unit 등록 + enable
- auth_key가 미설정(CHANGE_ME)이면 start하지 않음 (안전장치)

---

## 미완료 / 추가 필요 작업

### 즉시 필요

1. **Control Plane 실행 테스트**: `docker compose up` → Alembic migration → API 테스트
2. **Agent 실행 테스트**: config.yaml 설정 후 `python3 -m agent.main` 로컬 실행
3. **E2E 통합 테스트**: `docs/specs/05-integration-test-plan.md` 시나리오 수행

### Phase 2 (운영 기능)

- Group/Fleet targeting 확장
- Deployment pause/resume/abort API
- 실패율 기반 자동 중단
- 디바이스 오프라인 감지 (heartbeat timeout)
- Audit log
- FE Console 최소 구현 (`deploy-console/`)

### Phase 3 (프로덕션 강화)

- 인증 강화 (mTLS/JWT)
- Canary rollout
- Maintenance window
- 이미지 서명 검증 (Cosign)
- 디스크 GC
- 기존 인프라 통합

---

## 실행 방법

### Control Plane 기동

```bash
cd control-plane

# Docker Compose로 PostgreSQL + FastAPI 기동
docker compose up -d

# DB 마이그레이션
pip install -r requirements.txt
alembic upgrade head

# (또는 컨테이너 내부에서)
docker compose exec app alembic upgrade head
```

API 확인: http://localhost:8000/docs (Swagger UI)

### Agent 로컬 실행

```bash
cd robot-deploy-agent

pip install -r requirements.txt

# config 설정
cp config/agent.yaml.example /tmp/agent.yaml
# /tmp/agent.yaml 편집: control_plane_url, device_name, auth_key 등

# 실행
AGENT_CONFIG_PATH=/tmp/agent.yaml python3 -m agent.main
```

### E2E 테스트 흐름

```bash
# 1. Device 등록
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{"device_name":"robot-001","robot_model":"extreme","auth_key":"my-secret"}'

# 2. Release 생성
curl -X POST http://localhost:8000/api/v1/releases \
  -H "Content-Type: application/json" \
  -d '{"release_name":"v1.0","robot_model":"extreme","created_by":"admin","services":[{"service_name":"rise","image_repo":"registry/rise","image_tag":"v1.0","image_digest":"sha256:abc123","healthcheck_profile":{"type":"docker_health","timeout_sec":60}}]}'

# 3. Deployment 생성
curl -X POST http://localhost:8000/api/v1/deployments \
  -H "Content-Type: application/json" \
  -d '{"release_id":"<RELEASE_ID>","deployment_name":"deploy-1","target_type":"model","target_selector":{"robot_model":"extreme"},"strategy":"all_at_once","created_by":"admin"}'

# 4. Agent가 자동으로 desired release를 polling하여 배포 수행

# 5. 결과 확인
curl http://localhost:8000/api/v1/deployments/<DEPLOYMENT_ID>
```

---

## 핵심 파일 경로

| 구분 | 파일 | 설명 |
|------|------|------|
| 스펙 | `docs/specs/00-overview.md` | 전체 개요 |
| CP 진입점 | `control-plane/app/main.py` | FastAPI 앱 |
| CP 모델 | `control-plane/app/models/models.py` | DB 모델 6개 테이블 |
| CP 스키마 | `control-plane/app/schemas/schemas.py` | Pydantic v2 DTO |
| CP 핵심로직 | `control-plane/app/services/agent_service.py` | heartbeat/desired-release/report 처리 |
| CP 배포로직 | `control-plane/app/services/deployment_service.py` | 대상 디바이스 자동 계산 |
| Agent 진입점 | `robot-deploy-agent/agent/main.py` | polling loop + reconcile |
| Agent 상태머신 | `robot-deploy-agent/agent/state_machine.py` | 10 상태 + 전이 규칙 |
| Agent 롤백 | `robot-deploy-agent/agent/rollback.py` | .env 백업/복원 |
| Agent .env 갱신 | `robot-deploy-agent/agent/meta_renderer.py` | SERVICE_ENV_MAP 호환 |
| Bootstrap 수정 | `containner-runner/scripts/setup.sh` | agent 설치/시작 추가 |
| 아키텍처 원본 | `docs/robot_edge_deployment_architecture.md` | 설계 기반 문서 |
