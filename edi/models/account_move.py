from odoo import models, fields, api
import base64
from io import StringIO
from datetime import datetime

class AccountMove(models.Model):
    _inherit = 'account.move'

    delivery_date = fields.Date(string="Date de livraison", compute="_compute_delivery_date", store=True)

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

        # En-tête du message UNH
        buffer.write(f"UNH+{self.id}+INVOIC:D:96A:EDIFACT:EAN008'\n")

        # Segment BGM (En-tête de la facture)
        buffer.write(f"BGM+380+{self.name}+9'\n")

        # Segment DTM (Date de la facture)
        buffer.write(f"DTM+137:{self.invoice_date.strftime('%Y%m%d')}:102'\n")

    # Vérifier si la date de livraison est disponible avant d'utiliser strftime
        if self.delivery_date:
            buffer.write(f"DTM+35:{self.delivery_date.strftime('%Y%m%d')}:102'\n")
        else:
            # Si la date de livraison est indisponible, utiliser la date de la facture comme fallback
            buffer.write(f"DTM+35:{self.invoice_date.strftime('%Y%m%d')}:102'\n")


        # Texte libre FTX (exemple de texte)
        buffer.write(f"FTX+ZZZ+++PAIEMENT ANTICIPE ACCEPTE'\n")

        # Référence bon de livraison (RFF)
        buffer.write(f"RFF+DQ:WH/OUT/0999'\n")

        # Date de livraison (répétée pour exemple)
        buffer.write(f"DTM+35:{self.invoice_date.strftime('%Y%m%d')}:102'\n")

        # Référence commande (RFF)
        buffer.write(f"RFF+ON:SO45786'\n")

        # Fournisseur NAD (exemple)
        buffer.write(f"NAD+SU+4399901102626::9++HAREAU SAS:nom société+rue fournisseur+ville fournisseur++12345+FR'\n")

        # Client (NAD+BY)
        buffer.write(f"NAD+BY+4399901860919::9++Client_{client}:Adresse client+rue client+ville client++54321+DE'\n")

        # Numéro fiscal (RFF)
        buffer.write(f"RFF+VA:DE123456789'\n")

        # Devise CUX
        buffer.write(f"CUX+2:EUR:4'\n")

        # Conditions de paiement (PAT)
        buffer.write(f"PAT+3'\n")

        # Date d'échéance
        buffer.write(f"DTM+35:{self.invoice_date_due.strftime('%Y%m%d')}:102'\n")

        # Lignes de facture (LIN, PIA, IMD, QTY, MOA)
        for line in self.invoice_line_ids:
            buffer.write(f"LIN+{line.id}++{line.product_id.barcode}:EAN'\n")
            buffer.write(f"PIA+1+{line.product_id.default_code}:SA'\n")
            buffer.write(f"IMD+A++::: {line.name}'\n")
            buffer.write(f"QTY+47:{int(line.quantity)}:PCE'\n")
            buffer.write(f"MOA+203:{line.price_subtotal}'\n")
            if line.discount:
                buffer.write(f"MOA+131:-{line.price_subtotal * line.discount / 100}'\n")
            buffer.write(f"PRI+AAB:{line.price_unit}'\n")

        # TVA et montants globaux (TAX, MOA)
        buffer.write(f"TAX+7+VAT+++:::19'\n")
        buffer.write(f"MOA+124:{self.amount_tax}'\n")
        buffer.write(f"MOA+77:{self.amount_total}'\n")
        buffer.write(f"MOA+125:{self.amount_untaxed}'\n")

        # Fin du message UNT
        buffer.write(f"UNT+21+1'\n")

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
    def _compute_delivery_date(self):
        """Récupérer la date de livraison depuis les bons de livraison dans le champ delivery_order_numbers."""
        for move in self:
            delivery_date = False

            if move.delivery_order_numbers:
                # Rechercher les bons de livraison (stock.picking) en utilisant les numéros dans delivery_order_numbers
                picking_ids = self.env['stock.picking'].search([
                    ('name', 'in', move.delivery_order_numbers.split(','))
                ])
                
                # Filtrer les pickings terminés
                completed_pickings = picking_ids.filtered(lambda p: p.state == 'done')

                if completed_pickings:
                    # Récupérer la date de livraison du premier picking terminé
                    delivery_date = completed_pickings[0].scheduled_date.date()

            # Mettre à jour la date de livraison
            move.delivery_date = delivery_date
