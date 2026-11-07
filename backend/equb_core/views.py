from pathlib import Path
from django.conf import settings
from django.http import HttpResponse, Http404
from django.views.static import serve

FRONTEND_DIST_DIR = settings.BASE_DIR.parent / 'frontend' / 'dist'

def serve_spa(request, path=""):
    """
    Serves the compiled React Single Page Application (SPA) directly from Django,
    enabling seamless routing for both http://127.0.0.1:8000/ and frontend dev server.
    """
    # 1. If a specific resource is requested, check if it exists in frontend/dist (e.g. assets, favicon)
    if path:
        target_path = (FRONTEND_DIST_DIR / path).resolve()
        try:
            # Prevent directory traversal attacks
            target_path.relative_to(FRONTEND_DIST_DIR.resolve())
            if target_path.is_file():
                return serve(request, path, document_root=FRONTEND_DIST_DIR)
        except ValueError:
            pass

    # 2. Otherwise serve index.html for root path and client-side SPA routing
    index_file = FRONTEND_DIST_DIR / 'index.html'
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            return HttpResponse(f.read(), content_type='text/html')

    # Fallback if frontend is not built
    return HttpResponse(
        "<!DOCTYPE html><html><head><title>Digital Equb Ethiopia</title></head>"
        "<body style='font-family:system-ui,sans-serif;padding:3rem;text-align:center;background:#030712;color:#f9fafb;'>"
        "<h1 style='color:#10b981;'>Digital Equb Ethiopia (የኢትዮጵያ ዲጂታል ዕቁብ)</h1>"
        "<p>Frontend distribution bundle not found.</p>"
        "<p>Please build the frontend using <code>npm run build</code> in <code>frontend/</code> or visit the active Vite development server at "
        "<a href='http://127.0.0.1:5173' style='color:#f59e0b;font-weight:bold;'>http://127.0.0.1:5173</a>.</p>"
        "</body></html>",
        status=200
    )
