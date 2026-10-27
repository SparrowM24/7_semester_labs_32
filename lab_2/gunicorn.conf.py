import os

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
workers = 1
loglevel = os.getenv("LOG_LEVEL", "INFO").lower()
accesslog = "-"
errorlog = "-"
control_socket_disable = True