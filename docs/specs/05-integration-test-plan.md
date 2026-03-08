# Integration Test Plan

## 목적

Control Plane + Agent 간 E2E 배포 시나리오를 검증한다.

## 테스트 환경

```
docker compose up  (Control Plane + PostgreSQL)
python3 -m agent.main  (Agent 로컬 실행)
```

## 사전 조건

1. Control Plane이 `localhost:8000`에서 실행 중
2. PostgreSQL이 실행 중이고 마이그레이션 완료
3. Agent가 `localhost:8000`을 polling하도록 설정

---

## Scenario 1: E2E 정상 배포

### 1-1. Device 등록

```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{
    "device_name": "robot-test-001",
    "robot_model": "extreme",
    "auth_key": "test-secret-key"
  }'
```

검증: 201 응답, device_id 반환

### 1-2. Release 생성 (multi-service)

```bash
curl -X POST http://localhost:8000/api/v1/releases \
  -H "Content-Type: application/json" \
  -d '{
    "release_name": "v2.1.0-rc1",
    "robot_model": "extreme",
    "created_by": "test-admin",
    "services": [
      {
        "service_name": "rise",
        "image_repo": "samsung-humanoid-docker-remote.bart.sec.samsung.net/rise",
        "image_tag": "v2.1.0",
        "image_digest": "sha256:abc123",
        "healthcheck_profile": {"type": "docker_health", "timeout_sec": 60}
      },
      {
        "service_name": "rise-dashboard",
        "image_repo": "samsung-humanoid-docker-remote.bart.sec.samsung.net/rise-dashboard",
        "image_tag": "v2.1.0",
        "image_digest": "sha256:def456",
        "healthcheck_profile": {"type": "tcp", "host": "127.0.0.1", "port": 3000, "interval_sec": 5, "timeout_sec": 30, "success_threshold": 2}
      }
    ]
  }'
```

검증: 201 응답, release_id + 2개 service 반환

### 1-3. Deployment 생성

```bash
curl -X POST http://localhost:8000/api/v1/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "release_id": "<release_id>",
    "deployment_name": "test-deploy-1",
    "target_type": "model",
    "target_selector": {"robot_model": "extreme"},
    "strategy": "all_at_once",
    "created_by": "test-admin"
  }'
```

검증:
- 201 응답
- deployment.status == "in_progress"
- targets 배열에 robot-test-001 포함
- target.state == "pending"

### 1-4. Agent Polling 확인

Agent 실행 후 로그 확인:
- `GET /api/v1/agent/desired-release?device_name=robot-test-001` 호출
- desired release 수신

### 1-5. 배포 완료 확인

```bash
curl http://localhost:8000/api/v1/deployments/<deployment_id>
```

검증:
- target.state == "succeeded"
- device.current_release_id == release_id

---

## Scenario 2: 이미지 Pull 실패 → FAILED

### 설정
- Release의 image_digest를 존재하지 않는 digest로 설정

### 예상 결과
1. Agent가 DOWNLOADING 상태 진입
2. `docker pull` 실패
3. Agent가 FAILED 상태 보고
4. `.env` 파일 변경 없음 (pull 단계에서 중단)
5. deployment_target.state == "failed"

---

## Scenario 3: Healthcheck 실패 → 자동 Rollback

### 설정
1. 정상 release로 먼저 배포 (Scenario 1 완료)
2. 새 release 생성 (healthcheck 실패할 이미지)
   - healthcheck_profile을 실패할 조건으로 설정 (예: 닫힌 포트에 TCP check)
3. Deployment 생성

### 예상 결과
1. Agent가 새 이미지 pull 성공
2. `.env` 갱신 + 기존 `.env.bak` 백업
3. `systemctl restart` 수행
4. healthcheck 실패
5. Agent가 ROLLING_BACK 상태 진입
6. `.env.bak` → `.env` 복원
7. `systemctl restart` 다시 수행
8. Agent가 ROLLED_BACK 상태 보고
9. deployment_target.state == "rolled_back"

---

## Scenario 4: Heartbeat 정상 동작

### 검증

```bash
# Device의 last_seen_at이 업데이트되는지 확인
curl http://localhost:8000/api/v1/devices/<device_id>
```

- Agent가 heartbeat_interval_sec마다 POST /api/v1/agent/heartbeat 호출
- device.last_seen_at이 갱신됨
- device.status == "online"

---

## Scenario 5: 인증 실패

### 검증

```bash
curl -X GET "http://localhost:8000/api/v1/agent/desired-release?device_name=robot-test-001" \
  -H "X-Device-Auth-Key: wrong-key"
```

- 401 Unauthorized 응답

---

## Scenario 6: 동일 Release 재적용 (Idempotency)

### 설정
1. Scenario 1 완료 후 동일 release로 다시 Deployment 생성

### 예상 결과
- Agent가 desired release 수신
- current_release_id == desired release id이므로 IDLE로 복귀
- 불필요한 pull/restart가 발생하지 않음

---

## 수동 검증 체크리스트

- [ ] `docker compose up` 으로 Control Plane 기동
- [ ] curl로 device 등록
- [ ] curl로 release 생성 (multi-service)
- [ ] curl로 deployment 생성
- [ ] Agent 로컬 실행 후 desired-release polling 확인
- [ ] Agent 로그에서 이미지 pull 확인
- [ ] `.env` 파일 갱신 확인
- [ ] `systemctl restart` 수행 확인
- [ ] healthcheck 수행 확인
- [ ] Control Plane에서 deployment_targets 상태 변경 확인
- [ ] 의도적 healthcheck 실패로 rollback 동작 검증
- [ ] `.env.bak` 복원 확인
