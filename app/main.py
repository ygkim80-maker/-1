import base64
import binascii
import os
from datetime import datetime
from io import BytesIO

import qrcode
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
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


def _active_document(db: Session) -> models.EducationDocument:
    document = db.query(models.EducationDocument).order_by(models.EducationDocument.id.desc()).first()
    if not document:
        raise HTTPException(status_code=500, detail="등록된 교육 문서가 없습니다")
    return document


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    sites = db.query(models.Site).order_by(models.Site.id).all()
    site_rows = []
    total_headcount = 0
    total_signed = 0

    for site in sites:
        signatures = sorted(site.signatures, key=lambda s: s.signed_at, reverse=True)
        signed_count = len(signatures)
        total_headcount += site.headcount
        total_signed += signed_count
        rate = round(signed_count / site.headcount * 100, 1) if site.headcount else 0.0
        site_rows.append(
            {
                "site": site,
                "headcount": site.headcount,
                "signed": signed_count,
                "rate": rate,
                "signatures": signatures,
            }
        )

    overall_rate = round(total_signed / total_headcount * 100, 1) if total_headcount else 0.0

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "site_rows": site_rows,
            "total_headcount": total_headcount,
            "total_signed": total_signed,
            "overall_rate": overall_rate,
        },
    )


@app.get("/api/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    total_headcount = db.query(func.coalesce(func.sum(models.Site.headcount), 0)).scalar() or 0
    total_signed = db.query(func.count(models.Signature.id)).scalar() or 0
    return {
        "total_headcount": total_headcount,
        "total_signed": total_signed,
        "rate": round(total_signed / total_headcount * 100, 1) if total_headcount else 0.0,
    }


@app.get("/sign", response_class=HTMLResponse)
def sign_page(request: Request, db: Session = Depends(get_db)):
    document = _active_document(db)
    sites = db.query(models.Site).order_by(models.Site.id).all()
    return templates.TemplateResponse(
        "sign.html", {"request": request, "document": document, "sites": sites}
    )


@app.get("/qr.png", include_in_schema=False)
def master_qr(request: Request):
    sign_url = str(request.base_url).rstrip("/") + "/sign"
    img = qrcode.make(sign_url, border=2)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@app.get("/qr", response_class=HTMLResponse)
def qr_page(request: Request, db: Session = Depends(get_db)):
    document = _active_document(db)
    sign_url = str(request.base_url).rstrip("/") + "/sign"
    return templates.TemplateResponse(
        "qr_page.html",
        {"request": request, "sign_url": sign_url, "document_title": document.title},
    )


@app.post("/sign/submit")
def submit_signature(
    request: Request,
    name: str = Form(...),
    site_id: int = Form(...),
    agree: str = Form(...),
    signature_image: str = Form(...),
    db: Session = Depends(get_db),
):
    document = _active_document(db)
    site = db.get(models.Site, site_id)
    if not site:
        raise HTTPException(status_code=400, detail="소속 지사를 선택해 주세요")
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

    signed_at = datetime.utcnow()
    content_hash = sha256_hex(
        document.content.encode("utf-8"),
        image_bytes,
        name.encode("utf-8"),
        site.name.encode("utf-8"),
        signed_at.isoformat().encode("utf-8"),
    )

    signature = models.Signature(
        document_id=document.id,
        site_id=site.id,
        entered_name=name,
        signed_at=signed_at,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "")[:255],
        content_hash=content_hash,
    )
    db.add(signature)
    db.flush()

    image_path = os.path.join(SIGNATURES_DIR, f"{signature.id}.png")
    with open(image_path, "wb") as f:
        f.write(image_bytes)
    signature.signature_image_path = f"/static/signatures/{signature.id}.png"

    db.commit()

    return {"ok": True, "redirect": f"/certificate/{signature.id}"}


@app.get("/certificate/{signature_id}", response_class=HTMLResponse)
def certificate(signature_id: int, request: Request, db: Session = Depends(get_db)):
    signature = db.get(models.Signature, signature_id)
    if not signature:
        raise HTTPException(status_code=404, detail="서명 기록을 찾을 수 없습니다")
    return templates.TemplateResponse(
        "certificate.html", {"request": request, "signature": signature}
    )
