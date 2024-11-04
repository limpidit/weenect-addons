from odoo import models, fields, api
import base64
from io import StringIO
from datetime import datetime

class AccountMove(models.Model):
    _inherit = 'account.move'

    delivery_date = fields.Date(string="Date de livraison", compute="_compute_delivery_info", store=True)
    delivery_order_number = fields.Char(string="Numéro de bon de livraison", compute="_compute_delivery_info", store=True)
    note=fields.Text("Notes")

    def generate_edifact_sagaflor(self):
        """Générer un fichier EDIFACT pour Sagaflor"""
        edifact_content = self._generate_edifact_content('Sagaflor')
        return self._download_file(edifact_content, 'sagaflor_invoice.txt')

    def generate_edifact_futterhaus(self):
        """Générer un fichier EDIFACT pour Futterhaus"""
        edifact_content = self._generate_edifact_content('Futterhaus')
        return self._download_file(edifact_content, 'futterhaus_invoice.txt')

    def _generate_edifact_content(self, client):
        """Créer le contenu EDIFACT en fonction des spécifications du client"""
        buffer = StringIO()
        segment_count = 0  # Initialiser le compteur de segments

        # En-tête du message UNH
        buffer.write(f"UNH+{self.id}+INVOIC:D:96A:UN:EAN008'\n")
        segment_count += 1  # Incrémenter le compteur de segments

        # Segment BGM (En-tête de la facture ou avoir)
        if self.move_type == 'out_invoice':
            buffer.write(f"BGM+380+{self.name}+9'\n")  # Facture
        elif self.move_type == 'out_refund':
            buffer.write(f"BGM+381+{self.name}+9'\n")  # Avoir
        segment_count += 1

        # Segment DTM (Date de la facture)
        buffer.write(f"DTM+137:{self.invoice_date.strftime('%Y%m%d')}:102'\n")
        segment_count += 1

        # Date de livraison
        if self.delivery_date:
            buffer.write(f"DTM+35:{self.delivery_date.strftime('%Y%m%d')}:102'\n")
        else:
            buffer.write(f"DTM+35:{self.invoice_date.strftime('%Y%m%d')}:102'\n")
        segment_count += 1

        # Texte libre FTX
        if self.note:
            buffer.write(f"FTX+ZZZ+++{self.note}'\n")
            segment_count += 1

        if self.move_type == 'out_refund' and self.ref:
            buffer.write(f"FTX+ZZZ+++{self.ref}'\n")
            segment_count += 1

        if self.delivery_order_number:
            buffer.write(f"RFF+DQ:{self.delivery_order_number}'\n")
            segment_count += 1

        # Référence commande
        if self.invoice_origin:
            buffer.write(f"RFF+ON:{self.invoice_origin}'\n")
            segment_count += 1

        gln_client = self.env['edi.param'].search([('key', '=', 'gln_client')], limit=1).value

        # Fournisseur NAD
        buffer.write(f"NAD+SU+{gln_client}::9++{self.company_id.name}+"
                    f"{self.company_id.street}+{self.company_id.city}++{self.company_id.zip}+{self.company_id.country_id.code}'\n")
        segment_count += 1

        # Numéro fiscal du fournisseur
        buffer.write(f"RFF+VA:{self.company_id.vat}'\n")
        segment_count += 1

        # Client NAD
        buffer.write(f"NAD+BY+{self.partner_id.vat}::9++{self.partner_id.name}+"
                    f"{self.partner_id.street}+{self.partner_id.city}++{self.partner_id.zip}+{self.partner_id.country_id.code}'\n")
        segment_count += 1

        # Numéro fiscal du client
        buffer.write(f"RFF+VA:{self.partner_id.vat}'\n")
        segment_count += 1

        if self.partner_shipping_id:
            buffer.write(f"NAD+DP+{self.partner_shipping_id.gln}::9++{self.partner_shipping_id.name}+"
                        f"{self.partner_shipping_id.street}+{self.partner_shipping_id.city}++{self.partner_shipping_id.zip}+{self.partner_shipping_id.country_id.code}'\n")
            segment_count += 1

            # Numéro fiscal du destinataire
            buffer.write(f"RFF+VA:{self.partner_shipping_id.vat}'\n")
            segment_count += 1

        # Devise CUX
        buffer.write(f"CUX+2:EUR:4'\n")
        segment_count += 1

        # Conditions de paiement
        buffer.write(f"PAT+3'\n")
        segment_count += 1

        # Date d'échéance
        buffer.write(f"DTM+209:{self.invoice_date_due.strftime('%Y%m%d')}:102'\n")
        segment_count += 1

        # Lignes de facture
        for line in self.invoice_line_ids.filtered(lambda r: r.display_type == "product"):
            buffer.write(f"LIN+{line.id}++{line.product_id.ean_weenect}:EAN'\n")
            segment_count += 1
            buffer.write(f"IMD+A++::: {line.name}'\n")
            segment_count += 1
            buffer.write(f"QTY+47:{int(line.quantity)}:PCE'\n")
            segment_count += 1
            buffer.write(f"MOA+203:{line.price_subtotal}'\n")
            segment_count += 1
            if line.discount:
                buffer.write(f"MOA+131:-{line.price_subtotal * line.discount / 100}'\n")
                segment_count += 1
            buffer.write(f"PRI+AAB:{line.price_unit}'\n")
            segment_count += 1
            for tax in line.tax_ids:
                buffer.write(f"TAX+7+VAT+++:::{int(tax.amount)}'\n")
                segment_count += 1

        # Totaux
        buffer.write(f"MOA+124:{self.amount_tax}'\n")
        segment_count += 1
        buffer.write(f"MOA+77:{self.amount_total}'\n")
        segment_count += 1
        buffer.write(f"MOA+125:{self.amount_untaxed}'\n")
        segment_count += 1

        # Fin du message UNT
        buffer.write(f"UNT+{segment_count}+{self.id}'\n")  # Remplacer 21 par le nombre de segments
        return buffer.getvalue()

    def _download_file(self, content, filename):
        """Génère une pièce jointe et fournit une URL pour télécharger le fichier."""
        # Encodage du contenu en base64
        file_content = base64.b64encode(content.encode('utf-8'))

        # Créer une pièce jointe dans Odoo pour le fichier
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': file_content,
            'res_model': 'account.move',
            'res_id': self.id,
            'mimetype': 'text/plain',  # Type MIME du fichier
        })

        # Retourner une action qui redirige vers le téléchargement de la pièce jointe
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    @api.depends('delivery_order_numbers')
    def _compute_delivery_info(self):
        """Calculer la date et les numéros de bon de livraison à partir des bons de livraison liés."""
        for move in self:
            delivery_date = False
            delivery_order_number = False

            if move.delivery_order_numbers:
                # Rechercher les bons de livraison (stock.picking) liés à la facture
                picking_ids = self.env['stock.picking'].search([
                    ('name', 'in', move.delivery_order_numbers.split(','))
                ])

                # Filtrer les bons de livraison terminés
                completed_pickings = picking_ids.filtered(lambda p: p.state == 'done')

                if completed_pickings:
                    # Récupérer la date de livraison du premier picking terminé
                    delivery_date = completed_pickings[0].scheduled_date.date()
                    # Récupérer les numéros des bons de livraison terminés
                    delivery_order_number = ', '.join(completed_pickings.mapped('name'))

            # Mettre à jour les champs de la facture
            move.delivery_date = delivery_date
            move.delivery_order_number = delivery_order_number
