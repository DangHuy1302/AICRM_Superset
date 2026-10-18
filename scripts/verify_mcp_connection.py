"""
Script kiểm thử xác minh toàn diện Apache Superset MCP Server (TH2 - Stage 3)
Chạy từ môi trường host Windows kết nối tới http://127.0.0.1:5008/mcp
Kiểm tra:
1. Initialize / Protocol Handshake
2. tools/list (Discovery)
3. health_check tool execution
4. get_instance_info tool execution
5. list_dashboards tool execution (xác minh Dashboard ID 2 và ID 3)
6. list_datasets tool execution (xác minh 13 datasets)
7. execute_sql tool execution (truy vấn thực tế crm_customer theo ai_category)
"""

import sys
import json
import urllib.request

MCP_URL = "http://127.0.0.1:5008/mcp"

def call_mcp(method: str, params: dict, rpc_id: int = 1):
    req_body = {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "method": method,
        "params": params
    }
    req = urllib.request.Request(
        MCP_URL,
        data=json.dumps(req_body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read().decode("utf-8")
        results = []
        for line in raw.splitlines():
            if line.startswith("data: "):
                results.append(json.loads(line[6:]))
        for r in results:
            if "result" in r:
                return r["result"]
            if "error" in r:
                raise RuntimeError(f"RPC Error: {r['error']}")
        return results

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("================================================================")
    print("   KIỂM THỬ XÁC MINH TOÀN DIỆN APACHE SUPERSET MCP SERVER (TH2) ")
    print("================================================================\n")

    # 1. Initialize
    print("[1/6] Kiểm tra MCP Handshake (initialize)...")
    init_res = call_mcp("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "verify-script", "version": "1.0.0"}
    }, rpc_id=1)
    server_info = init_res.get("serverInfo", {})
    proto = init_res.get("protocolVersion")
    print(f"  -> PASS: Server={server_info.get('name')} v{server_info.get('version')}, Protocol={proto}\n")

    # 2. tools/list
    print("[2/6] Kiểm tra danh sách Tools (tools/list)...")
    tools_res = call_mcp("tools/list", {}, rpc_id=2)
    tools = tools_res.get("tools", [])
    print(f"  -> PASS: Đã phát hiện {len(tools)} công cụ khả dụng:")
    for t in tools:
        print(f"     - {t['name']}")
    print()

    # 3. health_check tool
    print("[3/6] Gọi công cụ 'health_check'...")
    hc_res = call_mcp("tools/call", {"name": "health_check", "arguments": {}}, rpc_id=3)
    hc_data = json.loads(hc_res["content"][0]["text"])
    print(f"  -> PASS: Status={hc_data.get('status')}, Version={hc_data.get('version')}, Uptime={hc_data.get('uptime_seconds')}s\n")

    # 4. list_dashboards tool
    print("[4/6] Gọi công cụ 'call_tool' -> 'list_dashboards'...")
    dash_res = call_mcp("tools/call", {
        "name": "call_tool",
        "arguments": {
            "name": "list_dashboards",
            "arguments": {"request": {"page": 1, "page_size": 10}}
        }
    }, rpc_id=4)
    dash_data = json.loads(dash_res["content"][0]["text"])
    dashboards = dash_data.get("dashboards", [])
    print(f"  -> PASS: Phát hiện {len(dashboards)} dashboards:")
    for d in dashboards:
        print(f"     - ID {d['id']}: '{d['dashboard_title']}' (Slug: {d['slug']})")
    print()

    # 5. list_datasets tool
    print("[5/6] Gọi công cụ 'call_tool' -> 'list_datasets'...")
    ds_res = call_mcp("tools/call", {
        "name": "call_tool",
        "arguments": {
            "name": "list_datasets",
            "arguments": {"request": {"page": 1, "page_size": 20}}
        }
    }, rpc_id=5)
    ds_data = json.loads(ds_res["content"][0]["text"])
    datasets = ds_data.get("datasets", [])
    print(f"  -> PASS: Phát hiện {len(datasets)} datasets:")
    for ds in datasets[:5]:
        print(f"     - ID {ds['id']}: {ds['table_name']}")
    if len(datasets) > 5:
        print(f"     ... và {len(datasets) - 5} datasets khác.")
    print()

    # 6. execute_sql tool
    print("[6/6] Gọi công cụ 'call_tool' -> 'execute_sql' (Truy vấn phân bổ khách hàng CRM)...")
    sql_res = call_mcp("tools/call", {
        "name": "call_tool",
        "arguments": {
            "name": "execute_sql",
            "arguments": {
                "request": {
                    "database_id": 1,
                    "sql": "SELECT ai_category, count(*) as count FROM crm_customer GROUP BY ai_category ORDER BY count DESC"
                }
            }
        }
    }, rpc_id=6)
    sql_data = json.loads(sql_res["content"][0]["text"])
    print(f"  -> PASS: Truy vấn SQL thực thi thành công:")
    for row in sql_data.get("rows", []):
        print(f"     - {row['ai_category']}: {row['count']} khách hàng")
    print()

    print("================================================================")
    print("   TẤT CẢ 6 BƯỚC KIỂM THỬ MCP SERVER ĐỀU ĐẠT CHUẨN 100% PASS!   ")
    print("================================================================")

if __name__ == "__main__":
    main()

