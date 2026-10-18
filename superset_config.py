SECRET_KEY = "doi-chuoi-nay-thanh-mot-chuoi-ngau-nhien-dai-32-ky-tu-tro-len"

# Mac dinh Superset chan ket noi SQLite; tat de co the dung file db.sqlite3
PREVENT_UNSAFE_DB_CONNECTIONS = False

# ==========================================
# Cấu hình MCP (Model Context Protocol) Service
# ==========================================
MCP_DEV_USERNAME = "admin"  # User admin đã có trong metadata db
MCP_RBAC_ENABLED = True     # Giữ nguyên RBAC an toàn
SUPERSET_WEBSERVER_ADDRESS = "http://127.0.0.1:8088"
WEBDRIVER_BASEURL = "http://127.0.0.1:8088/"

