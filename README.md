# 까르띠에 재고 확인 - Railway 웹 버전

까르띠에 공식 홈페이지의 제품 재고를 모니터링하고, 재고 입고 시 텔레그램으로 알림을 보내는 웹 애플리케이션입니다.

## 기능

- ✅ 웹 UI로 제품 URL 관리
- ✅ 실시간 재고 모니터링
- ✅ 재고 입고 시 텔레그램 알림
- ✅ 체크 간격 조절 (30초 ~ 10분)
- ✅ 24시간 자동 구동

## Railway 배포 방법

### 1. GitHub에 업로드

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/cartier-stock.git
git push -u origin main
```

### 2. Railway 배포

1. [Railway](https://railway.app) 접속
2. GitHub으로 로그인
3. "New Project" → "Deploy from GitHub repo"
4. 저장소 선택
5. 자동 배포 시작 (약 3-5분 소요)

### 3. 환경 변수 (선택)

Railway Dashboard → Variables에서 설정:

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `TELEGRAM_TOKEN` | 텔레그램 봇 토큰 | 내장됨 |
| `TELEGRAM_CHAT_ID` | 텔레그램 채팅 ID | 내장됨 |

## 사용법

1. 배포 완료 후 Railway에서 제공하는 URL 접속
2. 모니터링할 까르띠에 제품 URL 추가
3. "모니터링 시작" 클릭
4. 재고 입고 시 텔레그램으로 알림 수신

## 요금

- **Railway 무료 플랜**: 월 $5 크레딧 (약 500시간)
- **Hobby 플랜**: 월 $5 (무제한)

이 프로그램은 무료 범위 내에서 충분히 구동 가능합니다.

## 주의사항

- 너무 짧은 간격(30초)으로 체크하면 IP 차단 가능성 있음
- 권장 체크 간격: 1~3분
