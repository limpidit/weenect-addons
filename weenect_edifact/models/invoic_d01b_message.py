
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
        delivery = self.invoice.partner_shipping_id or self.invoice.partner_id.parent_id or self.invoice.partner_id
        delivery_gln = self._get_gln(delivery)

        self.add_segment(self.get_header_segment())

        doc_code = "380" if self.invoice.move_type == "out_invoice" else "381"
        self.add_segment(Segment("BGM", [doc_code, self.invoice.name, "9"]))
        self.add_segment(Segment("DTM", ["137", date_invoice.strftime("%Y%m%d"), "102"]))

        picking = self._get_picking()
        if picking:
            self.add_segment(Segment("RFF", ["DQ", picking.name]))

        if delivery_date:
            self.add_segment(Segment("DTM", ["171", delivery_date.strftime("%Y%m%d"), "102"]))

        self.add_segment(Segment("NAD", "SU", company_gln))
        self.add_segment(Segment("NAD", "BY", "4333671000007")) # Tout le temps le même GLN pour le client Futterhaus
        self.add_segment(Segment("NAD", "DP", delivery_gln))

        self.add_segment(Segment("RFF", ["VA", delivery.vat]))

        if date_due:
            self.add_segment(Segment("DTM", ["13", date_due.strftime("%Y%m%d"), "102"]))

        for idx, line in enumerate(self.invoice.invoice_line_ids.filtered(lambda l: l.product_id), start=1):
            self.add_segment(Segment("LIN", [str(idx), "", line.product_id.ean_weenect or "", "EN"]))
            self.add_segment(Segment("IMD", "A", "", ["", "", "", line.name[:70]]))
            self.add_segment(Segment("QTY", ["47", str(line.quantity)]))
            self.add_segment(Segment("MOA", ["203", f"{round(line.price_subtotal, 2):.2f}"]))
            self.add_segment(Segment("TAX", ["7", "VAT"]))

        self.add_segment(Segment("UNS", ["S"]))

        # Résumé global
        total = round(self.invoice.amount_total, 2)
        untaxed = round(self.invoice.amount_untaxed, 2)
        tax = round(self.invoice.amount_tax, 2)

        self.add_segment(Segment("MOA", ["77", f"{total:.2f}"]))     # Total TTC
        self.add_segment(Segment("MOA", ["79", f"{untaxed:.2f}"]))   # Total HT
        self.add_segment(Segment("MOA", ["125", f"{untaxed:.2f}"]))  # Base imposable
        self.add_segment(Segment("MOA", ["124", f"{tax:.2f}"]))      # Montant TVA

        # Détail par taux de taxe
        taxes = self._get_taxes_by_rate()
        for rate, base in taxes.items():
            rate_int = int(rate)  # arrondi pour correspondre au format ':::<taux>+E'
            tax_amount = round(base * rate / 100, 2)

            self.add_segment(Segment("TAX", "7", "VAT", "", "", ["", "", "", str(rate_int)], "E"))
            self.add_segment(Segment("MOA", ["79", f"{base:.2f}"]))        # Montant HT pour ce taux
            self.add_segment(Segment("MOA", ["125", f"{base:.2f}"]))       # Base imposable pour ce taux
            self.add_segment(Segment("MOA", ["124", f"{tax_amount:.2f}"])) # TVA pour ce taux

        self.add_segment(self.get_footer_segment())

    def _get_gln(self, partner):
        gln = partner.id_numbers.filtered(lambda x: x.category_id.code == "gln_id_number")
        return gln[0].name if gln else ""

    def _get_picking(self):
        source_order = self.invoice.line_ids.sale_line_ids.order_id
        if not source_order:
            return None
        picking_type = "outgoing" if self.invoice.move_type == "out_invoice" else "incoming"
        return source_order.picking_ids.filtered(
            lambda p: p.state != 'cancel' and p.picking_type_id.code == picking_type
        ).sorted(key=lambda p: p.date_done)[-1:] or None

    def _get_delivery_date(self):
        picking = self._get_picking()
        return picking.date_done.date() if picking and picking.date_done else None

    def _get_taxes_by_rate(self):
        taxes = {}
        for line in self.invoice.invoice_line_ids:
            for tax in line.tax_ids.filtered(lambda t: t.amount_type == 'percent'):
                rate = tax.amount
                taxes[rate] = taxes.get(rate, 0.0) + line.price_subtotal
        return taxes