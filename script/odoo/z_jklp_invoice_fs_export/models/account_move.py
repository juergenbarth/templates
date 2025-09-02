import os
import re
import logging
from datetime import datetime
from odoo import models

_logger = logging.getLogger(__name__)

# Kandidaten für Report-Actions (CE/Localization kann variieren)
REPORT_ACTION_XMLIDS = [
    "account.action_report_invoice_with_payments",
    "account.action_report_invoice",
    "account.account_invoices",
]

def _safe(text: str, fallback: str = "") -> str:
    if not text:
        return fallback
    t = text.strip().replace("/", "-")
    t = re.sub(r"[^A-Za-z0-9._\\-]+", "_", t)
    return t[:160] or fallback

def _apply_filename_pattern(pattern: str, move) -> str:
    """
    Platzhalter:
      {invoice_number}  → move.name/ref
      {partner}         → Partnername
      {date}            → Rechnungsdatum (YYYY-MM-DD)
      {id}              → Datensatz-ID
    """
    inv_no = _safe(move.name or move.ref or f"INV-{move.id}", "INV")
    partner = _safe(getattr(move.partner_id, "name", "") or "Kunde", "Kunde")
    inv_date = move.invoice_date and move.invoice_date.strftime("%Y-%m-%d") or datetime.now().strftime("%Y-%m-%d")
    name = pattern.format(invoice_number=inv_no, partner=partner, date=inv_date, id=move.id)
    name = re.sub(r"\s+", "_", name).strip(". ")
    return name or inv_no

def _apply_subdir_pattern(pattern: str, move, base_dir: str) -> str:
    """
    Platzhalter:
      {YYYY} {MM} {DD} {company} {partner}
    """
    d = move.invoice_date or datetime.today()
    y, m, dd = d.strftime("%Y"), d.strftime("%m"), d.strftime("%d")
    company = _safe(getattr(move.company_id, "name", "") or "Company", "Company")
    partner = _safe(getattr(move.partner_id, "name", "") or "Kunde", "Kunde")
    sub = pattern.format(YYYY=y, MM=m, DD=dd, company=company, partner=partner).replace("//", "/").strip("/")
    return os.path.join(base_dir, sub) if sub else base_dir

class AccountMove(models.Model):
    _inherit = "account.move"

    # ---------- Hilfen ----------

    def _get_invoice_report_action(self):
        """Finde eine ir.actions.report (qweb-pdf) für account.move."""
        for xid in REPORT_ACTION_XMLIDS:
            try:
                rec = self.env.ref(xid)
                if rec._name == "ir.actions.report" and rec.report_type == "qweb-pdf":
                    return rec
            except ValueError:
                continue
        return self.env["ir.actions.report"].sudo().search([
            ("model", "=", "account.move"),
            ("report_type", "=", "qweb-pdf"),
        ], limit=1) or False

    # ---------- Kern ----------

    def _export_pdf_to_fs(self):
        icp = self.env["ir.config_parameter"].sudo()

        target_dir = icp.get_param("jklp_invoice_fs_export.path", "/mnt/paperless_consume")
        subdir_pattern = icp.get_param("jklp_invoice_fs_export.subdir_pattern", "")
        filename_pattern = icp.get_param("jklp_invoice_fs_export.filename_pattern", "{invoice_number}")
        canary = icp.get_param("jklp_invoice_fs_export.canary", "false").lower() == "true"

        os.makedirs(target_dir, exist_ok=True)

        action = self._get_invoice_report_action()
        if not action or not action.report_name:
            _logger.error("JKLP: Keine geeignete ir.actions.report gefunden.")
            return

        report_ref = action.report_name  # in Odoo 18 als report_ref verwenden
        moves = self.filtered(lambda m: m.state == "posted" and m.move_type in ("out_invoice", "out_refund"))
        if not moves:
            return

        for move in moves:
            # UI-/Company-/Report-Kontext erzwingen (Branding)
            ctx = {
                "lang": move.partner_id.lang or self.env.user.lang,
                "tz": self.env.user.tz,
                "company_id": move.company_id.id,
                "allowed_company_ids": [move.company_id.id],
                "active_model": "account.move",
                "active_ids": [move.id],
                "active_id": move.id,
            }
            action_wc = action.with_company(move.company_id.id).with_context(**ctx).sudo()

            # Odoo 18: report_ref=action.report_name, res_ids=[...]
            pdf_content, _ = action_wc._render_qweb_pdf(report_ref=report_ref, res_ids=[move.id])

            # Zielordner (optional mit Subdir)
            out_dir = _apply_subdir_pattern(subdir_pattern, move, target_dir) if subdir_pattern else target_dir
            os.makedirs(out_dir, exist_ok=True)

            # Dateiname
            base_name = _apply_filename_pattern(filename_pattern, move)
            out_path = os.path.join(out_dir, f"{base_name}.pdf")

            # Kollisionsschutz
            if os.path.exists(out_path):
                i = 1
                while os.path.exists(os.path.join(out_dir, f"{base_name}-{i}.pdf")):
                    i += 1
                out_path = os.path.join(out_dir, f"{base_name}-{i}.pdf")

            with open(out_path, "wb") as f:
                f.write(pdf_content)

            if canary:
                _logger.warning("JKLP: Exported %s", out_path)

    # ---------- Hooks ----------

    def action_post(self):
        res = super().action_post()
        if self.env["ir.config_parameter"].sudo().get_param("jklp_invoice_fs_export.on_post", "false").lower() == "true":
            self.sudo()._export_pdf_to_fs()
        return res

    def action_invoice_sent(self):
        res = super().action_invoice_sent()
        if self.env["ir.config_parameter"].sudo().get_param("jklp_invoice_fs_export.on_send", "true").lower() == "true":
            self.sudo()._export_pdf_to_fs()
        return res
