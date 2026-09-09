
from datetime import datetime, timedelta

from pydifact.segmentcollection import Message
from pydifact.segments import Segment


class InvoicD01BMessage(Message):
    """Générateur de facture EDIFACT INVOIC D01B conforme Futterhaus BELA"""

    def __init__(self, invoice):
        super().__init__(str(invoice.id), ("INVOIC", "D", "01B", "UN"))
        self.invoice = invoice
        self.generate()

    def generate(self):
        date_invoice = self.invoice.invoice_date or self.invoice.create_date.date()
        date_due = self.invoice.invoice_date_due or date_invoice
        delivery_date = self._get_delivery_date()

        company_gln = self._get_gln(self.invoice.company_id.partner_id)
        delivery = self.invoice.partner_shipping_id or self.invoice.partner_id
        delivery_gln = self._get_gln(delivery)
        if not delivery_gln:
            # Fallback : GLN du partenaire commercial (BELA FUTTERHAUS)
            delivery_gln = self._get_gln(self.invoice.partner_id.commercial_partner_id)

        self.add_segment(self.get_header_segment())

        doc_code = "380" if self.invoice.move_type == "out_invoice" else "381"
        self.add_segment(Segment("BGM", doc_code, self.invoice.name, "9"))
        self.add_segment(Segment("DTM", ["137", date_invoice.strftime("%Y%m%d"), "102"]))
        self.add_segment(Segment("FTX", "AAK", "1", "ST1"))
        self.add_segment(Segment("FTX", "ZZZ", "1", "EEV"))

        picking = self._get_picking()
        if picking:
            self.add_segment(Segment("RFF", ["DQ", picking.name]))

        if delivery_date:
            self.add_segment(Segment("DTM", ["171", delivery_date.strftime("%Y%m%d"), "102"]))

        self.add_segment(Segment("NAD", "SU", [company_gln, "", "9"]))
        self.add_segment(Segment("NAD", "BY", ["4333671000007", "", "9"])) # Tout le temps le même GLN pour le client Futterhaus
        self.add_segment(Segment("NAD", "DP", [delivery_gln, "", "9"]))
        self.add_segment(Segment("RFF", ["VA", self.invoice.partner_id.vat or ""]))

        self.add_segment(Segment("TAX", "7", "VAT", "", "", ["", "", "", "0"], "E"))
        self.add_segment(Segment("CUX", ["2", "EUR", "4"]))

        # Conditions de paiement : après TAX/CUX (ordre exigé par Futterhaus)
        payment_term = self.invoice.invoice_payment_term_id
        if payment_term and payment_term.early_discount and payment_term.discount_days:
            discount_date = date_invoice + timedelta(days=payment_term.discount_days)
            self.add_segment(Segment("PAT", "22"))
            self.add_segment(Segment("DTM", ["12", discount_date.strftime("%Y%m%d"), "102"]))

        if date_due:
            self.add_segment(Segment("PAT", "3"))
            self.add_segment(Segment("DTM", ["13", date_due.strftime("%Y%m%d"), "102"]))

        total_net = 0.0
        net_by_rate = {}
        for idx, line in enumerate(self.invoice.invoice_line_ids.filtered(lambda l: l.product_id), start=1):
            taxes = line.tax_ids
            if taxes:
                tax_rate = taxes[0].amount
                if tax_rate == int(tax_rate):
                    tax_rate = int(tax_rate)
            else:
                tax_rate = 0
            # Bela recalcule la facture à partir du prix unitaire (PRI+AAA) et ne déduit
            # PAS de remise séparée. La remise doit donc être DANS le prix unitaire (prix
            # net). On dérive MOA+203 de ce prix pour que QTY x PRI = MOA+203 exactement,
            # et le résumé est la somme de ces montants de ligne.
            net_unit_price = round(line.price_subtotal / line.quantity, 2) if line.quantity else 0.0
            net_line = round(net_unit_price * line.quantity, 2)
            total_net += net_line
            net_by_rate[tax_rate] = round(net_by_rate.get(tax_rate, 0.0) + net_line, 2)
            self.add_segment(Segment("LIN", str(idx), "", [line.product_id.ean_weenect or "", "EN"]))
            self.add_segment(Segment("IMD", "A", "", ["", "", "", line.name[:70].replace('\n', '')]))
            self.add_segment(Segment("QTY", ["47", str(line.quantity)]))
            self.add_segment(Segment("PRI", ["AAA", f"{net_unit_price:.2f}", "", "", "1", "PCE"]))
            self.add_segment(Segment("TAX", "7", "VAT", "", "", ["", "", "", str(tax_rate)], "S"))
            self.add_segment(Segment("MOA", ["203", f"{net_line:.2f}"]))

        self.add_segment(Segment("UNS", ["S"]))

        # Résumé global : basé sur les montants de ligne réellement envoyés
        total_net = round(total_net, 2)
        total_tax = round(sum(base * rate / 100 for rate, base in net_by_rate.items()), 2)
        total_ttc = round(total_net + total_tax, 2)

        self.add_segment(Segment("MOA", ["77", f"{total_ttc:.2f}"]))    # Total TTC
        self.add_segment(Segment("MOA", ["79", f"{total_net:.2f}"]))    # Total HT
        self.add_segment(Segment("MOA", ["125", f"{total_net:.2f}"]))   # Base imposable
        self.add_segment(Segment("MOA", ["124", f"{total_tax:.2f}"]))   # Montant TVA

        # Détail par taux de taxe
        for rate, base in net_by_rate.items():
            rate_int = int(rate)  # arrondi pour correspondre au format ':::<taux>+E'
            tax_amount = round(base * rate / 100, 2)

            self.add_segment(Segment("TAX", "7", "VAT", "", "", ["", "", "", str(rate_int)], "E"))
            self.add_segment(Segment("MOA", ["79", f"{base:.2f}"]))        # Montant HT pour ce taux
            self.add_segment(Segment("MOA", ["125", f"{base:.2f}"]))       # Base imposable pour ce taux
            self.add_segment(Segment("MOA", ["124", f"{tax_amount:.2f}"])) # TVA pour ce taux

        self.add_segment(self.get_footer_segment())

    def _get_gln(self, partner):
        gln = partner.id_numbers.filtered(lambda x: x.category_id.code == "gln_id_number")
        if not gln and partner.parent_id:
            gln = partner.parent_id.id_numbers.filtered(lambda x: x.category_id.code == "gln_id_number")
        return gln[0].name if gln else ""

    def _get_picking(self):
        source_order = self.invoice.line_ids.sale_line_ids.order_id
        if not source_order:
            return None
        picking_type = "outgoing" if self.invoice.move_type == "out_invoice" else "incoming"
        return source_order.picking_ids.filtered(
            lambda p: p.state != 'cancel' and p.picking_type_id.code == picking_type
        ).sorted(key=lambda p: p.date_done or datetime.min)[-1:] or None

    def _get_delivery_date(self):
        picking = self._get_picking()
        return picking.date_done.date() if picking and picking.date_done else None