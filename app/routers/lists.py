import time
import uuid
import re
import sys
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import ProductCatalog, AIPartseAudit, VolatilityConfig, DraftGroceryList, SavedGroceryList
from app.schemas import (
    ParseListRequest,
    ParseListResponse,
    ParsedItem,
    UnresolvedLine,
    PipelineMetadata,
    DraftListCreate,
    DraftListResponse,
    SavedListCreate,
    SavedListResponse
)
from app.services.regex_parser import (
    extract_tokens_from_line,
    normalize_text,
    normalize_unit_and_quantity,
    parse_quantity_and_units
)
from app.services.gemini_service import (
    retrieve_line_candidates,
    call_gemini_api,
    call_gemini_api_chunked,
    validate_ai_response,
    match_catalog_item,
    circuit_breaker,
    get_last_diagnostic_metadata,
    split_raw_grocery_text,
    run_symbiotic_pipeline
)
from app.services.volatility_engine import (
    get_rolling_median_baseline,
    get_display_unit
)

router = APIRouter(prefix="/api/v1/lists", tags=["Lists"])

@router.post("/parse", response_model=ParseListResponse)
def parse_grocery_list(req: ParseListRequest, db: Session = Depends(get_db)):
    start_time = time.time()
    session_id = req.session_id or str(uuid.uuid4())

    # Intelligent Text Normalization & Pre-splitting
    if req.raw_items and isinstance(req.raw_items, list) and len(req.raw_items) > 0:
        raw_lines = [l.strip() for l in req.raw_items if l and l.strip()]
    else:
        raw_lines = split_raw_grocery_text(req.raw_text or "")

    if not raw_lines:
        raise HTTPException(status_code=400, detail="कृपया किराणा यादी सबमिट करा (यादी रिकामी आहे).")

    if len(raw_lines) > 500:
        raise HTTPException(status_code=400, detail="एका वेळी जास्तीत जास्त ५०० वस्तू सबमिट करता येतील.")

    # Check candidates for each line
    candidates_per_line = [retrieve_line_candidates(db, line, k=8) for line in raw_lines]

    # Two-Way Symbiotic Hybrid Engine (Local Regex Pre-parser + Gemini AI Co-processing)
    pipeline_result = run_symbiotic_pipeline(
        raw_lines=raw_lines,
        candidates_per_line=candidates_per_line,
        db=db,
        mode=req.mode or "auto"
    )

    parsed_items = pipeline_result["items"]
    unresolved = pipeline_result["unresolved"]
    merged_notifications = pipeline_result["merged_duplicates"]
    pipeline_source = pipeline_result["pipeline_source"]
    degraded = pipeline_result["degraded"]
    degrade_reason = pipeline_result["degrade_reason"]
    ai_fallback = pipeline_result["ai_fallback"]
    latency_ms = pipeline_result["latency_ms"]

    # Log audit entry
    try:
        audit_record = AIPartseAudit(
            session_id=session_id,
            model=pipeline_result["model"],
            prompt_version="symbiotic-1.2.0",
            latency_ms=latency_ms,
            outcome="ok" if not degraded else "degraded",
            degrade_reason=degrade_reason,
            lines_in=len(raw_lines),
            items_out=len(parsed_items),
            validator_fails={}
        )
        db.add(audit_record)
        db.commit()
    except Exception:
        db.rollback()

    ai_active = bool(pipeline_source == "gemini" and not ai_fallback)
    fallback_notice = None if ai_active else ("स्मार्ट सुधारणा उपलब्ध नाही, साधा पार्सर वापरला आहे." if ai_fallback else None)

    return ParseListResponse(
        session_id=session_id,
        pipeline=PipelineMetadata(
            source=pipeline_source,
            model=pipeline_result["model"],
            prompt_version="symbiotic-1.2.0",
            latency_ms=latency_ms,
            degraded=degraded,
            degrade_reason=degrade_reason,
            ai_fallback=ai_fallback,
            ai_active=ai_active
        ),
        items=parsed_items,
        unresolved=unresolved,
        merged_duplicates=merged_notifications,
        fallback_notice_mr=fallback_notice,
        ai_fallback=ai_fallback,
        ai_active=ai_active
    )


# ==============================================================================
# MODULE 2: OFFLINE DRAFT PERSISTENCE & QUICK RESTORE API
# ==============================================================================

