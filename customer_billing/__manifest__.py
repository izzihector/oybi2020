# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2019. All rights reserved.

{
    "name": "Customer Billing/Combined Invoices",
    "category": 'Accounting',
    'summary': 'Customer Billing for Several invoices.',
    "description": """
        Customer Billing allows you to combine several invoice (which is validated 
        but not paid yet) to single billing document, so each billing record will be list of invoice.
        This helps you to submit single combined invoice to customer and do a single payment against this. 
    """,
    "sequence": 1,
    "author": "Technaureus Info Solutions Pvt. Ltd.",
    "website": "http://www.technaureus.com/",
    "version": '13.0.0.1',
    'price': 60,
    'currency': 'EUR',
    'license': 'Other proprietary',
    "depends": ['account'],
    "data": [
        'data/billing_data.xml',
        'views/account_payment_view.xml',
        'views/customer_billing_view.xml',
        'security/ir.model.access.csv',
        'report/report_billing.xml',
        'report/report_billing_template.xml',
    ],
    'qweb': [],
    'images': ['images/customer_bill_screenshot.png'],
    "installable": True,
    "application": True,
    "auto_install": False,
    'live_test_url': 'https://www.youtube.com/watch?v=JpE_WnMX4qU'
}
