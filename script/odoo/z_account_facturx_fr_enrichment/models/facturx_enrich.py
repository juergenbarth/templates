# -*- coding: utf-8 -*-
import logging
from odoo import models
from lxml import etree

_logger = logging.getLogger(__name__)

NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}

BT120_TEXT_DEFAULT = "TVA non applicable, art. 293 B du CGI"


def _sub(el, tag, ns="ram", text=None):
    """Create a subelement in the given CII namespace and optionally set text."""
    child = etree.SubElement(el, f"{{{NS[ns]}}}{tag}")
    if text is not None:
        child.text = text
    return child


# -------- helper to be robust with different upstream return types ----------
def _xfx_bytes(x):
    """Return bytes for bytes/bytearray/memoryview/str; else None."""
    if isinstance(x, (bytes, bytearray, memoryview)):
        return bytes(x)
    if isinstance(x, str):
        return x.encode("utf-8")
    return None


def _xfx_unpack_result(res):
    """
    Normalize super().generate_facturx_xml(...) result.

    Accept bytes or a tuple containing the XML as one item.
    Return (xml_bytes, tail_tuple, was_tuple_flag).
    """
    b = _xfx_bytes(res)
    if b is not None:
        return b, (), False

    if isinstance(res, tuple):
        for i, item in enumerate(res):
            bi = _xfx_bytes(item)
            if bi is not None:
                tail = res[:i] + res[i + 1 :]  # everything except the XML item
                return bi, tail, True

    raise TypeError(f"Unsupported generate_facturx_xml return type: {type(res)!r}")


def _xfx_repack_result(xml_bytes, tail, was_tuple):
    """Put xml back into original return-shape."""
    return (xml_bytes,) + tail if was_tuple else xml_bytes


