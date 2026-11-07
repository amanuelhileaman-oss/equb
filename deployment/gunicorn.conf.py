"""
Production Gunicorn configuration for Digital Equb Ethiopia.
"""
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 4
worker_connections = 1000
timeout = 60
keepalive = 5

# Logging
accesslog = "/home/amanuel/Equb/logs/gunicorn_access.log"
errorlog = "/home/amanuel/Equb/logs/gunicorn_error.log"
loglevel = "info"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
