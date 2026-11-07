import datetime
import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SupportLog
from app.schemas import ContactCreate, ContactResponse

router = APIRouter(prefix="/api/v1/contact", tags=["Contact"])

@router.post("", response_model=ContactResponse)
def submit_contact_inquiry(req: ContactCreate, db: Session = Depends(get_db)):
    # Basic server validation
    clean_name = req.name.strip()
    clean_mobile = req.mobile.strip()
    clean_msg = req.message.strip()

    if len(clean_name) < 2:
        raise HTTPException(status_code=400, detail="कृपया आपले पूर्ण नाव प्रविष्ट करा.")

    digits_only = "".join([c for c in clean_mobile if c.isdigit()])
    if len(digits_only) < 10:
        raise HTTPException(status_code=400, detail="कृपया वैध १० अंकी मोबाईल नंबर प्रविष्ट करा.")

    if len(clean_msg) < 5:
        raise HTTPException(status_code=400, detail="संदेश किमान ५ अक्षरांचा असावा.")

    import uuid
    # Generate unique ticket number
    ticket_num = f"SK-TKT-{datetime.datetime.utcnow().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    inquiry = SupportLog(
        ticket_number=ticket_num,
        name=clean_name,
        mobile=clean_mobile,
        category=req.category,
        message=clean_msg,
        status="open",
        created_at=datetime.datetime.utcnow()
    )
    db.add(inquiry)
    db.commit()

    return ContactResponse(
        success=True,
        ticket_number=ticket_num,
        message_mr=f"आपली तक्रार/चौकशी यशस्वीरित्या नोंदवली आहे. तिकीट क्र: {ticket_num}. आमचा प्रतिनिधी २४ तासांत संपर्क करेल."
    )
