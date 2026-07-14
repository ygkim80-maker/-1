import random
import string

from app import models
from app.database import Base, SessionLocal, engine

SITE_NAMES = [f"제니엘 {i}지사" for i in range(1, 14)]  # 13개소 (CJ대한통운 파일럿 가정)
TOTAL_DRIVERS = 356

SAMPLE_SURNAMES = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임"]
SAMPLE_GIVEN = ["민준", "서준", "도윤", "예준", "시우", "지호", "주원", "현우", "지훈", "성민"]

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
        db.flush()

        sites = []
        for name in SITE_NAMES:
            site = models.Site(name=name, region=name)
            db.add(site)
            sites.append(site)
        db.flush()

        base_per_site = TOTAL_DRIVERS // len(sites)
        remainder = TOTAL_DRIVERS % len(sites)

        rng = random.Random(42)
        driver_seq = 1
        for idx, site in enumerate(sites):
            count = base_per_site + (1 if idx < remainder else 0)
            for _ in range(count):
                name = rng.choice(SAMPLE_SURNAMES) + rng.choice(SAMPLE_GIVEN)
                employee_no = f"EMP{driver_seq:04d}"
                birthdate = "{:04d}{:02d}{:02d}".format(
                    rng.randint(1975, 2000), rng.randint(1, 12), rng.randint(1, 28)
                )
                phone = "010" + "".join(rng.choice(string.digits) for _ in range(8))

                driver = models.Driver(
                    site_id=site.id,
                    name=name,
                    employee_no=employee_no,
                    phone=phone,
                    birthdate=birthdate,
                )
                db.add(driver)
                db.flush()

                link = models.SigningLink(driver_id=driver.id, document_id=document.id)
                db.add(link)

                driver_seq += 1

        db.commit()
        print(f"시드 완료: 지사 {len(sites)}개, 배송원 {driver_seq - 1}명")

        sample_links = db.query(models.SigningLink).limit(3).all()
        print("\n샘플 서명 링크 (테스트용, 본인확인 정보 포함):")
        for link in sample_links:
            print(
                f"  http://localhost:8000/sign/{link.token}"
                f"  ({link.driver.name}, 사번 {link.driver.employee_no}, 생년월일 {link.driver.birthdate})"
            )
    finally:
        db.close()


if __name__ == "__main__":
    run()
