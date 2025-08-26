from odoo import models
from lxml import etree
import logging

_logger = logging.getLogger(__name__)

RAM_NS = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"

def _bt85_inject(xml_bytes: bytes, account_name: str) -> bytes:
    """Insert <ram:AccountName> under *(PayeeParty)CreditorFinancialAccount if missing/empty."""
    try:
        root = etree.fromstring(xml_bytes)
    except Exception as e:
        _logger.exception("BT-85: XML parse failed: %s", e)
        return xml_bytes

    ns = {
        "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
        "ram": RAM_NS,
    }
    paths = [
        ".//rsm:SupplyChainTradeTransaction/ram:ApplicableHeaderTradeSettlement/ram:SpecifiedTradeSettlementPaymentMeans/ram:PayeePartyCreditorFinancialAccount",
        ".//rsm:SupplyChainTradeTransaction/ram:ApplicableHeaderTradeSettlement/ram:SpecifiedTradeSettlementPaymentMeans/ram:CreditorFinancialAccount",
        ".//*[local-name()='SpecifiedTradeSettlementPaymentMeans']/*[contains(local-name(),'CreditorFinancialAccount')]",
    ]

    modified = False
    nodes = []
    for xp in paths:
        try:
            nodes = root.xpath(xp, namespaces=ns)
        except Exception:
            nodes = root.xpath(xp) if "local-name()" in xp else []
        if nodes:
            break

    if not nodes:
        return xml_bytes

    for node in nodes:
        existing = node.xpath("ram:AccountName", namespaces={"ram": RAM_NS}) or node.xpath(".//*[local-name()='AccountName']")
        if existing and (existing[0].text or "").strip():
            continue

        el = existing[0] if existing else etree.SubElement(node, "{%s}AccountName" % RAM_NS)
        el.text = account_name
        modified = True

    return etree.tostring(root, encoding="UTF-8", xml_declaration=True, pretty_print=True) if modified else xml_bytes


class AccountMove(models.Model):
    _inherit = "account.move"

    def _bt85_get_account_name(self):
        """Resolve account holder name from journal bank -> invoice bank -> company name."""
        self.ensure_one()
        bank = getattr(self.journal_id, "bank_account_id", False)
        if bank and (getattr(bank, "acc_holder_name", None) or (bank.partner_id and bank.partner_id.name)):
            return (getattr(bank, "acc_holder_name", None) or bank.partner_id.name).strip()
        for fld in ("partner_bank_id", "invoice_partner_bank_id", "company_partner_bank_id"):
            b = getattr(self, fld, False)
            if b and (getattr(b, "acc_holder_name", None) or (b.partner_id and b.partner_id.name)):
                return (getattr(b, "acc_holder_name", None) or b.partner_id.name).strip()
        return (self.company_id.partner_id.name or "").strip() or None

    def generate_facturx_xml(self):
        """Call OCA generate_facturx_xml and inject BT-85 before returning."""
        xml_bytes, level = super().generate_facturx_xml()
        try:
            name = self._bt85_get_account_name()
            if name:
                xml_bytes = _bt85_inject(xml_bytes, name)
        except Exception:
            _logger.exception("BT-85: injection failed in generate_facturx_xml")
        return (xml_bytes, level)
