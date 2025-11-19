"""
PDF Extraction API Module

Author: AI Assistant
Date: 2025-11-18
"""

from api.pdf.routes import router as pdf_router
from api.pdf.pdf_routes import router as pdf_process_router

__all__ = ["pdf_router", "pdf_process_router"]
