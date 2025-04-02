
import pydifact
from pydifact.segments import Segment


class EdifactInvoicD01b:

    def __init__(self, invoice):
        self.invoice = invoice
        self.message = pydifact.SegmentCollection

    def _add_unh_segment(self):
        self.message.add_segment(
            Segment("UNH", self.invoice.id, ["INVOIC", "D", "01B", "UN", "EAN008"])
        )

    def _add_bgm_segment(self):
        move_type_code = {
            "out_invoice": "380",
            "in_invoice": "381"
        }.get(self.invoice_data.move_type, "381")
        self.message.add_segment(
            Segment("BGM", move_type_code, self.invoice.name, "9")
        )

    def generate_edifact(self):
        self._add_unh_segment()
        self._add_bgm_segment()
        return self.message.serialize()
    
