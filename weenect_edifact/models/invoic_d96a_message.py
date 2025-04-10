
from pydifact.segmentcollection import Message
from pydifact.segments import Segment


class InvoicD96AMessage(Message):
    """Générateur de facture EDIFACT INVOIC D96A conforme SAGAFLOR"""

    def __init__(self, invoice):
        super().__init__(str(invoice.id), ("INVOIC", "D", "96A", "UN", "EAN008"))
        self.invoice = invoice
        self.generate()

    def generate(self):
        self.add_segment(self.get_header_segment())

        doc_code = "380" if self.invoice.move_type == "out_invoice" else "381"
        self.add_segment(Segment("BGM", [doc_code, self.invoice.name, "9"]))

        date_invoice = self.invoice.invoice_date or self.invoice.create_date.date()
        self.add_segment(Segment("DTM", ["137", date_invoice.strftime("%Y%m%d"), "102"]))

        picking = self._get_picking()
        if picking:
            self.add_segment(Segment("DTM", ["35", picking.date_done.date().strftime("%Y%m%d"), "102"]))

        self.add_segment(Segment("FTX", "ZZZ", "", "", "Zentralregulierung über SAGAFLOR AG"))
        self.add_segment(Segment("FTX", "ZZZ", "", "", "Mehrwertsteuerbefreiung, art. 262 ter-l französisches Steuergesetzbuch"))

        source_order = self.invoice.line_ids.sale_line_ids.order_id
        if source_order:
            self.add_segment(Segment("RFF", ["ON", source_order.name]))
            self.add_segment(Segment("DTM", ["171", source_order.date_order.date().strftime("%Y%m%d"), "102"]))

        if picking:
            self.add_segment(Segment("RFF", ["DQ", picking.name]))
            self.add_segment(Segment("DTM", ["171", picking.date_done.date().strftime("%Y%m%d"), "102"]))

        # Supplier
        company = self.invoice.company_id.partner_id
        company_gln = self._get_gln(company)
        if not company_gln:
            raise ValueError("Company GLN not found")
        company_names = [company.display_name[i:i+35] for i in range(0, len(company.display_name), 35)]
        self.add_segment(Segment("NAD", "SU", [company_gln, "", "9"], "", company_names, company.street, company.city, "", company.zip, company.country_id.code))
        self.add_segment(Segment("RFF", ["VA", self.invoice.company_id.vat]))

        # Buyer
        buyer = self.invoice.partner_id
        buyer_gln = self._get_gln(buyer)
        if not buyer_gln:
            raise ValueError("Buyer GLN not found")
        buyer_names = [buyer.display_name[i:i+35] for i in range(0, len(buyer.display_name), 35)]
        self.add_segment(Segment("NAD", "BY", [buyer_gln, "", "9"], "", buyer_names, buyer.street, buyer.city, "", buyer.zip, buyer.country_id.code))
        self.add_segment(Segment("RFF", ["VA", buyer.vat]))

        # Delivery
        delivery = self.invoice.partner_shipping_id
        if delivery and delivery != buyer:
            delivery_gln = self._get_gln(delivery)
            if not delivery_gln:
                raise ValueError("Delivery GLN not found")
            delivery_names = [delivery.display_name[i:i+35] for i in range(0, len(delivery.display_name), 35)]
            self.add_segment(Segment("NAD", "DP", [delivery_gln, "", "9"], "", delivery_names, delivery.street, delivery.city, "", delivery.zip, delivery.country_id.code))
            self.add_segment(Segment("RFF", ["VA", delivery.vat]))

        self.add_segment(Segment("CUX", ["2", "EUR", "4"]))

        # Lines
        taxes = {}
        for idx, line in enumerate(self.invoice.invoice_line_ids.filtered(lambda l: l.product_id), start=1):
            product = line.product_id

            line_pdf_description = (product.client_friendly_name or "") + " " + (line.name or "")
            libelle_part1 = line_pdf_description[:35]
            libelle_part2 = line_pdf_description[35:70] if len(line_pdf_description) > 35 else ""
            libelle_segment = ["", "", "", libelle_part1]
            if libelle_part2:
                libelle_segment.append(libelle_part2)

            product_price_unit = round(line.price_unit, 2)
            line_price_subtotal = round(line.price_subtotal, 2)

            product_tax = 0
            if line.tax_ids and line.tax_ids.amount_type == "percent":
                product_tax = line.tax_ids[0].amount
                taxes[product_tax] = taxes.get(product_tax, 0.0) + line_price_subtotal

            self.add_segment(Segment("LIN", str(idx), "", [product.ean_weenect, "EN"]))
            self.add_segment(Segment("PIA", "5", [str(product.id), "SA", "", "91"]))
            self.add_segment(Segment("IMD", "A", "", libelle_segment))
            self.add_segment(Segment("QTY", ["47", str(line.quantity), "PCE"]))
            self.add_segment(Segment("MOA", ["203", f"{line_price_subtotal:.2f}"]))

            if line.discount:
                discount_amount = round(line.quantity * product_price_unit * line.discount / 100, 2)
                self.add_segment(Segment("MOA", ["131", f"-{discount_amount:.2f}"]))
                alc_pcd_moa_segment = [
                    ("ALC", "A", "", "", "1", "DI"),
                    ("PCD", ["3", f"{line.discount:.2f}"]),
                    ("MOA", ["8", f"{discount_amount:.2f}"]),
                ]

            self.add_segment(Segment("PRI", ["AAB", f"{product_price_unit:.2f}", "", "", "", "PCE"]))

            if line.discount:
                self.add_segment(Segment(*alc_pcd_moa_segment))

            self.add_segment(Segment(("TAX", "7", "VAT", "", "", ["", "", "", f"{round(product_tax, 2):.2f}"])))

        # Summary
        self.add_segment(Segment("UNS", "S"))

        self.add_segment(Segment("MOA", ["77", f"{round(self.invoice.amount_total, 2):.2f}"]))     # Total TTC
        self.add_segment(Segment("MOA", ["79", f"{round(self.invoice.amount_untaxed, 2):.2f}"]))   # Total HT
        
        for product_tax, price_total in taxes.items():
            self.add_segment(Segment("TAX", "7", "VAT", "", "", ["", "", "", round(product_tax, 2)]))
            self.add_segment(Segment("MOA", ["125", f"{round(price_total, 2):.2f}"]))
            self.add_segment(Segment("MOA", ["124", f"{round(price_total * product_tax / 100, 2):.2f}"]))

        self.add_segment(self.get_footer_segment())


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

    def _get_gln(self, partner):
        gln = partner.id_numbers.filtered(lambda x: x.category_id.code == "gln_id_number")
        return gln[0].name if gln else False