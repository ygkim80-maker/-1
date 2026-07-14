# 배송 서명 플랫폼 (MVP)

카드배송 배송원의 교육 이수 서명을 현장에서 수집하고, 본사 대시보드에서 진척률을 확인할 수 있는
최소 기능 제품(MVP)입니다. 대화에서 설계한 "배송 서명 → 본사 대시보드" 데이터 흐름의 1~2단계를 구현합니다.

## 아키텍처

- **Backend**: FastAPI + SQLAlchemy + SQLite (ZENIEL WORKSPACE와 동일한 스택으로 확장 가능)
- **Frontend**: 별도 프레임워크 없이 Jinja2 템플릿 + Vanilla JS (앱 설치/로그인 없이 링크 접속만으로 서명 가능)
- **서명 캡처**: `<canvas>` 기반 자체 구현 (외부 라이브러리 의존 없음)

## 핵심 설계 반영 사항

1. **현장 실행 가능성 우선 (본인확인 절차 없음)**
   - 별도 인증 절차(사번/생년월일 등) 없이 QR/링크 접속 → 이름 직접 입력 → 서명만으로 완료
   - 배송원은 앱 설치나 로그인 없이 개인별 서명 링크(`/sign/{token}`)로 접속
   - 실제 운영 시 카카오 알림톡·QR로 링크 발송 예정 (본 MVP의 `/api/remind/{driver_id}`는 stub)

2. **최소한의 감사 기록**
   - 서명 시각(UTC), IP, User-Agent, 직접 입력한 이름 기록
   - 문서 내용 + 서명 이미지 + 입력 이름 + 시각을 SHA-256으로 묶어 위변조 확인용 해시 저장
   - `/certificate/{link_id}` 에서 증빙서(인쇄 → PDF 저장) 확인 가능
   - ⚠️ 본인확인 절차가 없으므로 "링크를 받은 사람이 실제 서명자인지"는 보증하지 않습니다.
     법적 증빙력이 필요한 대외 제출용이라면 사번/생년월일 확인 단계나
     모두싸인/카카오전자서명 등 검증된 전자서명 API 연동을 다시 추가하는 것을 권장합니다.

## 실행 방법

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 시드 데이터 생성 (지사 13개소, 배송원 356명 샘플)
python -m app.seed

# 서버 실행
uvicorn app.main:app --reload
```

- 대시보드: http://localhost:8000/dashboard
- 서명 페이지: `python -m app.seed` 실행 시 콘솔에 출력되는 샘플 링크 사용, 또는 대시보드의 "서명페이지" 링크 클릭

## 배포 (Render, 무료 플랜)

1. https://render.com 에서 GitHub 계정으로 가입/로그인 후, `ygkim80-maker` 계정의 GitHub 저장소 접근을 허용합니다.
2. Render 대시보드 → **New** → **Web Service** → 이 저장소(`ygkim80-maker/-1`)를 선택합니다.
3. 브랜치를 `claude/delivery-signature-flow-immdgv` 로 지정합니다.
4. 아래 값을 그대로 입력합니다.
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free
5. **Create Web Service** 클릭 후 2~3분 기다리면 `https://[서비스명].onrender.com` 형태의 URL이 발급됩니다. `/dashboard`, `/sign/{token}` 경로로 바로 접속 가능합니다.

⚠️ 무료 플랜은 SQLite 파일이 **재배포 시 초기화**됩니다(시드 데이터로 리셋). 서명 기록을 계속 보존하려면
Postgres 애드온이나 유료 플랜의 영구 디스크(Persistent Disk) 연결이 필요합니다. 리포지토리에 포함된
`render.yaml`을 사용하면 Blueprint 배포로 같은 설정을 한 번에 적용할 수도 있습니다.

## 데이터 모델

`Site`(지사) → `Driver`(배송원) → `SigningLink`(문서별 서명 링크) → `Signature`(서명 기록)
`EducationDocument`는 서명 대상 교육/공지 문서로 버전 관리가 가능합니다.

## 로드맵

1. ✅ 1단계: 교육 콘텐츠 + 서명 링크 (알림톡 발송은 stub) — 본 MVP
2. ✅ 2단계: 본사 대시보드 진척률 시각화 — 본 MVP
   - ⏳ 미서명자 자동 리마인드는 stub만 구현 (카카오 알림톡 API 연동 필요)
3. 🔜 3단계: 고객사 제출용 PDF 자동 생성 — 현재는 브라우저 인쇄로 대체, 서버 사이드 PDF 생성(예: WeasyPrint) 연동 예정
4. 🔜 4단계: 전국 확대, 검증된 전자서명 API(모두싸인/카카오전자서명) 연동

## 보안 · 개인정보 주의사항

배송원 개인정보(생년월일, 휴대폰번호, 서명 이미지)가 포함되므로, 운영 배포 전 반드시 아래를 점검하세요.

- DB 암호화(at-rest) 및 접근 통제
- 원청(예: CJ대한통운) 제출 시 개인정보 마스킹 범위
- 개인정보보호법상 수집·보관 근거 및 보관 기간

이 저장소는 데모/MVP 목적이며, 시드 스크립트가 생성하는 배송원 정보는 모두 가상의 샘플 데이터입니다.
