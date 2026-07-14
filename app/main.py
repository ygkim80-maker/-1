import base64
import binascii
import os
from datetime import datetime

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models
from .database import Base, engine, get_db
from .utils import sha256_hex

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SIGNATURES_DIR = os.path.join(BASE_DIR, "static", "signatures")
os.makedirs(SIGNATURES_DIR, exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="배송 서명 플랫폼 MVP")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/dashboard")


def _driver_status(db: Session, driver: models.Driver):
    link = (
        db.query(models.SigningLink)
        .filter(models.SigningLink.driver_id == driver.id)
        .order_by(models.SigningLink.id.desc())
        .first()
    )
    signed = bool(link and link.signature)
    return link, signed


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    sites = db.query(models.Site).order_by(models.Site.id).all()
    site_rows = []
    total_drivers = 0
    total_signed = 0

    for site in sites:
        drivers = site.drivers
        signed_count = 0
        driver_rows = []
        for driver in drivers:
            link, signed = _driver_status(db, driver)
            if signed:
                signed_count += 1
            driver_rows.append(
                {
                    "driver": driver,
                    "signed": signed,
                    "signed_at": link.signature.signed_at if signed else None,
                    "token": link.token if link else None,
                    "link_id": link.id if link else None,
                }
            )
        total_drivers += len(drivers)
        total_signed += signed_count
        rate = round(signed_count / len(drivers) * 100, 1) if drivers else 0.0
        site_rows.append(
            {
                "site": site,
                "total": len(drivers),
                "signed": signed_count,
                "rate": rate,
                "drivers": driver_rows,
            }
        )

    overall_rate = round(total_signed / total_drivers * 100, 1) if total_drivers else 0.0

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "site_rows": site_rows,
            "total_drivers": total_drivers,
            "total_signed": total_signed,
            "overall_rate": overall_rate,
        },
    )


@app.get("/api/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    total_drivers = db.query(func.count(models.Driver.id)).scalar() or 0
    total_signed = db.query(func.count(models.Signature.id)).scalar() or 0
    return {
        "total_drivers": total_drivers,
        "total_signed": total_signed,
        "rate": round(total_signed / total_drivers * 100, 1) if total_drivers else 0.0,
    }


@app.post("/api/remind/{driver_id}")
def remind(driver_id: int, db: Session = Depends(get_db)):
    driver = db.get(models.Driver, driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="배송원을 찾을 수 없습니다")
    # TODO: 카카오 알림톡 API 연동. 본 MVP는 발송 없이 큐잉만 흉내내는 stub입니다.
    return {"status": "queued", "channel": "kakao_alimtalk(stub)", "driver": driver.name}


@app.get("/sign/{token}", response_class=HTMLResponse)
def sign_page(token: str, request: Request, db: Session = Depends(get_db)):
    link = db.query(models.SigningLink).filter(models.SigningLink.token == token).first()
    if not link:
        raise HTTPException(status_code=404, detail="유효하지 않은 링크입니다")
    if link.signature:
        return templates.TemplateResponse("signed.html", {"request": request, "link": link})
    return templates.TemplateResponse(
        "sign.html",
        {
            "request": request,
            "token": token,
            "document": link.document,
            "suggested_name": link.driver.name,
        },
    )


@app.post("/sign/{token}/submit")
def submit_signature(
    token: str,
    request: Request,
    name: str = Form(...),
    agree: str = Form(...),
    signature_image: str = Form(...),
    db: Session = Depends(get_db),
):
    link = db.query(models.SigningLink).filter(models.SigningLink.token == token).first()
    if not link:
        raise HTTPException(status_code=404, detail="유효하지 않은 링크입니다")
    if link.signature:
        raise HTTPException(status_code=409, detail="이미 서명이 완료되었습니다")
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="이름을 입력해 주세요")
    if agree not in ("on", "true", "1"):
        raise HTTPException(status_code=400, detail="교육 내용 동의가 필요합니다")

    try:
        _, encoded = signature_image.split(",", 1)
        image_bytes = base64.b64decode(encoded)
    except (ValueError, binascii.Error):
        raise HTTPException(status_code=400, detail="서명 이미지 형식이 올바르지 않습니다")

    if len(image_bytes) < 100:
        raise HTTPException(status_code=400, detail="서명이 비어 있습니다")

    image_path = os.path.join(SIGNATURES_DIR, f"{link.id}.png")
    with open(image_path, "wb") as f:
        f.write(image_bytes)

    signed_at = datetime.utcnow()
    content_hash = sha256_hex(
        link.document.content.encode("utf-8"),
        image_bytes,
        name.encode("utf-8"),
        signed_at.isoformat().encode("utf-8"),
    )

    signature = models.Signature(
        signing_link_id=link.id,
        entered_name=name,
        signed_at=signed_at,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "")[:255],
        verify_method="self_reported_name",
        signature_image_path=f"/static/signatures/{link.id}.png",
        content_hash=content_hash,
    )
    db.add(signature)
    db.commit()

    return {"ok": True, "redirect": f"/certificate/{link.id}"}


@app.get("/certificate/{link_id}", response_class=HTMLResponse)
def certificate(link_id: int, request: Request, db: Session = Depends(get_db)):
    link = db.get(models.SigningLink, link_id)
    if not link or not link.signature:
        raise HTTPException(status_code=404, detail="서명 기록을 찾을 수 없습니다")
    return templates.TemplateResponse(
        "certificate.html", {"request": request, "link": link, "signature": link.signature}
    )
