
from pydifact.segmentcollection import SegmentCollection
from pydifact.segments import Segment

from datetime import timedelta


class EdifactInvoicD01b:
    """Générateur de factures EDIFACT INVOIC D01B pour Odoo"""
    
    def __init__(self, invoice):
        self.invoice = invoice
        self.message = SegmentCollection()
    
    def generate(self):
        """Génère le message EDIFACT complet"""
        self._add_header()
        self._add_dates()
        self._add_parties()
        self._add_lines()
        self._add_totals()
        self._add_footer()
        return self.message
    
    def _add_header(self):
        """Ajoute l'en-tête du message"""
        # Segment UNH - En-tête de message
        self.message.add_segment(Segment('UNH', [self.invoice.name, 'INVOIC', 'D', '01B', 'UN']))
        
        # Segment BGM - Identification de la facture
        self.message.add_segment(
            Segment('BGM', ['380', self.invoice.name, '9']))
    
    def _add_dates(self):
        """Ajoute les segments de date"""
        # Date de facture (obligatoire)
        invoice_date = self.invoice.invoice_date.strftime('%Y%m%d')
        self.message.add_segment(
            Segment('DTM', ['137', invoice_date, '102']))
        
        # Date d'échéance si disponible
        if self.invoice.invoice_date_due:
            due_date = self.invoice.invoice_date_due.strftime('%Y%m%d')
            self.message.add_segment(
                Segment('DTM', ['13', due_date, '102']))
    
    def _add_parties(self):
        """Ajoute les informations sur les parties"""
        # Vendeur (SU)
        self._add_party('SU', self.invoice.company_id.partner_id)
        
        # Acheteur (BY)
        self._add_party('BY', self.invoice.partner_id)
    
    def _add_party(self, party_code, partner):
        """Ajoute les segments pour une partie"""
        # Segment NAD - Identification de la partie
        identifier = partner.vat or partner.ref or partner.name
        self.message.add_segment(
            Segment('NAD', [
                party_code,
                [identifier, '', '9'],  # 9 = SIRET
                partner.name
            ]))
        
        # Adresse (segments LOC)
        if partner.street: self._add_loc('7', partner.street)
        if partner.zip: self._add_loc('9', partner.zip)
        if partner.city: self._add_loc('8', partner.city)
        if partner.country_id: self._add_loc('10', partner.country_id.code)
    
    def _add_loc(self, qualifier, value):
        """Ajoute un segment LOC"""
        self.message.add_segment(Segment('LOC', [qualifier, value]))
    
    def _add_lines(self):
        """Ajoute les lignes de facture"""
        for idx, line in enumerate(self.invoice.invoice_line_ids, start=1):
            # Segment LIN - Ligne de facture
            product_code = line.product_id.barcode or line.product_id.default_code
            self.message.add_segment(
                Segment('LIN', [
                    str(idx),
                    '1',  # Action (1 = ajout)
                    [product_code, 'EN']  # EN = EAN
                ]))
            
            # Segment QTY - Quantité
            self.message.add_segment(
                Segment('QTY', ['47', str(line.quantity)]))
            
            # Segment MOA - Prix unitaire
            self.message.add_segment(
                Segment('MOA', ['203', str(line.price_unit)]))
            
            # Segment PIA - Référence fournisseur (si disponible)
            if line.product_id.seller_ids:
                supplier_code = line.product_id.seller_ids[0].product_code
                if supplier_code:
                    self.message.add_segment(
                        Segment('PIA', ['1', [supplier_code, 'SA']]))
    
    def _add_totals(self):
        """Ajoute les totaux"""
        # Montant total
        self.message.add_segment(
            Segment('MOA', ['9', str(self.invoice.amount_total)]))
        
        # Montant TVA
        self.message.add_segment(
            Segment('MOA', ['124', str(self.invoice.amount_tax)]))
    
    def _add_footer(self):
        """Ajoute le pied de page"""
        # Compter tous les segments sauf UNH et UNT
        segment_count = len(self.message.segments) + 1
        
        # Segment UNT - Fin de message
        self.message.add_segment(
            Segment('UNT', [str(segment_count), self.invoice.name]))
    
    def to_string(self):
        """Retourne le message sous forme de string"""
        return self.generate().serialize()
    
    def to_attachment(self):
        """Retourne les données pour un ir.attachment Odoo"""
        return {
            'name': f"{self.invoice.name}.edi",
            'datas': self.to_string().encode('iso-8859-1'),
            'res_model': 'account.move',
            'res_id': self.invoice.id,
            'type': 'binary'
        }