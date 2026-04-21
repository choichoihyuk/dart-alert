# dart-alert

DART 공시("임원·주요주주 특정증권등 소유상황보고서") 실시간 텔레그램 알림 봇. "장내매수" 또는 "증여" 포함 건만 전송.

## 로컬 실행
1. `pip install -r requirements.txt`
2. `.env.example`을 `.env`로 복사 후 값 채우기
3. `python main.py`

## GitHub Actions 24/7 무료 배포 (공개 저장소)

공개 저장소는 GitHub Actions 무료 분 무제한. 5분마다 한 번씩 폴링 → 신규 공시 있으면 텔레그램 전송.

### 사전 준비
- 텔레그램 봇 토큰 / 채팅 ID
- DART API 키

### 1. Git 저장소 초기화 (dart-alert 폴더에서)
```powershell
cd C:\Users\cjh09\dart-alert
git init -b main
git add .
git commit -m "Initial dart-alert bot"
```

`.gitignore`가 `.env`, `sent.db`, `__pycache__/`, `_probe_*.py`를 제외하므로 시크릿/상태 파일은 커밋되지 않음.

### 2. GitHub 공개 저장소 생성 후 푸시
```powershell
gh repo create dart-alert --public --source=. --push
# 또는 GitHub UI에서 생성 후:
# git remote add origin https://github.com/<user>/dart-alert.git
# git push -u origin main
```

### 3. GitHub Secrets 등록
저장소 > Settings > Secrets and variables > Actions > "New repository secret"로 3개 등록:
- `DART_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### 4. 첫 실행
- Actions 탭 → "dart-alert poll" 워크플로우 → "Run workflow" (수동 실행)
- 이후 5분마다 자동 실행 (cron `*/5 * * * *`)
- 첫 실행은 bootstrap (기존 공시 전체 skip 마킹, 전송 없음)
- 두 번째 실행부터 신규 공시만 매칭 → 텔레그램 알림

### 상태 저장
`sent.db`는 Actions Cache(`dart-alert-db-<run_id>`)로 run 간 유지됨. 7일 이상 미실행 시 캐시 삭제 → 재부트스트랩.

### 로그 확인
Actions 탭 → 각 run → "Run poll (one-shot)" 스텝에서 로그 확인.

## 파일 구조
- `main.py` — 오케스트레이션 (무한 루프 모드 / `RUN_ONCE=1` 원샷 모드)
- `dart_api.py` — DART `list.json` + `document.xml`
- `filter_rule.py` — "장내매수"/"증여" 키워드 매칭
- `telegram_send.py` — 텔레그램 `sendMessage` HTML
- `store.py` — SQLite 중복 전송 방지
- `.github/workflows/poll.yml` — GitHub Actions 스케줄
