from app import models
from app.database import Base, SessionLocal, engine

SITE_NAMES = [f"제니엘 {i}지사" for i in range(1, 14)]  # 13개소 (CJ대한통운 파일럿 가정)
TOTAL_HEADCOUNT = 356

DOCUMENT_CONTENT = """
[배송 안전 및 서비스 품질 교육 확인서]

1. 본 교육은 카드배송 업무 수행에 필요한 안전수칙 및 고객응대 매뉴얼을 포함합니다.
2. 서명자는 아래 내용을 숙지하였음을 확인합니다.
   - 개인정보가 포함된 우편물의 취급 및 보관 절차
   - 수령인 본인확인 절차 준수
   - 배송 완료 후 서명/사진 증빙 절차
   - 안전운전 및 사고 예방 수칙
3. 본 서명은 전자적으로 기록되며, 서명 시각/IP/문서 해시가 함께 저장되어
   위변조 확인 및 대외 제출용 증빙 자료로 활용됩니다.
""".strip()


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.Site).count() > 0:
            print("이미 시드 데이터가 존재합니다. 초기화를 건너뜁니다.")
            return

        document = models.EducationDocument(
            title="배송 안전 및 서비스 품질 교육 확인서",
            version="1.0",
            content=DOCUMENT_CONTENT,
        )
        db.add(document)

        base_per_site = TOTAL_HEADCOUNT // len(SITE_NAMES)
        remainder = TOTAL_HEADCOUNT % len(SITE_NAMES)
        for idx, name in enumerate(SITE_NAMES):
            headcount = base_per_site + (1 if idx < remainder else 0)
            db.add(models.Site(name=name, headcount=headcount))

        db.commit()
        print(f"시드 완료: 지사 {len(SITE_NAMES)}개, 예상 인원 합계 {TOTAL_HEADCOUNT}명")
        print("\n서명 QR/링크(공용, 전 지사 동일):")
        print("  http://localhost:8000/sign")
        print("  http://localhost:8000/qr  (QR 코드 인쇄용 페이지)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
