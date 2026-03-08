# Release Manifest Spec

## 목적

Multi-service Release manifest의 JSON 스키마와 healthcheck profile 타입을 정의한다.

## Release Manifest 구조

Release는 Control Plane DB에 저장되며, Agent가 `GET /api/v1/agent/desired-release`를 통해 조회한다.

### Response JSON 형식

```json
{
  "release": {
    "id": "uuid",
    "release_name": "v2.1.0-rc1",
    "robot_model": "extreme",
    "status": "active",
    "created_by": "deploy-admin",
    "created_at": "2026-03-08T10:00:00Z",
    "services": [
      {
        "id": "uuid",
        "release_id": "uuid",
        "service_name": "rise",
        "image_repo": "samsung-humanoid-docker-remote.bart.sec.samsung.net/rise",
        "image_tag": "v2.1.0",
        "image_digest": "sha256:abcd1234567890abcd1234567890abcd1234567890abcd1234567890abcd1234",
        "healthcheck_profile": {
          "type": "http",
          "url": "http://127.0.0.1:8080/health",
          "interval_sec": 5,
          "timeout_sec": 60,
          "success_threshold": 3
        },
        "created_at": "2026-03-08T10:00:00Z"
      },
      {
        "id": "uuid",
        "release_id": "uuid",
        "service_name": "rise-dashboard",
        "image_repo": "samsung-humanoid-docker-remote.bart.sec.samsung.net/rise-dashboard",
        "image_tag": "v2.1.0",
        "image_digest": "sha256:def4567890abcdef4567890abcdef4567890abcdef4567890abcdef4567890ab",
        "healthcheck_profile": {
          "type": "tcp",
          "host": "127.0.0.1",
          "port": 3000,
          "interval_sec": 5,
          "timeout_sec": 30,
          "success_threshold": 2
        },
        "created_at": "2026-03-08T10:00:00Z"
      }
    ]
  }
}
```

## Healthcheck Profile 타입

### http

HTTP GET 요청으로 서비스 health를 확인한다.

```json
{
  "type": "http",
  "url": "http://127.0.0.1:8080/health",
  "interval_sec": 5,
  "timeout_sec": 60,
  "success_threshold": 3
}
```

- `url`: health 엔드포인트 URL
- `interval_sec`: 재시도 간격 (초)
- `timeout_sec`: 전체 healthcheck 타임아웃 (초)
- `success_threshold`: 성공으로 판정하기 위한 연속 성공 횟수

판정 로직: `timeout_sec` 내에 `success_threshold`회 연속 2xx 응답을 받으면 성공.

### tcp

TCP 소켓 연결로 포트 오픈 여부를 확인한다.

```json
{
  "type": "tcp",
  "host": "127.0.0.1",
  "port": 3000,
  "interval_sec": 5,
  "timeout_sec": 30,
  "success_threshold": 2
}
```

- `host`: 대상 호스트
- `port`: 대상 포트
- `interval_sec`: 재시도 간격 (초)
- `timeout_sec`: 전체 healthcheck 타임아웃 (초)
- `success_threshold`: 성공으로 판정하기 위한 연속 성공 횟수

### exec (Phase 2)

컨테이너 내부에서 명령을 실행하여 health를 확인한다.

```json
{
  "type": "exec",
  "command": ["python3", "-c", "import requests; requests.get('http://localhost:8080/health').raise_for_status()"],
  "interval_sec": 10,
  "timeout_sec": 60,
  "success_threshold": 1
}
```

### docker_health

Docker 자체 HEALTHCHECK에 의존한다. Agent가 별도 healthcheck를 수행하지 않고 `docker inspect`로 상태를 확인한다.

```json
{
  "type": "docker_health",
  "timeout_sec": 120
}
```

- POC에서는 docker_health가 지정되면 healthcheck를 skip하고 성공으로 간주한다.

## container-runner SERVICE_ENV_MAP 호환 규칙

Agent가 `.env` 파일의 이미지 참조를 갱신할 때, `generate_config.py`의 `SERVICE_ENV_MAP`과 동일한 매핑을 사용한다.

```python
SERVICE_ENV_MAP = {
    "rise": "RISE_IMAGE",
    "rise-dashboard": "RISE_DASHBOARD_IMAGE",
    "whole-body-controller": "WHOLE_BODY_CONTROLLER_IMAGE",
}
```

매핑에 없는 서비스는 `<SERVICE_NAME>_IMAGE` (upper, `-` → `_`) 형식으로 fallback한다.

### 이미지 참조 형식

`.env` 파일에 기록되는 이미지 참조 형식:

```
RISE_IMAGE=samsung-humanoid-docker-remote.bart.sec.samsung.net/rise:v2.1.0@sha256:abcd1234...
```

형식: `<registry>/<service>:<tag>@<digest>`

- `tag`는 사람이 읽기 위한 참조용
- `digest`가 실제 immutable 식별자
- compose fragment는 `${RISE_IMAGE}` 환경변수를 사용하므로 `.env`만 갱신하면 됨

## Release 생성 API 요청 예시

```bash
curl -X POST http://localhost:8000/api/v1/releases \
  -H "Content-Type: application/json" \
  -d '{
    "release_name": "v2.1.0-rc1",
    "robot_model": "extreme",
    "created_by": "deploy-admin",
    "services": [
      {
        "service_name": "rise",
        "image_repo": "samsung-humanoid-docker-remote.bart.sec.samsung.net/rise",
        "image_tag": "v2.1.0",
        "image_digest": "sha256:abcd1234567890abcd1234567890abcd1234567890abcd1234567890abcd1234",
        "healthcheck_profile": {
          "type": "http",
          "url": "http://127.0.0.1:8080/health",
          "interval_sec": 5,
          "timeout_sec": 60,
          "success_threshold": 3
        }
      },
      {
        "service_name": "rise-dashboard",
        "image_repo": "samsung-humanoid-docker-remote.bart.sec.samsung.net/rise-dashboard",
        "image_tag": "v2.1.0",
        "image_digest": "sha256:def4567890abcdef4567890abcdef4567890abcdef4567890abcdef4567890ab",
        "healthcheck_profile": {
          "type": "tcp",
          "host": "127.0.0.1",
          "port": 3000,
          "interval_sec": 5,
          "timeout_sec": 30,
          "success_threshold": 2
        }
      }
    ]
  }'
```
