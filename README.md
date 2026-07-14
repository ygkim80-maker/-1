# 배송 서명 플랫폼 (MVP)

카드배송 배송원의 교육 이수 서명을 현장에서 수집하고, 본사 대시보드에서 진척률을 확인할 수 있는
최소 기능 제품(MVP)입니다. 대화에서 설계한 "배송 서명 → 본사 대시보드" 데이터 흐름의 1~2단계를 구현합니다.

## 아키텍처

- **Backend**: FastAPI + SQLAlchemy + SQLite (ZENIEL WORKSPACE와 동일한 스택으로 확장 가능)
- **Frontend**: 별도 프레임워크 없이 Jinja2 템플릿 + Vanilla JS
- **서명 캡처**: `<canvas>` 기반 자체 구현 (외부 라이브러리 의존 없음)

## 핵심 설계 반영 사항

1. **QR 코드 하나로 전 지사 공용 (본인확인 절차 없음, 개인별 링크 없음)**
   - `/qr` 페이지의 QR 코드 **하나만** 인쇄해서 모든 지사에 게시하면 됩니다.
   - 배송원은 앱 설치나 로그인, 개인별 링크 없이 QR을 스캔해 `/sign` 페이지로 접속 →
     소속 지사와 이름을 직접 입력 → 서명만으로 완료됩니다.
   - 별도 인증 절차(사번/생년월일 등)가 없어 현장 이탈률이 낮습니다.

2. **최소한의 감사 기록**
   - 서명 시각(UTC), IP, User-Agent, 직접 입력한 이름·소속 기록
   - 문서 내용 + 서명 이미지 + 입력 이름 + 소속 + 시각을 SHA-256으로 묶어 위변조 확인용 해시 저장
   - `/certificate/{signature_id}` 에서 증빙서(인쇄 → PDF 저장) 확인 가능
   - ⚠️ 본인확인 절차와 개인별 링크가 없으므로, "실제 서명자 본인인지"와 "중복 서명 방지"는
     보증하지 않습니다. 법적 증빙력이 필요한 대외 제출용이라면 사번/생년월일 확인 단계나
     모두싸인/카카오전자서명 등 검증된 전자서명 API 연동을 다시 추가하는 것을 권장합니다.

## 실행 방법

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 시드 데이터 생성 (지사 13개소, 예상 인원 합계 356명)
python -m app.seed

# 서버 실행
uvicorn app.main:app --reload
```

- 대시보드: http://localhost:8000/dashboard
- 공용 서명 QR: http://localhost:8000/qr (인쇄용 페이지, 전 지사 동일 QR)
- 서명 페이지: http://localhost:8000/sign (QR을 스캔하면 도착하는 페이지, 직접 접속도 가능)

## 배포 (Render, 무료 플랜)

1. https://render.com 에서 GitHub 계정으로 가입/로그인 후, `ygkim80-maker` 계정의 GitHub 저장소 접근을 허용합니다.
2. Render 대시보드 → **New** → **Web Service** → 이 저장소를 선택합니다.
3. 브랜치를 `claude/delivery-signature-flow-immdgv` 로 지정합니다.
4. 아래 값을 그대로 입력합니다.
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free
5. **Create Web Service** 클릭 후 2~3분 기다리면 `https://[서비스명].onrender.com` 형태의 URL이 발급됩니다.
   `/qr` 페이지를 인쇄해서 게시하면 바로 사용할 수 있습니다.

⚠️ 무료 플랜은 SQLite 파일이 **재배포 시 초기화**됩니다(시드 데이터로 리셋). 서명 기록을 계속 보존하려면
Postgres 애드온이나 유료 플랜의 영구 디스크(Persistent Disk) 연결이 필요합니다. 리포지토리에 포함된
`render.yaml`을 사용하면 Blueprint 배포로 같은 설정을 한 번에 적용할 수도 있습니다.

## 데이터 모델

`Site`(지사, 예상 인원 headcount 보유) ← `Signature`(서명 기록: 소속·입력 이름·서명 이미지·해시)
`EducationDocument`는 서명 대상 교육/공지 문서로 버전 관리가 가능합니다.

지사별 진척률은 `headcount`(예상 인원) 대비 수집된 서명 수로 계산합니다. 개인별 로스터와
1:1로 매칭하지 않으므로, 같은 사람이 중복 서명하거나 다른 지사 인원이 잘못 선택할 가능성은
운영 단계에서 별도로 점검이 필요합니다.

## 로드맵

1. ✅ 1단계: 교육 콘텐츠 + 공용 QR 서명 — 본 MVP
2. ✅ 2단계: 본사 대시보드 진척률 시각화 — 본 MVP
3. 🔜 3단계: 고객사 제출용 PDF 자동 생성 — 현재는 브라우저 인쇄로 대체, 서버 사이드 PDF 생성(예: WeasyPrint) 연동 예정
4. 🔜 4단계: 전국 확대, 필요 시 본인확인·중복 서명 방지 단계 재도입, 검증된 전자서명 API(모두싸인/카카오전자서명) 연동

## 보안 · 개인정보 주의사항

배송원 개인정보(이름, 서명 이미지)가 포함되므로, 운영 배포 전 반드시 아래를 점검하세요.

- DB 암호화(at-rest) 및 접근 통제
- 원청(예: CJ대한통운) 제출 시 개인정보 마스킹 범위
- 개인정보보호법상 수집·보관 근거 및 보관 기간

이 저장소는 데모/MVP 목적이며, 시드 스크립트가 생성하는 지사·인원 데이터는 모두 가상의 샘플 데이터입니다.
