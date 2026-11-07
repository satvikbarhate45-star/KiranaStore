"""
KiranaStore Production Django Views
Serves all Kirana Store UI pages and routes API endpoints synchronously.
"""
import time
import json
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

def safe_healthcheck(request):
    """
    Zero-DB, zero-allocation instant healthcheck for Render probes.
    """
    return HttpResponse("KiranaStore Production OK", content_type="text/plain; charset=utf-8", status=200)

def home_view(request):
    if request.method == "HEAD":
        return safe_healthcheck(request)
    return render(request, "index.html", {
        "active_page": "home",
        "title": "स्मार्ट किराणा - मुख्यपृष्ठ | बिलिंग व यादी शुद्धीकरण",
        "time": int(time.time())
    })

def catalog_view(request):
    if request.method == "HEAD":
        return safe_healthcheck(request)
    return render(request, "catalog.html", {
        "active_page": "catalog",
        "title": "स्मार्ट किराणा - पॉईंट-अँड-क्लिक व्हिज्युअल किराणा कॅटलॉग",
        "time": int(time.time())
    })

def history_view(request):
    if request.method == "HEAD":
        return safe_healthcheck(request)
    return render(request, "history.html", {
        "active_page": "history",
        "title": "स्मार्ट किराणा - खरेदी इतिहास | मागील पावत्या व हिशोब",
        "time": int(time.time())
    })

def analyzer_view(request):
    if request.method == "HEAD":
        return safe_healthcheck(request)
    return render(request, "analyzer.html", {
        "active_page": "analyzer",
        "title": "स्मार्ट किराणा - दर विश्लेषक व बजेट सिम्युलेटर",
        "time": int(time.time())
    })

def about_view(request):
    if request.method == "HEAD":
        return safe_healthcheck(request)
    return render(request, "about.html", {
        "active_page": "about",
        "title": "स्मार्ट किराणा - आमच्याबद्दल",
        "time": int(time.time())
    })

def contact_view(request):
    if request.method == "HEAD":
        return safe_healthcheck(request)
    return render(request, "contact.html", {
        "active_page": "contact",
        "title": "स्मार्ट किराणा - संपर्क व मदत",
        "time": int(time.time())
    })

# In-thread synchronous API dispatcher (Zero thread deadlock, zero background loops)
_test_client = None

def get_test_client():
    global _test_client
    if _test_client is None:
        from starlette.testclient import TestClient
        from app.main import app
        _test_client = TestClient(app, raise_server_exceptions=False)
    return _test_client

@csrf_exempt
def api_dispatcher(request, path=""):
    full_path = f"/api/{path}"
    if request.META.get("QUERY_STRING"):
        full_path += f"?{request.META['QUERY_STRING']}"

    client = get_test_client()
    method = request.method.upper()

    headers = {}
    for k, v in request.META.items():
        if k.startswith("HTTP_"):
            header_name = k[5:].replace("_", "-").lower()
            headers[header_name] = str(v)
        elif k in ("CONTENT_TYPE", "CONTENT_LENGTH") and v:
            headers[k.replace("_", "-").lower()] = str(v)

    files = {}
    data = {}
    body = None

    content_type_header = request.META.get("CONTENT_TYPE", "").lower()
    if "multipart/form-data" in content_type_header or len(request.FILES) > 0:
        for fname, fobj in request.FILES.items():
            files[fname] = (fobj.name, fobj.read(), fobj.content_type)
        for k, v in request.POST.items():
            data[k] = v
        # Remove Content-Type and Content-Length so TestClient generates correct multipart boundary
        headers.pop("content-type", None)
        headers.pop("content-length", None)
    else:
        try:
            body = request.body if method in ("POST", "PUT", "PATCH") else None
        except Exception:
            body = None

    try:
        response = client.request(
            method=method,
            url=full_path,
            headers=headers,
            content=body if not files else None,
            files=files if files else None,
            data=data if data else None
        )
        content_type = response.headers.get("content-type", "application/json")
        return HttpResponse(
            content=response.content,
            status=response.status_code,
            content_type=content_type
        )
    except Exception as exc:
        return JsonResponse({
            "success": False,
            "error": "API Dispatch Error",
            "detail": str(exc)
        }, status=500)

