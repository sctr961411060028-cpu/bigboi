# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'United Arab Emirates - Payroll',
    'countries': ['ae'],
    'category': 'Human Resources/Payroll',
    'description': """
United Arab Emirates Payroll and End of Service rules.
=======================================================
- Basic Salary Calculations
- EOS Calculations

    """,
    'depends': ['hr_payroll', 'l10n_ae'],
    'data': [
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_salary_rule_data.xml',
        'data/hr_payslip_input_type_data.xml',
        'views/hr_contract_views.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}
