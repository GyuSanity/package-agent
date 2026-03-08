# Git Commit and Push Command

GitHub 저장소에 현재까지 생성한 소스를 커밋하고 푸시합니다.

## 주요 작업

1. **변경사항 확인**
   - `git status`로 현재 변경사항 확인
   - `git diff`로 변경 내용 상세 검토
   - 스테이징된 파일과 미스테이징 파일 모두 확인

2. **커밋 메시지 작성 규칙**
   - **한국어로 작성**: 모든 커밋 메시지는 한국어로 작성
   - **간결하고 명확하게**: 무엇을, 왜 변경했는지 명확히 표현
   - **최근 커밋 스타일 참고**: `git log --oneline -10`으로 기존 커밋 메시지 패턴 확인
   - **타입 접두사 사용** (선택적, 프로젝트에 따라):
     - `추가:` - 새로운 기능 추가
     - `수정:` - 기존 기능 개선
     - `버그수정:` - 버그 수정
     - `리팩토링:` - 코드 구조 개선
     - `문서:` - 문서 업데이트
     - `테스트:` - 테스트 추가/수정
     - `의존성:` - 의존성 패키지 업데이트

3. **보안 확인**
   - `.env` 파일, `credentials.json` 등 민감 정보 커밋 방지
   - `.gitignore` 설정 검토
   - API 키, 비밀번호 등 하드코딩 여부 확인
   - 사용자가 명시적으로 요청해도 민감 정보 커밋 시 경고

 

4. **초기 프로젝트 처리**
   - 원격 저장소가 없는 경우 새로 생성
   - 별도 지시가 없으면 **public** 저장소로 생성
   - `git remote add origin` 자동 설정
   - 첫 커밋 후 `git push -u origin main`으로 업스트림 설정

5. **커밋 실행**
   - 관련 변경사항을 스테이징 영역에 추가
   - 의미 있는 단위로 파일 그룹화
   - 커밋 메시지 하단에 Claude Code 서명 추가:
     ```

     🤖 Generated with [Claude Code](https://claude.com/claude-code)

     Co-Authored-By: Claude <noreply@anthropic.com>
     ```

6. **푸시 전 확인**
   - 현재 브랜치 확인
   - 원격 저장소 연결 상태 확인
   - 푸시 권한 확인

7. **푸시 실행**
   - `git push` 또는 `git push -u origin <branch>` 실행
   - **주의**: `--force` 플래그는 사용자가 명시적으로 요청한 경우에만 사용
   - main/master 브랜치에 force push 시도 시 사용자에게 경고

8. **사후 확인**
   - `git status`로 푸시 성공 여부 확인
   - "Your branch is up to date" 메시지 확인
   - 원격 저장소 URL 제공 (가능한 경우)

## 예외 처리

- **충돌 발생 시**: 사용자에게 충돌 내용 설명 및 해결 방법 안내
- **권한 오류**: 인증 문제 해결 방법 안내
- **대용량 파일**: Git LFS 사용 권장
- **커밋할 내용 없음**: 빈 커밋 생성하지 않고 사용자에게 알림

## Git Hook 처리

- pre-commit hook이 파일을 수정한 경우:
  - 작성자 확인: `git log -1 --format='%an %ae'`
  - 푸시 여부 확인: `git status`에서 "Your branch is ahead" 확인
  - 둘 다 true인 경우에만 `git commit --amend`
  - 그렇지 않으면 새 커밋 생성 (다른 개발자의 커밋은 절대 amend 금지)

 

## 금지 사항

- **절대 실행하지 말 것**:
  - `git config` 변경
  - `git push --force` (명시적 요청 없이)
  - `git reset --hard` (명시적 요청 없이)
  - `git clean -fd` (명시적 요청 없이)
  - `--no-verify`, `--no-gpg-sign` 플래그 사용 (명시적 요청 없이)
  - `-i` 플래그를 사용한 인터랙티브 명령 (`git rebase -i`, `git add -i` 등)