@router.post("/drafts", response_model=DraftListResponse)
def save_draft_list(req: DraftListCreate, db: Session = Depends(get_db)):
    """
    Saves a verified grocery list draft to PostgreSQL/SQLite draft_grocery_lists table.
    Enables mobile offline/online list creation and shop counter restore.
    """
    sess_id = req.session_id or str(uuid.uuid4())
    total_items = len(req.items)
    
    # Check if a draft with this session_id already exists to update it
    existing = db.query(DraftGroceryList).filter(DraftGroceryList.session_id == sess_id).first()
    if existing:
        existing.title = req.title or existing.title
        existing.raw_text = req.raw_text
        existing.items_json = req.items
        existing.total_items = total_items
        existing.updated_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        db.commit()
        db.refresh(existing)
        return DraftListResponse(
            draft_id=existing.draft_id,
            session_id=existing.session_id,
            buyer_id=existing.buyer_id,
            title=existing.title,
            raw_text=existing.raw_text,
            total_items=existing.total_items,
            items=existing.items_json,
            created_at=existing.created_at.strftime("%d-%m-%Y %I:%M %p") if isinstance(existing.created_at, datetime.date) else str(existing.created_at),
            updated_at=existing.updated_at.strftime("%d-%m-%Y %I:%M %p") if isinstance(existing.updated_at, datetime.date) else str(existing.updated_at)
        )

    new_draft = DraftGroceryList(
        session_id=sess_id,
        buyer_id=settings.DEFAULT_BUYER_ID,
        title=req.title or "किराणा यादी ड्राफ्ट",
        raw_text=req.raw_text,
        items_json=req.items,
        total_items=total_items
    )
    db.add(new_draft)
    db.commit()
    db.refresh(new_draft)

    created_str = new_draft.created_at.strftime("%d-%m-%Y %I:%M %p") if hasattr(new_draft.created_at, "strftime") else str(new_draft.created_at)
    updated_str = new_draft.updated_at.strftime("%d-%m-%Y %I:%M %p") if hasattr(new_draft.updated_at, "strftime") else str(new_draft.updated_at)

    return DraftListResponse(
        draft_id=new_draft.draft_id,
        session_id=new_draft.session_id,
        buyer_id=new_draft.buyer_id,
        title=new_draft.title,
        raw_text=new_draft.raw_text,
        total_items=new_draft.total_items,
        items=new_draft.items_json,
        created_at=created_str,
        updated_at=updated_str
    )

@router.get("/drafts", response_model=List[DraftListResponse])
def get_draft_lists(db: Session = Depends(get_db)):
    """Lists all saved drafts ordered by latest updated."""
    drafts = db.query(DraftGroceryList).order_by(DraftGroceryList.updated_at.desc()).all()
    results = []
    for d in drafts:
        c_str = d.created_at.strftime("%d-%m-%Y %I:%M %p") if hasattr(d.created_at, "strftime") else str(d.created_at)
        u_str = d.updated_at.strftime("%d-%m-%Y %I:%M %p") if hasattr(d.updated_at, "strftime") else str(d.updated_at)
        results.append(DraftListResponse(
            draft_id=d.draft_id,
            session_id=d.session_id,
            buyer_id=d.buyer_id,
            title=d.title,
            raw_text=d.raw_text,
            total_items=d.total_items,
            items=d.items_json,
            created_at=c_str,
            updated_at=u_str
        ))
    return results

@router.get("/drafts/{draft_id}", response_model=DraftListResponse)
def get_single_draft(draft_id: int, db: Session = Depends(get_db)):
    """Retrieves a specific draft list with items."""
    draft = db.query(DraftGroceryList).filter(DraftGroceryList.draft_id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="ड्राफ्ट यादी सापडली नाही.")
    c_str = draft.created_at.strftime("%d-%m-%Y %I:%M %p") if hasattr(draft.created_at, "strftime") else str(draft.created_at)
    u_str = draft.updated_at.strftime("%d-%m-%Y %I:%M %p") if hasattr(draft.updated_at, "strftime") else str(draft.updated_at)
    return DraftListResponse(
        draft_id=draft.draft_id,
        session_id=draft.session_id,
        buyer_id=draft.buyer_id,
        title=draft.title,
        raw_text=draft.raw_text,
        total_items=draft.total_items,
        items=draft.items_json,
        created_at=c_str,
        updated_at=u_str
    )

