

class EdifactInvoicD96A:
    def __init__(self):
        self.segments = []

    def get_unh_segment(self, id):
        return ("UNH", id, ["INVOIC", "D", "96A", "UN", "EAN008"])
