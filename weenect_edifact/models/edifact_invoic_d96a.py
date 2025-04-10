
from pydifact.segmentcollection import SegmentCollection
from pydifact.segments import Segment
import base64

class EdifactInvoicD96A:
    def __init__(self, invoice):
        self.invoice = invoice
        self.message = SegmentCollection()

    def generate(self):

        # UNH: header
        self.message.add_segment(Segment("UNH", self.invoice.id, ["INVOIC", "D", "96A", "UN", "EAN008"]))
        
        # BGM: invoice or credit note
        doc_code = "380" if self.invoice.move_type == "out_invoice" else "381"
        self.message.add_segment(Segment("BGM", [doc_code, self.invoice.name, "9"]))