@router.delete("/drafts/{draft_id}")
def delete_draft(draft_id: int, db: Session = Depends(get_db)):
    """Deletes a draft list."""
    draft = db.query(DraftGroceryList).filter(DraftGroceryList.draft_id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="ड्राफ्ट यादी सापडली नाही.")
    db.delete(draft)
    db.commit()
    return {"success": True, "message_mr": "ड्राफ्ट यादी यशस्वीरीत्या हटवली आहे."}


# ==============================================================================
# MODULE 5: PERSISTENT "सेव्ह केलेल्या याद्या" (SAVED LISTS) API
# ==============================================================================

@router.post("/saved", response_model=SavedListResponse)
def create_saved_grocery_list(req: SavedListCreate, db: Session = Depends(get_db)):
    """
    Persists confirmed grocery list to PostgreSQL/SQLite saved_grocery_lists table.
    Enables persistent 1-click loading onto the Reverse POS billing counter.
    """
    total_items = req.total_items if req.total_items and req.total_items > 0 else len(req.items)
    
    # Calculate estimated budget if not provided
    est_budget = req.estimated_budget or 0.0
    if est_budget <= 0.0 and req.items:
        for it in req.items:
            q = float(it.get("quantity") or it.get("qty") or 1.0)
            p = float(it.get("estimated_price") or it.get("target_price") or it.get("rate") or 0.0)
            est_budget += round(q * p, 2)

    new_saved = SavedGroceryList(
        list_name=req.list_name or "माझी किराणा यादी",
        total_items=total_items,
        estimated_budget=round(est_budget, 2),
        items_payload=req.items
    )
    db.add(new_saved)
    db.commit()
    db.refresh(new_saved)

    c_str = new_saved.created_at.strftime("%d-%m-%Y %I:%M %p") if hasattr(new_saved.created_at, "strftime") else str(new_saved.created_at)

    return SavedListResponse(
        id=new_saved.id,
        list_name=new_saved.list_name,
        created_at=c_str,
        total_items=new_saved.total_items,
        estimated_budget=new_saved.estimated_budget,
        items=new_saved.items_payload
    )

@router.get("/saved", response_model=List[SavedListResponse])
def get_all_saved_grocery_lists(db: Session = Depends(get_db)):
    """
    Retrieves all persistent saved grocery lists ordered by creation date desc.
    """
    lists = db.query(SavedGroceryList).order_by(SavedGroceryList.created_at.desc()).all()
    results = []
    for l in lists:
        c_str = l.created_at.strftime("%d-%m-%Y %I:%M %p") if hasattr(l.created_at, "strftime") else str(l.created_at)
        results.append(SavedListResponse(
            id=l.id,
            list_name=l.list_name,
            created_at=c_str,
            total_items=l.total_items,
            estimated_budget=l.estimated_budget or 0.0,
            items=l.items_payload
        ))
    return results

@router.get("/saved/{saved_id}", response_model=SavedListResponse)
def get_saved_grocery_list(saved_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a single saved list with all line items.
    """
    saved_list = db.query(SavedGroceryList).filter(SavedGroceryList.id == saved_id).first()
    if not saved_list:
        raise HTTPException(status_code=404, detail="सेव्ह केलेली यादी सापडली नाही.")
    c_str = saved_list.created_at.strftime("%d-%m-%Y %I:%M %p") if hasattr(saved_list.created_at, "strftime") else str(saved_list.created_at)
    return SavedListResponse(
        id=saved_list.id,
        list_name=saved_list.list_name,
        created_at=c_str,
        total_items=saved_list.total_items,
        estimated_budget=saved_list.estimated_budget or 0.0,
        items=saved_list.items_payload
    )

@router.delete("/saved/{saved_id}")
def delete_saved_grocery_list(saved_id: int, db: Session = Depends(get_db)):
    """
    Deletes a persistent saved grocery list.
    """
    saved_list = db.query(SavedGroceryList).filter(SavedGroceryList.id == saved_id).first()
    if not saved_list:
        raise HTTPException(status_code=404, detail="सेव्ह केलेली यादी सापडली नाही.")
    db.delete(saved_list)
    db.commit()
    return {"success": True, "message_mr": "यादी यशस्वीरीत्या हटवली आहे."}


