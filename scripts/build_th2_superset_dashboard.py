"""
Script tạo và cập nhật Dashboard TH2 trên Apache Superset 6.1.0:
'Northstar CRM Intelligence — Executive Overview'
Tự động cấu hình 16 biểu đồ, 4 hàng bố cục BI chuyên nghiệp,
các chỉ số KPI, lớp dữ liệu phân tích và liên kết an toàn không ghi đè dashboard cũ.
"""

import json
import uuid
from superset.app import create_app
from superset.extensions import db

app = create_app()

with app.app_context():
    from superset.models.core import Database
    from superset.connectors.sqla.models import SqlaTable, TableColumn, SqlMetric
    from superset.models.slice import Slice
    from superset.models.dashboard import Dashboard

    print("=== BẮT ĐẦU CẤU HÌNH TH2 SUPERSET DASHBOARD ===")
    
    # 1. Tìm Database kết nối
    crm_db = db.session.query(Database).filter_by(id=1).first()
    if not crm_db:
        raise RuntimeError("Không tìm thấy Database ID 1 (Wagtail ERP CRM) trong Superset!")
    print(f"- Đang sử dụng Database: {crm_db.database_name} ({crm_db.sqlalchemy_uri})")

    # 2. Đảm bảo các bảng vật lý và virtual dataset
    table_names = [
        'crm_customer', 'crm_lead', 'crm_opportunity', 'crm_interaction', 
        'crm_task', 'crm_supportticket', 'crm_product', 'crm_quote', 'crm_quoteitem'
    ]
    datasets = {}
    for t_name in table_names:
        tbl = db.session.query(SqlaTable).filter_by(database_id=crm_db.id, table_name=t_name).first()
        if not tbl:
            tbl = SqlaTable(table_name=t_name, database=crm_db)
            db.session.add(tbl)
            db.session.flush()
        tbl.fetch_metadata()
        datasets[t_name] = tbl

    # Virtual datasets
    virtual_sqls = {
        'view_customer_360_analytics': """WITH opp_stats AS (
    SELECT 
        customer_id,
        COUNT(id) AS total_opps,
        SUM(CASE WHEN stage = 'won' THEN amount ELSE 0 END) AS won_amount,
        SUM(CASE WHEN stage NOT IN ('won', 'lost') THEN amount ELSE 0 END) AS open_pipeline_amount,
        SUM(CASE WHEN stage NOT IN ('won', 'lost') THEN amount * probability / 100.0 ELSE 0 END) AS weighted_forecast_amount,
        SUM(CASE WHEN stage NOT IN ('won', 'lost') THEN 1 ELSE 0 END) AS open_opps_count,
        SUM(CASE WHEN stage = 'won' THEN 1 ELSE 0 END) AS won_opps_count
    FROM crm_opportunity
    GROUP BY customer_id
),
int_stats AS (
    SELECT 
        customer_id,
        COUNT(id) AS total_interactions,
        MAX(happened_at) AS last_interaction_at
    FROM crm_interaction
    GROUP BY customer_id
),
task_stats AS (
    SELECT 
        customer_id,
        SUM(CASE WHEN status != 'done' AND due_date < DATE('now') THEN 1 ELSE 0 END) AS overdue_tasks_count
    FROM crm_task
    WHERE customer_id IS NOT NULL
    GROUP BY customer_id
)
SELECT 
    c.id AS customer_id,
    c.name AS customer_name,
    c.company,
    c.source,
    c.status AS customer_status,
    c.ai_category,
    c.created_at AS customer_created_at,
    COALESCE(o.total_opps, 0) AS total_opps,
    COALESCE(o.won_amount, 0) AS won_amount,
    COALESCE(o.open_pipeline_amount, 0) AS open_pipeline_amount,
    COALESCE(o.weighted_forecast_amount, 0) AS weighted_forecast_amount,
    COALESCE(o.open_opps_count, 0) AS open_opps_count,
    COALESCE(o.won_opps_count, 0) AS won_opps_count,
    COALESCE(i.total_interactions, 0) AS total_interactions,
    i.last_interaction_at,
    COALESCE(t.overdue_tasks_count, 0) AS overdue_tasks_count
FROM crm_customer c
LEFT JOIN opp_stats o ON c.id = o.customer_id
LEFT JOIN int_stats i ON c.id = i.customer_id
LEFT JOIN task_stats t ON c.id = t.customer_id""",

        'view_monthly_sales_forecast': """SELECT 
    strftime('%Y-%m', expected_close_date) AS close_month,
    stage,
    COUNT(id) AS deal_count,
    SUM(amount) AS total_amount,
    SUM(amount * probability / 100.0) AS weighted_forecast
FROM crm_opportunity
WHERE stage NOT IN ('won', 'lost') AND expected_close_date IS NOT NULL
GROUP BY strftime('%Y-%m', expected_close_date), stage""",

        'view_support_sla': """SELECT 
    id AS ticket_id,
    title,
    category,
    priority,
    status,
    created_at,
    resolved_at,
    CASE 
        WHEN resolved_at IS NOT NULL 
        THEN ROUND((JULIANDAY(resolved_at) - JULIANDAY(created_at)) * 24, 1) 
        ELSE NULL 
    END AS resolution_hours
FROM crm_supportticket""",

        'view_lead_scoring_analytics': """SELECT 
    id AS lead_id,
    name AS lead_name,
    email,
    source,
    status,
    score,
    CASE 
        WHEN score >= 75 THEN 'Hot (>=75)'
        WHEN score >= 45 THEN 'Warm (45-74)'
        ELSE 'Cold (<45)'
    END AS score_tier,
    CASE
        WHEN status = 'converted' THEN 'Đã chuyển đổi'
        WHEN status = 'lost' THEN 'Không tiềm năng'
        ELSE 'Đang chăm sóc'
    END AS lead_lifecycle,
    need,
    created_at
FROM crm_lead"""
    }

    for v_name, sql in virtual_sqls.items():
        tbl = db.session.query(SqlaTable).filter_by(database_id=crm_db.id, table_name=v_name).first()
        if not tbl:
            tbl = SqlaTable(table_name=v_name, database=crm_db)
            db.session.add(tbl)
            db.session.flush()
        tbl.sql = sql
        tbl.fetch_metadata()
        datasets[v_name] = tbl

    # 3. Đăng ký các SqlMetric chuyên biệt trên từng Dataset
    def add_metric(dataset, name, verbose_name, expr, metric_type="count"):
        m = db.session.query(SqlMetric).filter_by(table_id=dataset.id, metric_name=name).first()
        if not m:
            m = SqlMetric(metric_name=name, table=dataset)
            db.session.add(m)
        m.verbose_name = verbose_name
        m.expression = expr
        m.metric_type = metric_type

    # Metrics cho crm_opportunity
    add_metric(datasets['crm_opportunity'], 'won_amount', 'Tổng giá trị Won (VNĐ)', "SUM(CASE WHEN stage = 'won' THEN amount ELSE 0 END)")
    add_metric(datasets['crm_opportunity'], 'open_pipeline_amount', 'Tổng Pipeline mở (VNĐ)', "SUM(CASE WHEN stage NOT IN ('won', 'lost') THEN amount ELSE 0 END)")
    add_metric(datasets['crm_opportunity'], 'weighted_forecast', 'Dự báo có trọng số (VNĐ)', "SUM(CASE WHEN stage NOT IN ('won', 'lost') THEN amount * probability / 100.0 ELSE 0 END)")
    add_metric(datasets['crm_opportunity'], 'total_amount', 'Tổng giá trị deal (VNĐ)', "SUM(amount)")

    # Metrics cho crm_customer
    add_metric(datasets['crm_customer'], 'high_potential_count', 'Số khách Tiềm năng cao', "SUM(CASE WHEN ai_category = 'Tiềm năng cao' THEN 1 ELSE 0 END)")
    add_metric(datasets['crm_customer'], 'high_potential_pct', 'Tỷ lệ Tiềm năng cao (%)', "ROUND(100.0 * SUM(CASE WHEN ai_category = 'Tiềm năng cao' THEN 1 ELSE 0 END) / COUNT(*), 1)")

    # Metrics cho crm_lead
    add_metric(datasets['crm_lead'], 'converted_rate', 'Tỷ lệ chuyển đổi (%)', "ROUND(100.0 * SUM(CASE WHEN status = 'converted' THEN 1 ELSE 0 END) / COUNT(*), 1)")

    # Metrics cho view_customer_360_analytics
    add_metric(datasets['view_customer_360_analytics'], 'sum_won_amount', 'Tổng doanh thu Won (VNĐ)', "SUM(won_amount)")
    add_metric(datasets['view_customer_360_analytics'], 'sum_open_pipeline', 'Tổng Pipeline mở (VNĐ)', "SUM(open_pipeline_amount)")
    add_metric(datasets['view_customer_360_analytics'], 'sum_weighted_forecast', 'Tổng Dự báo (VNĐ)', "SUM(weighted_forecast_amount)")

    # Metrics cho view_monthly_sales_forecast
    add_metric(datasets['view_monthly_sales_forecast'], 'sum_weighted_forecast', 'Dự báo có trọng số (VNĐ)', "SUM(weighted_forecast)")
    add_metric(datasets['view_monthly_sales_forecast'], 'sum_total_amount', 'Tổng giá trị Pipeline (VNĐ)', "SUM(total_amount)")

    # Metrics cho view_support_sla
    add_metric(datasets['view_support_sla'], 'avg_sla_hours', 'Giờ giải quyết TB (SLA)', "ROUND(AVG(resolution_hours), 1)")

    # Metrics cho view_lead_scoring_analytics
    add_metric(datasets['view_lead_scoring_analytics'], 'avg_lead_score', 'Điểm số Lead TB', "ROUND(AVG(score), 1)")
    add_metric(datasets['view_lead_scoring_analytics'], 'hot_lead_count', 'Số Lead Hot (>=75)', "SUM(CASE WHEN score >= 75 THEN 1 ELSE 0 END)")

    db.session.commit()
    print("- Đã cập nhật xong tất cả Datasets và Metrics chuẩn.")

    # 4. Tìm hoặc tạo Dashboard TH2 mới (giữ nguyên Dashboard cũ ID=2)
    DASHBOARD_TITLE = "Northstar CRM Intelligence — Executive Overview"
    dash = db.session.query(Dashboard).filter_by(dashboard_title=DASHBOARD_TITLE).first()
    if not dash:
        dash = Dashboard(dashboard_title=DASHBOARD_TITLE, slug="northstar-crm-executive-overview")
        db.session.add(dash)
        db.session.flush()
    print(f"- Dashboard TH2: ID = {dash.id}, Title = '{dash.dashboard_title}'")

    # 5. Hàm trợ giúp tạo hoặc cập nhật Slice (Chart)
    def upsert_slice(name, viz_type, dataset_name, params_dict):
        dataset = datasets[dataset_name]
        s = db.session.query(Slice).filter_by(slice_name=name).first()
        if not s:
            s = Slice(
                slice_name=name,
                datasource_type='table',
                datasource_id=dataset.id,
                viz_type=viz_type
            )
            db.session.add(s)
            db.session.flush()
        s.viz_type = viz_type
        s.datasource_id = dataset.id
        s.datasource_type = 'table'
        
        base_params = {
            "datasource": f"{dataset.id}__table",
            "viz_type": viz_type,
            "slice_id": s.id,
            "dashboards": [dash.id],
            "extra_form_data": {},
        }
        base_params.update(params_dict)
        s.params = json.dumps(base_params, ensure_ascii=False)
        return s

    charts = {}

    # === HÀNG 1: 6 KPI ĐIỀU HÀNH ===
    charts['kpi_total_customers'] = upsert_slice(
        name="[TH2] Tổng số khách hàng",
        viz_type="big_number_total",
        dataset_name="crm_customer",
        params_dict={
            "metric": "count",
            "subheader": "Hồ sơ đối tác đang quản lý",
            "y_axis_format": ",d",
            "header_font_size": 0.4,
            "subtitle_font_size": 0.15
        }
    )

    charts['kpi_total_leads'] = upsert_slice(
        name="[TH2] Tổng số Lead tiềm năng",
        viz_type="big_number_total",
        dataset_name="crm_lead",
        params_dict={
            "metric": "count",
            "subheader": "Đầu mối tiếp nhận từ các kênh",
            "y_axis_format": ",d",
            "header_font_size": 0.4,
            "subtitle_font_size": 0.15
        }
    )

    charts['kpi_open_pipeline'] = upsert_slice(
        name="[TH2] Tổng giá trị Pipeline đang mở",
        viz_type="big_number_total",
        dataset_name="crm_opportunity",
        params_dict={
            "metric": "open_pipeline_amount",
            "subheader": "VNĐ (Các deal đang theo đuổi)",
            "y_axis_format": "$,.0f",
            "header_font_size": 0.38,
            "subtitle_font_size": 0.15
        }
    )

    charts['kpi_weighted_forecast'] = upsert_slice(
        name="[TH2] Doanh thu kỳ vọng có trọng số",
        viz_type="big_number_total",
        dataset_name="crm_opportunity",
        params_dict={
            "metric": "weighted_forecast",
            "subheader": "VNĐ (Pipeline mở x Xác suất)",
            "y_axis_format": "$,.0f",
            "header_font_size": 0.38,
            "subtitle_font_size": 0.15
        }
    )

    charts['kpi_won_revenue'] = upsert_slice(
        name="[TH2] Tổng giá trị cơ hội Won",
        viz_type="big_number_total",
        dataset_name="crm_opportunity",
        params_dict={
            "metric": "won_amount",
            "subheader": "VNĐ (Doanh thu đã ký kết)",
            "y_axis_format": "$,.0f",
            "header_font_size": 0.38,
            "subtitle_font_size": 0.15
        }
    )

    charts['kpi_high_potential_pct'] = upsert_slice(
        name="[TH2] Tỷ lệ khách hàng Tiềm năng cao (AI)",
        viz_type="big_number_total",
        dataset_name="crm_customer",
        params_dict={
            "metric": "high_potential_pct",
            "subheader": "% do Gemini AI đánh giá",
            "y_axis_format": ".1f",
            "header_font_size": 0.4,
            "subtitle_font_size": 0.15
        }
    )

    # === HÀNG 2: AI CUSTOMER INTELLIGENCE ===
    charts['chart_ai_pie'] = upsert_slice(
        name="[TH2] Phân bổ khách hàng theo phân loại AI",
        viz_type="pie",
        dataset_name="crm_customer",
        params_dict={
            "groupby": ["ai_category"],
            "metric": "count",
            "show_legend": True,
            "donut": True,
            "labels_outside": True,
            "color_scheme": "supersetColors"
        }
    )

    charts['chart_ai_won_bar'] = upsert_slice(
        name="[TH2] Doanh thu cơ hội Won theo phân loại AI",
        viz_type="echarts_timeseries_bar",
        dataset_name="view_customer_360_analytics",
        params_dict={
            "x_axis": "ai_category",
            "metrics": ["sum_won_amount"],
            "orientation": "vertical",
            "y_axis_format": "$,.0f",
            "show_legend": False
        }
    )

    charts['chart_priority_table'] = upsert_slice(
        name="[TH2] Khách hàng ưu tiên chăm sóc & SLA",
        viz_type="table",
        dataset_name="view_customer_360_analytics",
        params_dict={
            "all_columns": ["customer_name", "company", "ai_category", "open_pipeline_amount", "overdue_tasks_count", "source"],
            "order_by_cols": ['["overdue_tasks_count", false]', '["open_pipeline_amount", false]'],
            "server_page_length": 10,
            "show_cell_bars": True
        }
    )

    # === HÀNG 3: SALES PIPELINE & FORECAST ===
    charts['chart_pipeline_stage'] = upsert_slice(
        name="[TH2] Cơ hội bán hàng theo giai đoạn Pipeline",
        viz_type="echarts_timeseries_bar",
        dataset_name="crm_opportunity",
        params_dict={
            "x_axis": "stage",
            "metrics": ["total_amount", "count"],
            "orientation": "vertical",
            "y_axis_format": "$,.0f",
            "show_legend": True
        }
    )

    charts['chart_monthly_forecast'] = upsert_slice(
        name="[TH2] Dự báo giá trị theo tháng dự kiến chốt (Pipeline mở)",
        viz_type="echarts_timeseries_bar",
        dataset_name="view_monthly_sales_forecast",
        params_dict={
            "x_axis": "close_month",
            "metrics": ["sum_weighted_forecast", "sum_total_amount"],
            "orientation": "vertical",
            "y_axis_format": "$,.0f",
            "show_legend": True
        }
    )

    charts['chart_prob_dist'] = upsert_slice(
        name="[TH2] Phân bố cơ hội theo xác suất thành công (%)",
        viz_type="echarts_timeseries_bar",
        dataset_name="crm_opportunity",
        params_dict={
            "x_axis": "probability",
            "metrics": ["count"],
            "orientation": "vertical",
            "show_legend": False
        }
    )

    # === HÀNG 4: LEAD ACQUISITION & OPERATIONS ===
    charts['chart_lead_source'] = upsert_slice(
        name="[TH2] Số lượng Lead theo kênh tiếp cận",
        viz_type="echarts_timeseries_bar",
        dataset_name="crm_lead",
        params_dict={
            "x_axis": "source",
            "metrics": ["count"],
            "orientation": "vertical",
            "show_legend": False
        }
    )

    charts['chart_lead_conversion'] = upsert_slice(
        name="[TH2] Tỷ lệ chuyển đổi Lead theo kênh (%)",
        viz_type="echarts_timeseries_bar",
        dataset_name="crm_lead",
        params_dict={
            "x_axis": "source",
            "metrics": ["converted_rate"],
            "orientation": "vertical",
            "y_axis_format": ".1f",
            "show_legend": False
        }
    )

    charts['chart_overdue_tasks'] = upsert_slice(
        name="[TH2] Công việc theo mức độ ưu tiên",
        viz_type="echarts_timeseries_bar",
        dataset_name="crm_task",
        params_dict={
            "x_axis": "priority",
            "metrics": ["count"],
            "orientation": "vertical",
            "show_legend": False
        }
    )

    charts['chart_support_sla'] = upsert_slice(
        name="[TH2] Thời gian giải quyết Ticket SLA theo phân loại (Giờ)",
        viz_type="echarts_timeseries_bar",
        dataset_name="view_support_sla",
        params_dict={
            "x_axis": "category",
            "metrics": ["avg_sla_hours", "count"],
            "orientation": "vertical",
            "show_legend": True
        }
    )

    # === HÀNG 5: LEAD SCORING INTELLIGENCE (AI/ML) ===
    charts['chart_lead_score_tier'] = upsert_slice(
        name="[TH2] Phân bổ Lead theo nhóm điểm số tiềm năng (ML)",
        viz_type="pie",
        dataset_name="view_lead_scoring_analytics",
        params_dict={
            "groupby": ["score_tier"],
            "metric": "count",
            "show_legend": True,
            "donut": True,
            "labels_outside": True,
            "color_scheme": "supersetColors"
        }
    )

    charts['chart_hot_leads_table'] = upsert_slice(
        name="[TH2] Danh sách Lead nóng (Hot Leads) ưu tiên chốt đơn",
        viz_type="table",
        dataset_name="view_lead_scoring_analytics",
        params_dict={
            "all_columns": ["lead_name", "source", "score", "score_tier", "status", "need"],
            "order_by_cols": ['["score", false]'],
            "server_page_length": 10,
            "show_cell_bars": True
        }
    )

    db.session.commit()
    print(f"- Đã lưu thành công 18 Charts cho Dashboard TH2.")

    # 6. Gán các Slice vào Dashboard TH2
    dash.slices = list(charts.values())

    # 7. Xây dựng cấu trúc bố cục Grid chuẩn v2 (12-column grid)
    position = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"children": ["GRID_ID"], "id": "ROOT_ID", "type": "ROOT"},
        "GRID_ID": {
            "children": ["ROW_KPI", "ROW_AI", "ROW_SALES", "ROW_LEAD", "ROW_LEAD_AI"],
            "id": "GRID_ID",
            "parents": ["ROOT_ID"],
            "type": "GRID"
        },
        "HEADER_ID": {
            "id": "HEADER_ID",
            "meta": {"text": DASHBOARD_TITLE},
            "type": "HEADER"
        },
        # Hàng 1: 6 KPIs (mỗi thẻ width=2)
        "ROW_KPI": {
            "children": [
                f"CHART_{charts['kpi_total_customers'].id}",
                f"CHART_{charts['kpi_total_leads'].id}",
                f"CHART_{charts['kpi_open_pipeline'].id}",
                f"CHART_{charts['kpi_weighted_forecast'].id}",
                f"CHART_{charts['kpi_won_revenue'].id}",
                f"CHART_{charts['kpi_high_potential_pct'].id}"
            ],
            "id": "ROW_KPI",
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
            "parents": ["ROOT_ID", "GRID_ID"],
            "type": "ROW"
        },
        # Hàng 2: AI Customer Intelligence (3 biểu đồ, mỗi thẻ width=4)
        "ROW_AI": {
            "children": [
                f"CHART_{charts['chart_ai_pie'].id}",
                f"CHART_{charts['chart_ai_won_bar'].id}",
                f"CHART_{charts['chart_priority_table'].id}"
            ],
            "id": "ROW_AI",
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
            "parents": ["ROOT_ID", "GRID_ID"],
            "type": "ROW"
        },
        # Hàng 3: Sales Pipeline & Forecast (3 biểu đồ, mỗi thẻ width=4)
        "ROW_SALES": {
            "children": [
                f"CHART_{charts['chart_pipeline_stage'].id}",
                f"CHART_{charts['chart_monthly_forecast'].id}",
                f"CHART_{charts['chart_prob_dist'].id}"
            ],
            "id": "ROW_SALES",
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
            "parents": ["ROOT_ID", "GRID_ID"],
            "type": "ROW"
        },
        # Hàng 4: Lead & Operations (4 biểu đồ, mỗi thẻ width=3)
        "ROW_LEAD": {
            "children": [
                f"CHART_{charts['chart_lead_source'].id}",
                f"CHART_{charts['chart_lead_conversion'].id}",
                f"CHART_{charts['chart_overdue_tasks'].id}",
                f"CHART_{charts['chart_support_sla'].id}"
            ],
            "id": "ROW_LEAD",
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
            "parents": ["ROOT_ID", "GRID_ID"],
            "type": "ROW"
        },
        # Hàng 5: Lead Scoring Intelligence (2 biểu đồ: width 4 và width 8)
        "ROW_LEAD_AI": {
            "children": [
                f"CHART_{charts['chart_lead_score_tier'].id}",
                f"CHART_{charts['chart_hot_leads_table'].id}"
            ],
            "id": "ROW_LEAD_AI",
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
            "parents": ["ROOT_ID", "GRID_ID"],
            "type": "ROW"
        }
    }

    # Định nghĩa chi tiết từng ô CHART trong position_json
    chart_configs = [
        # (key, slice_obj, row_id, width, height)
        ('kpi_total_customers', charts['kpi_total_customers'], 'ROW_KPI', 2, 28),
        ('kpi_total_leads', charts['kpi_total_leads'], 'ROW_KPI', 2, 28),
        ('kpi_open_pipeline', charts['kpi_open_pipeline'], 'ROW_KPI', 2, 28),
        ('kpi_weighted_forecast', charts['kpi_weighted_forecast'], 'ROW_KPI', 2, 28),
        ('kpi_won_revenue', charts['kpi_won_revenue'], 'ROW_KPI', 2, 28),
        ('kpi_high_potential_pct', charts['kpi_high_potential_pct'], 'ROW_KPI', 2, 28),

        ('chart_ai_pie', charts['chart_ai_pie'], 'ROW_AI', 4, 52),
        ('chart_ai_won_bar', charts['chart_ai_won_bar'], 'ROW_AI', 4, 52),
        ('chart_priority_table', charts['chart_priority_table'], 'ROW_AI', 4, 52),

        ('chart_pipeline_stage', charts['chart_pipeline_stage'], 'ROW_SALES', 4, 52),
        ('chart_monthly_forecast', charts['chart_monthly_forecast'], 'ROW_SALES', 4, 52),
        ('chart_prob_dist', charts['chart_prob_dist'], 'ROW_SALES', 4, 52),

        ('chart_lead_source', charts['chart_lead_source'], 'ROW_LEAD', 3, 50),
        ('chart_lead_conversion', charts['chart_lead_conversion'], 'ROW_LEAD', 3, 50),
        ('chart_overdue_tasks', charts['chart_overdue_tasks'], 'ROW_LEAD', 3, 50),
        ('chart_support_sla', charts['chart_support_sla'], 'ROW_LEAD', 3, 50),

        ('chart_lead_score_tier', charts['chart_lead_score_tier'], 'ROW_LEAD_AI', 4, 52),
        ('chart_hot_leads_table', charts['chart_hot_leads_table'], 'ROW_LEAD_AI', 8, 52),
    ]

    for key, slc, r_id, w, h in chart_configs:
        cid = f"CHART_{slc.id}"
        position[cid] = {
            "children": [],
            "id": cid,
            "meta": {
                "chartId": slc.id,
                "height": h,
                "sliceName": slc.slice_name,
                "uuid": str(uuid.uuid4()),
                "width": w
            },
            "parents": ["ROOT_ID", "GRID_ID", r_id],
            "type": "CHART"
        }

    dash.position_json = json.dumps(position, ensure_ascii=False)
    
    # Metadata: Kích hoạt cross filters và color scheme nhất quán
    metadata = {
        "color_scheme": "supersetColors",
        "cross_filters_enabled": True,
        "refresh_frequency": 0,
        "native_filter_configuration": []
    }
    dash.json_metadata = json.dumps(metadata, ensure_ascii=False)

    db.session.commit()
    print(f"=== ĐÃ XÂY DỰNG XONG DASHBOARD TH2: ID = {dash.id} ===")
    print(f"- Số lượng biểu đồ trong Dashboard: {len(dash.slices)}")