class AccountMove(models.Model):
    _inherit = "account.move"

    # ---------------- Config helpers ----------------
    def _xfx_cfg(self):
        ICP = self.env["ir.config_parameter"].sudo()
        return {
            "enable": ICP.get_param("x_facturx_fr_enrichment.enable", default="True") == "True",
            "log_enable": ICP.get_param("x_facturx_fr_enrichment.logging_enable", default="False") == "True",
            "log_level": ICP.get_param("x_facturx_fr_enrichment.logging_level", default="INFO").upper(),
            "attach_snaps": ICP.get_param("x_facturx_fr_enrichment.attach_snapshots", default="False") == "True",
            "notify": ICP.get_param("x_facturx_fr_enrichment.notify_chatter", default="True") == "True",
            # BT-32 controls
            "bt32_enable": ICP.get_param("x_facturx_fr_enrichment.bt32_enable", default="True") == "True",
            "bt32_scheme": ICP.get_param("x_facturx_fr_enrichment.bt32_scheme", default="SIRET"),
            "bt32_source": ICP.get_param("x_facturx_fr_enrichment.bt32_source", default="auto"),
            # BT-121 controls
            "bt121_enable": ICP.get_param("x_facturx_fr_enrichment.bt121_enable", default="False") == "True",
            "bt121_code": ICP.get_param("x_facturx_fr_enrichment.bt121_code", default=""),
        }

    def _xfx_log(self, level, msg, *args):
        cfg = self._xfx_cfg()
        if not cfg["log_enable"]:
            return
        configured = getattr(logging, cfg["log_level"], logging.INFO)
        severity = getattr(logging, level, logging.INFO)
        if severity >= configured:
            _logger.log(severity, msg, *args)

    def _xfx_attach(self, name, data_bytes, mimetype="application/xml"):
        cfg = self._xfx_cfg()
        if not cfg["attach_snaps"] or not self:
            return
        try:
            self.sudo().message_post(attachments=[(name, data_bytes)], body=f"Attached: {name}")
        except Exception as e:
            self._xfx_log("WARNING", "[xfx] Could not attach %s: %s", name, e)

    def _xfx_notify(self, body):
        cfg = self._xfx_cfg()
        if cfg["notify"] and self:
            self.sudo().message_post(body=body)

    # ---------------- Hook 1: preferred path ----------------
    def generate_facturx_xml(self, *args, **kwargs):
        upstream = super().generate_facturx_xml(*args, **kwargs)
        cfg = self._xfx_cfg()
        if not cfg["enable"]:
            return upstream
        try:
            xml_bytes, tail, was_tuple = _xfx_unpack_result(upstream)

            self._xfx_log("INFO", "[xfx] Enrichment via generate_facturx_xml for %s", self.ids)
            self._xfx_attach("facturx_pre_enrichment.xml", xml_bytes)

            xml_bytes = self._xfx_enrich_xml(xml_bytes)

            self._xfx_attach("facturx_post_enrichment.xml", xml_bytes)
            return _xfx_repack_result(xml_bytes, tail, was_tuple)

        except Exception as e:
            self._xfx_log("ERROR", "[xfx] Enrichment error in generate_facturx_xml: %s", e)
            self._xfx_notify(f"<p><b>Factur-X Enrichment error (gen):</b> {e}</p>")
            return upstream

    # ---------------- Hook 2: fallback path ----------------
    def _prepare_facturx_attachments(self, *args, **kwargs):
        """
        Be compatible with both call styles:
        - OCA account_invoice_facturx: _prepare_facturx_attachments()  (no args)
        - Other variants: _prepare_facturx_attachments(pdf_binary, xml_bytes)
        We enrich only if we can detect an xml_bytes argument.
        """
        cfg = self._xfx_cfg()
        xml_bytes = None
        if "xml_bytes" in kwargs:
            xml_bytes = kwargs.get("xml_bytes")
        elif args and len(args) >= 2 and isinstance(args[1], (bytes, bytearray, memoryview)):
            xml_bytes = bytes(args[1])

        if cfg["enable"] and xml_bytes:
            try:
                self._xfx_log("INFO", "[xfx] Enrichment via _prepare_facturx_attachments for %s", self.ids)
                self._xfx_attach("facturx_pre_enrichment.xml", xml_bytes)
                xml_bytes = self._xfx_enrich_xml(xml_bytes)
                self._xfx_attach("facturx_post_enrichment.xml", xml_bytes)

                if "xml_bytes" in kwargs:
                    kwargs["xml_bytes"] = xml_bytes
                elif args and len(args) >= 2:
                    args = (args[0], xml_bytes) + tuple(args[2:])
            except Exception as e:
                self._xfx_log("ERROR", "[xfx] Enrichment error in _prepare_facturx_attachments: %s", e)
                self._xfx_notify(f"<p><b>Factur-X Enrichment error (prep):</b> {e}</p>")

        return super()._prepare_facturx_attachments(*args, **kwargs)

    # ---------------- Core enrichment ----------------
    def _xfx_enrich_xml(self, xml_bytes: bytes) -> bytes:
        if not xml_bytes:
            return xml_bytes

        root = etree.fromstring(xml_bytes)

        # ---- company identifiers (SIRET/SIREN) ----
        company = self.company_id

        def _digits(s):
            return "".join(ch for ch in (s or "") if ch.isdigit())

        # try multiple sources for siret
        siret = _digits(getattr(company, "siret", None) or getattr(company, "l10n_fr_siret", None) or getattr(company.partner_id, "siret", None))
        siren = _digits(company.company_registry)

        legal_id = siret if len(siret) == 14 else (siren if len(siren) in (9, 14) else "")
        self._xfx_log("DEBUG", "[xfx] Sources: siret=%s siren=%s legal_id=%s", siret, siren, legal_id)

        seller = root.find(".//ram:SellerTradeParty", namespaces=NS)

        # (1) BT-30: SpecifiedLegalOrganization/ID mit erlaubtem schemeID (ISO 6523 EAS)
        # FR: EAS "0002" (SIRENE). Wert: SIREN (9-stellig). Aus SIRET (14) ableiten, falls nötig.
        # --- BT-30: SpecifiedLegalOrganization korrekt einsortieren + zulässiges schemeID ---
        if seller is not None:
            def _digits(s): return "".join(ch for ch in (s or "") if ch.isdigit())

            # SIREN aus company ableiten (9-stellig). Aus SIRET (14) -> erste 9.
            _siret = _digits(siret) if 'siret' in locals() else ""
            _siren = _digits(siren) if 'siren' in locals() else ""
            base_siren = _siren if len(_siren) == 9 else (_siret[:9] if len(_siret) == 14 else "")

            # Hilfen, um Kinder/Indizes zu finden
            def _idx_of(tag_local):
                q = "{%s}%s" % (NS["ram"], tag_local)
                for i, ch in enumerate(seller):
                    if ch.tag == q:
                        return i
                return -1

            idx_name = _idx_of("Name")
            idx_after_name = (idx_name + 1) if idx_name >= 0 else 0
            # vor diesen „Blockern“ muss SLO stehen:
            blockers = ["DefinedTradeContact", "PostalTradeAddress", "URIUniversalCommunication", "SpecifiedTaxRegistration"]
            blocker_indices = [i for i in (_idx_of(b) for b in blockers) if i >= 0]
            idx_before_blocker = min(blocker_indices) if blocker_indices else len(seller)
            desired_idx = min(max(idx_after_name, 0), idx_before_blocker)

            # SLO beschaffen/erzeugen
            slo = seller.find("ram:SpecifiedLegalOrganization", namespaces=NS)
            if slo is None:
                slo = etree.Element("{%s}SpecifiedLegalOrganization" % NS["ram"])
                seller.insert(desired_idx, slo)
            else:
                # ggf. verschieben
                try:
                    current_idx = list(seller).index(slo)
                except ValueError:
                    current_idx = -1
                if current_idx < 0 or not (desired_idx-1 <= current_idx <= desired_idx+1):
                    seller.remove(slo)
                    seller.insert(desired_idx, slo)

            # ID setzen (Wert = SIREN) + zulässiges schemeID für BT-30 (ISO 6523 EAS)
            id_el = slo.find("ram:ID", namespaces=NS)
            if id_el is None:
                id_el = etree.SubElement(slo, "{%s}ID" % NS["ram"])
            if base_siren and not (id_el.text or "").strip():
                id_el.text = base_siren

            # Factur-X/EN16931: BT-30 erwartet EAS-Codeliste -> Frankreich = "0002" (SIRENE)
            # (keine freien Werte wie "SIREN"/"SIRET" hier!)
            id_el.set("schemeID", "0002")

            self._xfx_log("DEBUG", "[xfx] BT-30 set/moved: %s (schemeID=0002) at idx %s",
                          id_el.text or "", desired_idx)




        # (1b) BT-32 — Seller tax registration identifier
        # Haupt-Regel: Für EN16931/QUBA in FR muss BT-32 mit schemeID="FC" (SIREN) geschrieben werden.
        # Optional kann zusätzlich SIRET mit eigenem schemeID hinterlegt werden (nur informativ).

        cfg_local = self._xfx_cfg()
        if seller is not None and cfg_local.get("bt32_enable", True):
            ICP = self.env["ir.config_parameter"].sudo()
            write_siret_too = ICP.get_param(
                "x_facturx_fr_enrichment.bt32_write_siret_also", "False"  # Default: nur SIREN/FC
            ) == "True"

            # --- Quellen normalisieren ---
            def _digits(s):
                return "".join(ch for ch in (s or "") if ch.isdigit())

            _siret = _digits(siret) if 'siret' in locals() else ""
            _siren = _digits(siren) if 'siren' in locals() else ""

            base_siret = _siret if len(_siret) == 14 else ""
            base_siren = _siren if len(_siren) == 9 else (_siret[:9] if len(_siret) == 14 else "")

            # --- Helper: Existenz prüfen (optional auch Schema prüfen) ---
            def _has_tax_reg(val, scheme=None):
                for reg in seller.findall("ram:SpecifiedTaxRegistration", namespaces=NS):
                    ide = reg.find("ram:ID", namespaces=NS)
                    if ide is not None and (ide.text or "").strip() == val:
                        if scheme is None or (ide.get("schemeID") or "").strip() == scheme:
                            return True
                return False

            # --- 1) SIREN als Haupteintrag mit schemeID="FC" ---
            if base_siren and not _has_tax_reg(base_siren, "FC"):
                reg = _sub(seller, "SpecifiedTaxRegistration")
                ide = _sub(reg, "ID", text=base_siren)
                ide.set("schemeID", "FC")
                self._xfx_log("DEBUG", "[xfx] BT-32 main set to %s (scheme=FC)", base_siren)

            # --- 2) Optional zusätzlich SIRET (informativ; von Viewern meist ignoriert) ---
            if write_siret_too and base_siret and not _has_tax_reg(base_siret):
                reg2 = _sub(seller, "SpecifiedTaxRegistration")
                ide2 = _sub(reg2, "ID", text=base_siret)
                ide2.set("schemeID", "SIRET")
                self._xfx_log("DEBUG", "[xfx] BT-32 secondary set to %s (scheme=SIRET)", base_siret)


        # (2) BT-85: Account name (use AccountName, not Name)
        pm = root.find(".//ram:SpecifiedTradeSettlementPaymentMeans", namespaces=NS)
        if pm is not None:
            acct = pm.find("ram:PayeePartyCreditorFinancialAccount", namespaces=NS)
            if acct is not None and acct.find("ram:AccountName", namespaces=NS) is None:
                acc = self.company_id.partner_id.bank_ids[:1]
                acc_name = None
                if acc:
                    acc_name = getattr(acc, "acc_holder_name", None) or getattr(acc, "acc_holder", None)
                if not acc_name:
                    acc_name = self.company_id.partner_id.name or self.company_id.name
                if acc_name:
                    _sub(acct, "AccountName", text=acc_name)
                    self._xfx_log("DEBUG", "[xfx] BT-85 set to %s (AccountName)", acc_name)
                else:
                    self._xfx_log("INFO", "[xfx] BT-85 skipped (no holder/partner/company name)")

        # =========================
        # (BT-120 / BT-121 Handling) — nur wenn es passt
        # =========================
        # Regeln:
        # - BT-120 (ExemptionReason) / BT-121 (ExemptionReasonCode) setzen wir NICHT blind.
        # - Wir fügen BT-120 (Default-Text) nur hinzu, wenn:
        #   * Verkäufer in FR ist UND
        #   * im XML KEIN BT-31 (VAT-ID, schemeID="VA") existiert UND
        #   * die Steuerkategorie am Header 'E' ist UND
        #   * noch kein ExemptionReason/Code vorhanden ist.
        # - Optional: BT-121 per Config.
        #
        # Konfig:
        # - x_facturx_fr_enrichment.bt120_text (optional, überschreibt Default)
        # - x_facturx_fr_enrichment.bt121_enable / x_facturx_fr_enrichment.bt121_code

        # Reihenfolge-Helfer: ExemptionReason/Code vor BasisAmount/CategoryCode ziehen
        def _ensure_reason_before_base_and_category(tax_el):
            exr = tax_el.find("ram:ExemptionReason", namespaces=NS)
            exr_code = tax_el.find("ram:ExemptionReasonCode", namespaces=NS)

            children = list(tax_el)
            target_idx = None
            for i, ch in enumerate(children):
                local = etree.QName(ch).localname
                if local in ("BasisAmount", "CategoryCode"):
                    target_idx = i
                    break
            if target_idx is None:
                return

            if exr is not None:
                try:
                    tax_el.remove(exr)
                except Exception:
                    pass
                tax_el.insert(target_idx, exr)
                if exr_code is not None:
                    try:
                        tax_el.remove(exr_code)
                    except Exception:
                        pass
                    tax_el.insert(target_idx + 1, exr_code)
            elif exr_code is not None:
                try:
                    tax_el.remove(exr_code)
                except Exception:
                    pass
                tax_el.insert(target_idx, exr_code)

        # Bedingungen für sinnvolles Setzen ermitteln
        seller_country = (self.company_id.country_id.code or "").upper()
        seller_vat_field = (self.company_id.partner_id.vat or self.company_id.vat or "")  # Odoo-Stammdaten
        # BT-31 im XML? (Seller VAT-ID = schemeID "VA")
        has_bt31_xml = False
        if seller is not None:
            vat_id_xml = seller.find("ram:SpecifiedTaxRegistration/ram:ID[@schemeID='VA']", namespaces=NS)
            has_bt31_xml = vat_id_xml is not None

        # Optional überschreibbarer BT-120-Text aus Config
        ICP = self.env["ir.config_parameter"].sudo()
        bt120_text = (ICP.get_param("x_facturx_fr_enrichment.bt120_text") or "").strip() or BT120_TEXT_DEFAULT

        # HEADER: Nur wenn Kategorie 'E' und Bedingungen erfüllt -> Reason/Code setzen
        for tax in root.findall(".//ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax", namespaces=NS):
            cat = tax.find("ram:CategoryCode", namespaces=NS)
            if cat is None or (cat.text or "").strip() != "E":
                continue

            has_text = tax.find("ram:ExemptionReason", namespaces=NS) is not None
            has_code = tax.find("ram:ExemptionReasonCode", namespaces=NS) is not None

            # Setz-Bedingung:
            # - Verkäufer FR
            # - KEINE VAT-ID (weder in Odoo-Stammdaten noch als BT-31 im XML)
            # - noch kein Reason im Header vorhanden
            cond_fr_micro = (seller_country == "FR") and (not seller_vat_field) and (not has_bt31_xml)

            if cond_fr_micro and not has_text:
                _sub(tax, "ExemptionReason", text=bt120_text)
                self._xfx_log("DEBUG", "[xfx] BT-120 set on header (text=%s)", bt120_text)

            if cond_fr_micro and cfg_local.get("bt121_enable", False) and not has_code:
                code = (cfg_local.get("bt121_code") or "").strip()
                if code:
                    _sub(tax, "ExemptionReasonCode", text=code)
                    self._xfx_log("DEBUG", "[xfx] BT-121 set on header (code=%s)", code)

        # Reihenfolge-Fix in ALLEN Tax-Blöcken (Header + Lines)
        for tax in root.findall(".//ram:ApplicableTradeTax", namespaces=NS):
            _ensure_reason_before_base_and_category(tax)


        return etree.tostring(root, xml_declaration=True, encoding="UTF-8")
