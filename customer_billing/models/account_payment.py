# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2019. All rights reserved.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'out_receipt': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
    'in_receipt': 'supplier',
}

MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': 1,
    'in_invoice': -1,
    'out_refund': -1,
}


class RegisterBillingPayments(models.Model):
    _inherit = "account.payment"

    has_invoices = fields.Boolean(help="Technical field used for usability purposes")

    @api.depends('invoice_ids')
    def _get_has_invoices(self):
        self.has_invoices = bool(self.invoice_ids)

    def _get_invoices(self):
        context = dict(self._context or {})
        active_id = context.get('active_id')
        billing = self.env[context.get('active_model')].browse(active_id)
        invoice_ids = [invoice.id for invoice in billing.invoice_ids]
        invoices = self.env['account.move'].search([('state', '=', 'posted'), ('id', 'in', invoice_ids)])
        return invoices

    @api.model
    def default_get(self, default_fields):
        rec = super(RegisterBillingPayments, self).default_get(default_fields)

        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        if not active_ids or active_model != 'customer.billing':
            return rec

        if not active_model or not active_ids:
            raise UserError(
                _("Programmation error: wizard action executed without active_model or active_ids in context."))
        if active_model != 'customer.billing':
            raise UserError(_(
                "Programmation error: the expected model for this action is 'customer.billing'. The provided one is '%d'.") % active_model)

        invoices = self._get_invoices()
        if not invoices or any(invoice.state != 'posted' for invoice in invoices):
            raise UserError(_("You can only register payments for open invoices"))
        dtype = invoices[0].type
        for inv in invoices[1:]:
            if inv.type != dtype:
                if ((dtype == 'in_refund' and inv.type == 'in_invoice') or
                        (dtype == 'in_invoice' and inv.type == 'in_refund')):
                    raise UserError(
                        _("You cannot register payments for vendor bills and supplier refunds at the same time."))
                if ((dtype == 'out_refund' and inv.type == 'out_invoice') or
                        (dtype == 'out_invoice' and inv.type == 'out_refund')):
                    raise UserError(
                        _("You cannot register payments for customer invoices and credit notes at the same time."))

        amount = self._compute_payment_amount(invoices, invoices[0].currency_id, invoices[0].journal_id,
                                              rec.get('payment_date') or fields.Date.today())
        rec.update({
            'currency_id': invoices[0].currency_id.id,
            'amount': abs(amount),
            'payment_type': 'inbound' if amount > 0 else 'outbound',
            'partner_id': invoices[0].commercial_partner_id.id,
            'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].type],
            'communication': invoices[0].ref or invoices[0].name,
            'invoice_ids': [(6, 0, invoices.ids)],
        })
        return rec

    @api.onchange('journal_id')
    def _onchange_journal(self):
        res = super(RegisterBillingPayments, self)._onchange_journal()
        if self.env.context.get('active_model') == 'customer.billing':
            invoices = self._get_invoices()
            self.amount = abs(
                self._compute_payment_amount(invoices, self.currency_id, self.journal_id, self.payment_date))
        return res

    @api.onchange('currency_id')
    def _onchange_currency(self):
        res = super(RegisterBillingPayments, self)._onchange_currency()
        if self.env.context.get('active_model') == 'customer.billing':
            invoices = self._get_invoices()
            self.amount = abs(
                self._compute_payment_amount(invoices, self.currency_id, self.journal_id, self.payment_date))
        return res

    def get_payment_vals(self):
        res = {
            'journal_id': self.journal_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_date': self.payment_date,
            'communication': self.communication,
            'invoice_ids': [(4, inv.id, None) for inv in self._get_invoices()],
            'payment_type': self.payment_type,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_type': self.partner_type,
        }
        return res

    def create_payment(self):
        context = dict(self._context or {})
        active_id = context.get('active_id')
        payment = self.env['account.payment'].create(self.get_payment_vals())
        payment.post()
        bill_record = self.env[context.get('active_model')].browse(active_id)
        if bill_record.residual <= 0:
            bill_record.write({'state': 'paid'})
        return {'type': 'ir.actions.act_window_close'}
