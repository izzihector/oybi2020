# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2019. All rights reserved.

from odoo import api, fields, models, _

TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}


class CustomerBilling(models.Model):
    _name = 'customer.billing'
    _inherit = ['mail.thread']
    _description = "Customer Billing"

    @api.model
    def _default_journal(self):
        inv_type = 'out_invoice'
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', [TYPE2JOURNAL[ty] for ty in inv_types if ty in TYPE2JOURNAL]),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)

    @api.model
    def _default_currency(self):
        journal = self._default_journal()
        return journal.currency_id or journal.company_id.currency_id

    @api.depends('invoice_ids','residual', 'state')
    def _compute_amount(self):
        for move in self:
            move.amount_untaxed = sum(inv.amount_untaxed for inv in move.invoice_ids)
            move.amount_tax = sum(inv.amount_tax for inv in move.invoice_ids)
            move.amount_total = move.amount_untaxed + move.amount_tax

            if move.state == 'confirm' and move.residual == 0:
                move.invoice_payment_state = 'paid'
                move.state = 'paid'
            else:
                move.invoice_payment_state = 'not_paid'

    @api.depends('invoice_ids', 'state', 'invoice_ids.amount_residual_signed', )
    def _compute_residual(self):
        self.residual = sum(inv.amount_residual_signed for inv in self.invoice_ids)

    name = fields.Char(string='Reference', index=True,
                       readonly=True, states={'draft': [('readonly', False)]}, copy=False, default='New')
    date_billing = fields.Date(string='Billing Date',
                               readonly=True, states={'draft': [('readonly', False)]}, index=True,
                               default=lambda self: self._context.get('date', fields.Date.context_today(self)),
                               copy=False)
    desc = fields.Char('Description', readonly=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', string='Customer', change_default=True,
                                 required=True, readonly=True, states={'draft': [('readonly', False)]},
                                 track_visibility='always')
    comment = fields.Text('Additional Information', readonly=True, states={'draft': [('readonly', False)]})
    invoice_payment_state = fields.Selection(selection=[
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid')],
        string='Payment', store=True, readonly=True, copy=False, tracking=True,
        compute='_compute_amount')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled'),
    ], string='Status', index=True, readonly=True, default='draft', track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Customer billing.\n"
             " * The 'Confirmed' status is used when user create customer billing, a billing number is generated. Its in confirm status till user does not pay the bill amount.\n"
             " * The 'Paid' status is set automatically when the invoices is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel billing.")
    invoice_ids = fields.Many2many('account.move', 'billing_invoice_rel', 'bill_id', 'inv_id',
                                   string='Invoices', readonly=True, states={'draft': [('readonly', False)]},
                                   copy=False)
    user_id = fields.Many2one('res.users', string='Salesperson', track_visibility='onchange',
                              readonly=True, states={'draft': [('readonly', False)]},
                              default=lambda self: self.env.user)
    type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('out_refund', 'Customer Refund'),
    ], readonly=True, index=True, change_default=True, default='out_invoice', track_visibility='always')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True, readonly=True, states={'draft': [('readonly', False)]},
                                  default=_default_currency, track_visibility='always')
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
                                 required=True, readonly=True, states={'draft': [('readonly', False)]},
                                 default=lambda self: self.env['res.company']._company_default_get('account.invoice'))
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', currency_field='currency_id',
                                     store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_tax = fields.Monetary(string='Tax', currency_field='currency_id',
                                 store=True, readonly=True, compute='_compute_amount')
    amount_total = fields.Monetary(string='Total', currency_field='currency_id',
                                   store=True, readonly=True, compute='_compute_amount')
    residual = fields.Monetary(string='Amount Due', currency_field='currency_id',
                               compute='_compute_residual', store=False, help="Remaining amount due.")

    @api.onchange('partner_id')
    @api.depends('partner_id', 'invoice_ids')
    def onchange_partner_id(self):
        existing_invoices = self.env['customer.billing'].search([('partner_id', '=', self.partner_id.id)])
        # invArr = [invoice.invoice_ids.name for invoice in invArr]
        inv_ids = self.env['account.move'].search([('state', '=', 'posted'),
                                            ('invoice_payment_state', '=', 'not_paid'),
                                            ('type', '=', 'out_invoice'),
                                            ('partner_id', '=', self.partner_id.id),
                                            ('company_id', '=', self.company_id.id),
                                            ('x_studio_eci_project_manager', '=', self.x_studio_eci_project_manager)])
                                            #('name','not in', existing_invoices.invoice_ids.name)])
        # if inv_ids:
        #     for inv_id in inv_ids:
        #         if inv_id not in invArr:
        self.invoice_ids = inv_ids.ids

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('customer.billing')
        if vals.get('invoice_ids'):
            inv_ids = vals.get('invoice_ids')[0][2]
            vals['invoice_ids'] = [(6, 0, inv_ids)]
        return super(CustomerBilling, self).create(vals)

    def write(self, vals):
        if vals and vals.get('invoice_ids'):
            if vals.get('invoice_ids')[0][2] != []:
                inv_ids = vals.get('invoice_ids')[0][2]
                vals['invoice_ids'] = [(6, 0, inv_ids)]
        return super(CustomerBilling, self).write(vals)

    def action_invoice_register_payment(self):
        return self.with_context(active_ids=self.ids, active_model='customer.billing', active_id=self.id) \
            .action_register_billing_payment()

    def action_register_billing_payment(self):
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return ''
        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'account.view_account_payment_invoice_form').id,
            'context': self.env.context,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def confirm_billing(self):
        self.write({'state': 'confirm'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_cancel_draft(self):
        self.write({'state': 'draft'})

    def action_print(self):
        self.ensure_one()
        return self.env.ref('customer_billing.customer_billing_report').report_action(self)
