"""
Management command to refresh Lead scores using the ML Lead Scorer (or Rule-Based fallback).
Defaults to --dry-run to inspect score changes safely. Use --apply to commit updates to database.
"""

import sys
import logging
from collections import Counter
from django.core.management.base import BaseCommand
from crm.models import Lead
from crm.services.lead_scoring import calculate_lead_score, get_lead_score_tier

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Refreshes scores for active (or all) leads using ML or Rule-based scoring."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            default=False,
            help="Persist updated scores to the database. Without this flag, command runs in dry-run mode.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            default=False,
            help="Score all leads including finalized ones. Default is only active leads (new, contacted, qualified).",
        )
        parser.add_argument(
            "--method",
            type=str,
            choices=["auto", "ml", "rule"],
            default="auto",
            help="Scoring engine to use: auto (prefers ML, falls back to rule), ml, or rule.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of leads to process.",
        )

    def handle(self, *args, **options):
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")

        apply_changes = options["apply"]
        score_all = options["all"]
        method = options["method"]
        limit = options["limit"]

        mode_text = "[APPLY - GHI DỮ LIỆU]" if apply_changes else "[DRY-RUN - CHỈ MÔ PHỎNG]"
        self.stdout.write(self.style.NOTICE(f"=== CẬP NHẬT ĐIỂM SỐ LEAD {mode_text} ==="))

        qs = Lead.objects.all()
        if not score_all:
            qs = qs.filter(status__in=["new", "contacted", "qualified"])
        qs = qs.order_by("id")

        if limit:
            qs = qs[:limit]

        leads_to_process = list(qs)
        total_count = len(leads_to_process)

        if total_count == 0:
            self.stdout.write(self.style.WARNING("Không có lead nào cần cập nhật điểm số."))
            return

        self.stdout.write(f"Số lượng lead xử lý: {total_count} (Tiêu chí: {'Tất cả' if score_all else 'Đang hoạt động'})")

        updates = []
        tier_counts = Counter()
        method_counts = Counter()

        for lead in leads_to_process:
            new_score, method_used = calculate_lead_score(lead.source, lead.need, method=method)
            tier = get_lead_score_tier(new_score)
            tier_counts[tier] += 1
            method_counts[method_used] += 1

            diff = new_score - lead.score
            diff_str = f"+{diff}" if diff > 0 else f"{diff}"
            updates.append({
                "lead": lead,
                "old_score": lead.score,
                "new_score": new_score,
                "diff": diff_str,
                "tier": tier,
                "method": method_used,
            })

            if apply_changes:
                lead.score = new_score
                lead.save(update_fields=["score"])

        # Display sample preview
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(f"{'ID':<5} | {'Tên Lead':<20} | {'Nguồn':<12} | {'Cũ':<4} | {'Mới':<4} | {'Đổi':<6} | {'Phân hạng':<15}")
        self.stdout.write("-" * 80)
        for u in updates[:15]:
            lead = u["lead"]
            name_disp = lead.name[:18]
            src_disp = (lead.source or "")[:10]
            self.stdout.write(
                f"{lead.id:<5} | {name_disp:<20} | {src_disp:<12} | {u['old_score']:<4} | {u['new_score']:<4} | {u['diff']:<6} | {u['tier']:<15}"
            )
        if len(updates) > 15:
            self.stdout.write(f"... và {len(updates) - 15} lead khác.")
        self.stdout.write("=" * 80 + "\n")

        # Summary statistics
        scores = [u["new_score"] for u in updates]
        avg_score = sum(scores) / len(scores) if scores else 0

        self.stdout.write("THỐNG KÊ KẾT QUẢ:")
        self.stdout.write(f"- Điểm số trung bình: {avg_score:.1f}/100")
        self.stdout.write(f"- Động cơ chấm điểm: {dict(method_counts)}")
        self.stdout.write(f"- Phân bổ nhóm tiềm năng: {dict(tier_counts)}")

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING(
                    "\n[*] Đây là chế độ DRY-RUN (chưa lưu vào DB). "
                    "Để cập nhật thật vào cơ sở dữ liệu, hãy chạy lại với cờ '--apply'."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\n[OK] Đã cập nhật thành công điểm số cho {total_count} leads vào SQLite!")
            )

