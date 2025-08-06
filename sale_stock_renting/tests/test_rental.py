# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from freezegun import freeze_time
from odoo import Command
from odoo.fields import Datetime, Date
from odoo.tests import Form
from odoo.addons.sale_stock_renting.tests.test_rental_common import TestRentalCommon


class TestRentalWizard(TestRentalCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_rental_product_flow(self):

        self.assertEqual(
            self.product_id.qty_available,
            4
        )

        self.order_line_id1.write({
            'product_uom_qty': 3
        })

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin,
                self.order_line_id1.return_date,
                # self.order_line_id1.id,
            ), 3
        )

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin - timedelta(days=1),
                self.order_line_id1.return_date,
            ), 3
        )

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin,
                self.order_line_id1.return_date - timedelta(days=1),
            ), 3
        )

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin - timedelta(days=1),
                self.order_line_id1.return_date - timedelta(days=1),
            ), 3
        )

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin + timedelta(days=1),
                self.order_line_id1.return_date + timedelta(days=1),
            ), 3
        )

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin,
                self.order_line_id1.return_date + timedelta(days=1),
            ), 3
        )

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin + timedelta(days=1),
                self.order_line_id1.return_date,
            ), 3
        )

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin - timedelta(days=1),
                self.order_line_id1.return_date + timedelta(days=1),
            ), 3
        )

        self.assertEqual(
            self.product_id._get_unavailable_qty(
                self.order_line_id1.reservation_begin + timedelta(days=1),
                self.order_line_id1.return_date - timedelta(days=1),
            ), 3
        )

        """
            Total Pickup
        """

        self.order_line_id1.write({
            'qty_delivered': 3
        })

        """ In sale order warehouse """
        self.assertEqual(
            self.product_id.with_context(
                warehouse=self.order_line_id1.order_id.warehouse_id.id,
                from_date=self.order_line_id1.reservation_begin,
                to_date=self.order_line_id1.return_date,
            ).qty_available,
            1
        )

        self.env.invalidate_all()
        """ In company internal rental location (in stock valuation but not in available qty) """
        self.assertEqual(
            self.product_id.with_context(
                location=self.env.company.rental_loc_id.id,
                from_date=self.order_line_id1.start_date,
                to_date=self.order_line_id1.return_date,
            ).qty_available,
            3
        )

        """ In company warehouses """
        self.assertEqual(
            self.product_id.qty_available,
            1
        )

        """ In company stock valuation """
        self.assertEqual(
            self.product_id.quantity_svl,
            4
        )

        ####################################
        # Cancel deliver then re-apply
        ####################################

        self.order_line_id1.write({'qty_delivered': 0})
        self.assertEqual(self.product_id.qty_available, 4)
        self.order_line_id1.write({'qty_delivered': 3})

        """
            Partial Return
        """

        self.order_line_id1.write({
            'qty_returned': 2
        })

        """ In sale order warehouse """
        self.assertEqual(
            self.product_id.with_context(
                warehouse=self.order_line_id1.order_id.warehouse_id.id
            ).qty_available,
            3
        )

        """ In company internal rental location (in stock valuation but not in available qty) """
        self.assertEqual(
            self.product_id.with_context(
                location=self.env.company.rental_loc_id.id,
                from_date=self.order_line_id1.start_date,
                to_date=self.order_line_id1.return_date,
            ).qty_available,
            1
        )

        """ In company warehouses """
        self.assertEqual(
            self.product_id.qty_available,
            3
        )

        """ In company stock valuation """
        self.assertEqual(
            self.product_id.quantity_svl,
            4
        )

        """
            Total Return
        """

        self.order_line_id1.write({
            'qty_returned': 3
        })

        self.assertEqual(
            self.product_id.qty_available,
            4.0
        )

    def test_rental_lot_flow(self):
        self.lots_rental_order.action_confirm()

        lots = self.env['stock.lot'].search([('product_id', '=', self.tracked_product_id.id)])
        rentable_lots = self.env['stock.lot']._get_available_lots(self.tracked_product_id)
        self.assertEqual(set(lots.ids), set(rentable_lots.ids))  # set is here to ensure that order wont break test

        self.order_line_id2.reserved_lot_ids += self.lot_id1
        self.order_line_id2.product_uom_qty = 1.0

        self.order_line_id2.pickedup_lot_ids += self.lot_id2

        # Ensure lots are unreserved if other lots are picked up in their place
        # and qty pickedup = product_uom_qty (qty reserved)
        self.assertEqual(self.order_line_id2.reserved_lot_ids, self.order_line_id2.pickedup_lot_ids)

        return

    def test_rental_lot_concurrent(self):
        """The purpose of this test is to mimmic a concurrent picking of a rental product.
        As the same lot is applied to the sol twice, its qty_delivered should be 1.
        """
        so = self.lots_rental_order
        sol = self.order_line_id2
        lot = self.lot_id2

        sol.product_uom_qty = 1.0
        so.action_confirm()

        wizard_vals = so.action_open_pickup()
        for _i in range(2):
            wizard = self.env[wizard_vals['res_model']].with_context(wizard_vals['context']).create({
                'rental_wizard_line_ids': [
                    (0, 0, {
                        'order_line_id': sol.id,
                        'product_id': sol.product_id.id,
                        'qty_delivered': 1.0,
                        'pickedup_lot_ids':[[6, False, [lot.id]]],
                    })
                ]
            })
            wizard.apply()

        self.assertEqual(sol.qty_delivered, len(sol.pickedup_lot_ids), "The quantity delivered should not exceed the number of picked up lots")

        for _i in range(2):
            wizard = self.env[wizard_vals['res_model']].with_context(wizard_vals['context']).create({
                'rental_wizard_line_ids': [
                    (0, 0, {
                        'order_line_id': sol.id,
                        'product_id': sol.product_id.id,
                        'qty_returned': 1.0,
                        'returned_lot_ids':[[6, False, [lot.id]]],
                    })
                ]
            })
            wizard.apply()

        self.assertEqual(sol.qty_returned, len(sol.returned_lot_ids), "The quantity returned should not exceed the number of returned lots")

    def test_schedule_report(self):
        """Verify sql scheduling view consistency.

        One sale.order.line with 3 different lots (reserved/pickedup/returned)
        is represented by 3 sale.rental.schedule to allow grouping reservation information
        by stock.lot .

        Note that a lot can be pickedup (sol.pickedup_lot_ids) even if not reserved (sol.reserved_lot_ids).
        """
        self.order_line_id2.reserved_lot_ids = self.lot_id1
        # Avoid magic setting pickedup lots as reserved when full quantity has been pickedup
        self.order_line_id2.product_uom_qty = 2.0

        # Lot pickedup but not reserved.
        self.order_line_id2.pickedup_lot_ids = self.lot_id2

        self.assertEqual(
            self.env["sale.rental.schedule"].search_count([('lot_id', '=', self.lot_id2.id)]),
            1,
        )
        scheduling_recs = self.env["sale.rental.schedule"].search([
            ('order_line_id', '=', self.order_line_id2.id),
        ])
        self.assertEqual(
            len(scheduling_recs),
            2, # 1 reserved, 1 pickedup
        )
        self.assertEqual(
            scheduling_recs.mapped('report_line_status'),
            ["reserved", "pickedup"],
        )

        # More generic behavior:
        # 2 reserved, 2 pickedup, 1 returned
        self.order_line_id2.returned_lot_ids = self.lot_id2
        self.order_line_id2.pickedup_lot_ids += self.lot_id1
        self.env.invalidate_all()
        scheduling_recs = self.env["sale.rental.schedule"].search([
            ('order_line_id', '=', self.order_line_id2.id)
        ])
        self.assertEqual(
            len(scheduling_recs),
            2,
        )
        self.assertEqual(
            scheduling_recs.lot_id,
            self.lot_id1 + self.lot_id2,
        )
        self.assertEqual(
            scheduling_recs.mapped('report_line_status'),
            ["pickedup", "returned"],
        )

    def test_lot_accuracy_in_schedule(self):
        """ Schedule should only display lots that are associated with
        rental order lines
        """
        rental_schedule = self.env['sale.rental.schedule']
        rental_transfers_group = self.env.ref('sale_stock_renting.group_rental_stock_picking')
        self.env.user.groups_id = [(4, rental_transfers_group.id)]
        so = self.lots_rental_order
        so.company_id._create_rental_location()
        self.order_line_id2.product_uom_qty = 1.0
        so.order_line = [(6, 0, [self.order_line_id2.id])]
        so.action_confirm()

        # Rental schedule should have 1 out of the 3 total lots for `self.tracked_product_id`
        self.assertEqual(
            rental_schedule.search_count([('product_id', '=', self.tracked_product_id.id)]),
            1
        )

    @freeze_time('2025-01-01 09:10:15')
    def test_rental_forecast_with_rental_transfers(self):
        """
            With rental transfers enable, we check if the forecast rentable quantity takes
            incoming and outgoing moves happening prior to the rental period and other
            rental orders in its computation.
        """
        # Enable "rental transfers" and rely on the qty_in_rent fot the forecast
        self.env['res.config.settings'].create({'group_rental_stock_picking': True}).execute()
        self.assertTrue(self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'))
        product = self.env['product.product'].create({
            'name': 'Lovely Product',
            'type': 'product',
            'rent_ok': True,
        })
        # Put 100 units in stock
        self.env['stock.quant']._update_available_quantity(product, self.warehouse_id.lot_stock_id, 101)

        delivery = self.env['stock.picking'].create({
            'name': "Lovely Delivery",
            'location_id': self.warehouse_id.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'picking_type_id': self.warehouse_id.out_type_id.id,
            'scheduled_date': Datetime.today() + timedelta(days=2),
            'move_ids': [Command.create({
                'location_id': self.warehouse_id.lot_stock_id.id,
                'location_dest_id':  self.ref('stock.stock_location_customers'),
                'name': 'Lovely product move',
                'product_id': product.id,
                'product_uom_qty': 20,
            })]
        })
        delivery.action_confirm()
        # Create 2 rental orders: one to confirmed
        sale_orders = self.env['sale.order'].create([
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=1),
                'rental_return_date': Datetime.today() + timedelta(days=2),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 8.0,
                })],
            },
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=4),
                'rental_return_date': Datetime.today() + timedelta(days=6),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 10.0,
                })],
            },
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=5),
                'rental_return_date': Datetime.today() + timedelta(days=7),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 20.0,
                })],
            },
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=6),
                'rental_return_date': Datetime.today() + timedelta(days=8),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 30.0,
                })],
            },
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=1),
                'rental_return_date': Datetime.today() + timedelta(days=10),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 1.0,
                })],
            },
        ])

        """
        The last SO is here to create a rental order covering the entire renting periods.
        In a picture the delivery and the other rental orders are intertwined as follows:

        |    1    |    2    |    3    |    4    |    5    |    6    |    7    |    8    |    9    |    10    |

                   -20[-----------------------------------------------------------------------------------

                                       -10[-----------------]

                                                -20[------------------]

                                                            -30[----------------]

        """

        sale_orders.order_line.update({'is_rental': True})
        so = sale_orders[0]
        (sale_orders - so).action_confirm()
        self.assertEqual(so.order_line.virtual_available_at_date, 100)
        so.write({
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=4),
        })
        # We need to invalidate the cache after each change since the qty_in_rent does not have
        # any dependence and hence will only be recomputed if it was not already set in cache
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 80)
        so.write({
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=4) + timedelta(hours=1),
        })
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 70)
        so.write({
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=5),
        })
        product.invalidate_recordset()

        self.assertEqual(so.order_line.virtual_available_at_date, 70)
        so.write({
            'rental_start_date': Datetime.today() + timedelta(days=5),
            'rental_return_date': Datetime.today() + timedelta(days=6),
        })
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 50)
        so.write({
            'rental_start_date': Datetime.today() + timedelta(days=6),
            'rental_return_date': Datetime.today() + timedelta(days=8),
        })
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 30)
        so.action_confirm()
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 30)
        so.picking_ids.filtered(lambda p: p.picking_type_id == self.warehouse_id.out_type_id).button_validate()
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 30)

    def test_rental_forecast_without_rental_transfers(self):
        """
            With rental transfers disabled, we check if the forecast rentable quantity takes
            incoming and outgoing moves happening prior to the rental period and other
            rental orders in its computation.
        """
        # Disable "rental transfers" and rely on the qty_in_rent fot the forecast
        self.env['res.config.settings'].create({'group_rental_stock_picking': False}).execute()
        self.assertFalse(self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'))
        product = self.env['product.product'].create({
            'name': 'Lovely Product',
            'type': 'product',
            'rent_ok': True,
        })
        # Put 100 units in stock
        self.env['stock.quant']._update_available_quantity(product, self.warehouse_id.lot_stock_id, 100)

        delivery = self.env['stock.picking'].create({
            'name': "Lovely Delivery",
            'location_id': self.warehouse_id.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'picking_type_id': self.warehouse_id.out_type_id.id,
            'scheduled_date': Datetime.today() + timedelta(days=3),
            'move_ids': [Command.create({
                'location_id': self.warehouse_id.lot_stock_id.id,
                'location_dest_id':  self.ref('stock.stock_location_customers'),
                'name': 'Lovely product move',
                'product_id': product.id,
                'product_uom_qty': 20,
            })]
        })
        delivery.action_confirm()
        # Create 2 rental orders: one to confirmed
        so1, so2 = self.env['sale.order'].create([
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=1),
                'rental_return_date': Datetime.today() + timedelta(days=2),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 5.0,
                })],
            },
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=5),
                'rental_return_date': Datetime.today() + timedelta(days=6),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 10.0,
                })],
            },
        ])

        (so1 | so2).order_line.update({'is_rental': True})
        so2.action_confirm()
        self.assertFalse(so2.picking_ids)
        self.assertEqual(so1.order_line.virtual_available_at_date, 100)
        so1.write({
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=4),
        })
        # We need to invalidate the cache after each change since the qty_in_rent does not have
        # any dependence and hence will only be recomputed if it was not already set in cache
        product.invalidate_recordset()
        self.assertEqual(so1.order_line.virtual_available_at_date, 80)
        so1.write({
            'rental_start_date': Datetime.today() + timedelta(days=5),
            'rental_return_date': Datetime.today() + timedelta(days=6),
        })
        product.invalidate_recordset()
        self.assertEqual(so1.order_line.virtual_available_at_date, 70)
        so1.write({
            'rental_start_date': Datetime.today() + timedelta(days=7),
            'rental_return_date': Datetime.today() + timedelta(days=8),
        })
        product.invalidate_recordset()
        self.assertEqual(so1.order_line.virtual_available_at_date, 80)

    def test_rental_forecast_without_rental_transfers_and_with_pickup(self):
        """Ensure correct virtual availability calculation when
        'Rental Transfers' are disabled.

        Scenario:
        - Create a storable rental product with 10 units in stock.
        - Disable the 'Rental Transfer' setting.
        - Create two rental orders for the same period:
            * Order A: 9 units
            * Order B: 1 unit
        - Confirm and pick up Order A.
        - Check that Order B still shows 1 unit available.

        Expected:
        - Virtual availability before any confirmation: 10
        - After confirming and picking up Order A: Order B should still show 1 available unit.
        """
        # Disable rental transfers
        self.env['res.config.settings'].create({'group_rental_stock_picking': False}).execute()
        self.assertFalse(self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'))
        self.env['stock.quant']._update_available_quantity(self.product_id, self.warehouse_id.lot_stock_id, 6)
        # Create 2 rental orders for the same period
        start = Datetime.today() + timedelta(days=1)
        end = start + timedelta(days=1)
        so1, so2 = self.env['sale.order'].create([
            {
                'partner_id': self.cust1.id,
                'rental_start_date': start,
                'rental_return_date': end,
                'order_line': [Command.create({
                    'product_id': self.product_id.id,
                    'product_uom_qty': 9.0,
                })],
            },
            {
                'partner_id': self.cust1.id,
                'rental_start_date': start,
                'rental_return_date': end,
                'order_line': [Command.create({
                    'product_id': self.product_id.id,
                    'product_uom_qty': 1.0,
                })],
            },
        ])
        (so1 | so2).order_line.update({'is_rental': True})
        self.assertEqual(so2.order_line.virtual_available_at_date, 10)
        # Confirm Order A (9 units)
        so1.action_confirm()
        self.assertFalse(so1.picking_ids)
        self.assertTrue(so1.has_pickable_lines)
        # Check availability for Order B after confirming Order A
        so2.order_line.invalidate_recordset()
        self.assertEqual(so2.order_line.virtual_available_at_date, 1)
        # Simulate pickup of Order A
        pickup_action = so1.action_open_pickup()
        wizard = Form(self.env['rental.order.wizard'].with_context(pickup_action['context'])).save()
        with freeze_time(so1.order_line.start_date):
            wizard.apply()
        so2.order_line.invalidate_recordset()
        self.assertFalse(so1.has_pickable_lines)
        # Virtual availability should remain correct for Order B
        self.assertEqual(so2.order_line.virtual_available_at_date, 1)


class TestRentalPicking(TestRentalCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['res.config.settings'].create({'group_rental_stock_picking': True}).execute()

    def test_flow_1(self):
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 3, 'is_rental': True})
        rental_order_1.rental_start_date = self.rental_start_date
        rental_order_1.rental_return_date = self.rental_return_date
        rental_order_1.action_confirm()
        self.assertEqual(len(rental_order_1.picking_ids), 2)
        self.assertEqual([d.date() for d in rental_order_1.picking_ids.mapped('scheduled_date')],
                         [rental_order_1.rental_start_date.date(), rental_order_1.rental_return_date.date()])
        self.assertEqual(rental_order_1.picking_ids.move_ids.mapped('product_uom_qty'), [3.0, 3.0])

        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming')

        outgoing_picking.move_ids.quantity = 2
        backorder_wizard_dict = outgoing_picking.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 2)
        self.assertEqual(rental_order_1.rental_status, 'pickup')
        self.assertEqual(len(rental_order_1.picking_ids), 3)
        self.assertEqual(incoming_picking.move_ids.quantity, 2)

        incoming_picking.move_ids.quantity = 1
        backorder_wizard_dict = incoming_picking.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()
        self.assertEqual(rental_order_1.order_line.qty_returned, 1)
        self.assertEqual(rental_order_1.rental_status, 'pickup')
        self.assertEqual(len(rental_order_1.picking_ids), 4)

        outgoing_picking_2 = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing' and p.state == 'assigned')
        incoming_picking_2 = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming' and p.state == 'assigned')
        self.assertEqual(outgoing_picking_2.scheduled_date.date(), rental_order_1.rental_start_date.date())
        self.assertEqual(incoming_picking_2.scheduled_date.date(), rental_order_1.rental_return_date.date())
        self.assertEqual(outgoing_picking_2.move_ids.quantity, 1)
        self.assertEqual(incoming_picking_2.move_ids.quantity, 1)

        rental_order_1.order_line.write({'product_uom_qty': 5})
        self.assertEqual(outgoing_picking_2.move_ids.product_uom_qty, 3)
        self.assertEqual(incoming_picking_2.move_ids.product_uom_qty, 4)

        outgoing_picking_2.move_ids.quantity = 1
        backorder_wizard_dict = outgoing_picking_2.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 3)
        self.assertEqual(rental_order_1.rental_status, 'pickup')
        self.assertEqual(len(rental_order_1.picking_ids), 5)
        self.assertEqual(incoming_picking_2.move_ids.quantity, 2)

        rental_order_1.order_line.write({'product_uom_qty': 4})
        outgoing_picking_3 = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing' and p.state == 'assigned')
        self.assertEqual(outgoing_picking_3.scheduled_date.date(), rental_order_1.rental_start_date.date())
        self.assertEqual(outgoing_picking_3.move_ids.product_uom_qty, 1)
        self.assertEqual(incoming_picking_2.move_ids.product_uom_qty, 3)

        outgoing_picking_3.button_validate()
        self.assertEqual(incoming_picking_2.move_ids.quantity, 3)
        self.assertEqual(rental_order_1.order_line.qty_delivered, 4)
        self.assertEqual(rental_order_1.rental_status, 'return')

        incoming_picking_2.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_returned, 4)
        self.assertEqual(rental_order_1.rental_status, 'returned')

    def test_flow_multisteps(self):
        self.warehouse_id.delivery_steps = 'pick_pack_ship'
        self.warehouse_id.reception_steps = 'three_steps'

        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 3, 'is_rental': True})
        rental_order_1.rental_start_date = self.rental_start_date
        rental_order_1.rental_return_date = self.rental_return_date
        rental_order_1.action_confirm()
        self.assertEqual(len(rental_order_1.picking_ids), 6)
        self.assertEqual([d.date() for d in rental_order_1.picking_ids.mapped('scheduled_date')],
                         [rental_order_1.rental_start_date.date(), rental_order_1.rental_start_date.date(), rental_order_1.rental_start_date.date(),
                          rental_order_1.rental_return_date.date(), rental_order_1.rental_return_date.date(), rental_order_1.rental_return_date.date()])
        self.assertEqual(rental_order_1.picking_ids.move_ids.mapped('product_uom_qty'), [3.0, 3.0, 3.0, 3.0, 3.0, 3.0])

        rental_order_1.order_line.write({'product_uom_qty': 4})
        self.assertEqual(len(rental_order_1.picking_ids), 6)
        self.assertEqual(rental_order_1.picking_ids.move_ids.mapped('product_uom_qty'), [4.0, 4.0, 4.0, 4.0, 4.0, 4.0])

        pick_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(pick_picking.location_dest_id, self.warehouse_id.wh_pack_stock_loc_id)
        pick_picking.button_validate()
        rental_order_1.order_line.write({'product_uom_qty': 1})
        self.assertEqual(len(rental_order_1.picking_ids), 7)

        return_pick_picking = rental_order_1.picking_ids.filtered(lambda p: p.location_id == self.warehouse_id.wh_pack_stock_loc_id and p.location_dest_id == self.warehouse_id.lot_stock_id)
        all_other_pickings = rental_order_1.picking_ids.filtered(lambda p: p.state != 'done' and p.id != return_pick_picking.id)
        self.assertEqual(return_pick_picking.move_ids.product_uom_qty, 3.0)
        self.assertEqual(return_pick_picking.state, 'waiting')
        self.assertEqual(all_other_pickings.move_ids.mapped('product_uom_qty'), [1.0, 1.0, 1.0, 1.0, 1.0])
        return_pick_picking.action_assign()
        return_pick_picking.button_validate()

        pack_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(pack_picking.location_dest_id, self.warehouse_id.wh_output_stock_loc_id)
        pack_picking.button_validate()

        out_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(out_picking.location_dest_id, self.env.company.rental_loc_id)
        out_picking.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 1)

        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(incoming_picking.location_dest_id, self.warehouse_id.wh_input_stock_loc_id)
        incoming_picking.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_returned, 1)

        qc_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(qc_picking.location_dest_id, self.warehouse_id.wh_qc_stock_loc_id)
        qc_picking.button_validate()

        final_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(final_picking.location_dest_id, self.warehouse_id.lot_stock_id)
        final_picking.button_validate()

    def test_flow_serial(self):
        empty_lot = self.env['stock.lot'].create({
            'product_id': self.tracked_product_id.id,
            'name': "Dofus Ocre",
            'company_id': self.env.company.id,
        })
        available_lot = self.env['stock.lot'].create({
            'product_id': self.tracked_product_id.id,
            'name': "Dofawa",
            'company_id': self.env.company.id,
        })
        available_quant = self.env['stock.quant'].create({
            'product_id': self.tracked_product_id.id,
            'inventory_quantity': 1.0,
            'lot_id': available_lot.id,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        reserved_lot = self.env['stock.lot'].create({
            'product_id': self.tracked_product_id.id,
            'name': "Dolmanax",
            'company_id': self.env.company.id,
        })
        reserved_quant = self.env['stock.quant'].create({
            'product_id': self.tracked_product_id.id,
            'inventory_quantity': 1.0,
            'lot_id': reserved_lot.id,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        (available_quant + reserved_quant).action_apply_inventory()

        # Reserve 1 serial
        reserved_rental = self.sale_order_id.copy()
        reserved_rental.order_line.write({'product_id': self.tracked_product_id.id, 'reserved_lot_ids': reserved_lot, 'product_uom_qty': 1})
        reserved_rental.order_line.is_rental = True
        reserved_rental.rental_start_date = self.rental_start_date
        reserved_rental.rental_return_date = self.rental_return_date
        reserved_rental.action_confirm()

        # Test with 3 serials: 1 available, 1 reserved and 1 empty
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_id': self.tracked_product_id.id, 'reserved_lot_ids': available_lot + reserved_lot + empty_lot, 'product_uom_qty': 3})
        rental_order_1.order_line.is_rental = True
        rental_order_1.rental_start_date = self.rental_start_date
        rental_order_1.rental_return_date = self.rental_return_date
        rental_order_1.action_confirm()
        self.assertEqual(len(rental_order_1.picking_ids), 2)

        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(len(outgoing_picking.move_ids.move_line_ids), 3)
        self.assertEqual(outgoing_picking.move_ids.move_line_ids.lot_id, self.lot_id2 + self.lot_id3 + available_lot)

        outgoing_picking.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 3)
        self.assertEqual(available_lot.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.env.company.rental_loc_id)
        self.assertEqual(self.lot_id2.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.env.company.rental_loc_id)
        self.assertEqual(self.lot_id3.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.env.company.rental_loc_id)

        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(len(incoming_picking.move_ids.move_line_ids), 3)
        self.assertEqual(incoming_picking.move_ids.move_line_ids.lot_id, self.lot_id2 + self.lot_id3 + available_lot)

        incoming_picking.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_returned, 3)
        self.assertEqual(available_lot.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.warehouse_id.lot_stock_id)
        self.assertEqual(self.lot_id2.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.warehouse_id.lot_stock_id)
        self.assertEqual(self.lot_id3.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.warehouse_id.lot_stock_id)

    def test_late_fee(self):
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 1, 'is_rental': True})
        rental_order_1.rental_start_date = Datetime.now() - timedelta(days=7)
        rental_order_1.rental_return_date = Datetime.now() - timedelta(days=3)
        rental_order_1.action_confirm()

        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(outgoing_picking.scheduled_date.date(), rental_order_1.rental_start_date.date())
        outgoing_picking.button_validate()

        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(incoming_picking.scheduled_date.date(), rental_order_1.rental_return_date.date())
        incoming_picking.button_validate()

        self.assertEqual(len(rental_order_1.order_line), 2)
        late_fee_order_line = rental_order_1.order_line.filtered(lambda l: l.product_id.type == 'service')
        self.assertEqual(late_fee_order_line.price_unit, 30)

    def test_buttons(self):
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 3, 'is_rental': True})
        rental_order_1.action_confirm()

        action_open_pickup = rental_order_1.action_open_pickup()
        action_open_return = rental_order_1.action_open_return()
        self.assertEqual(action_open_pickup.get('res_id'), rental_order_1.picking_ids[0].id)
        self.assertEqual(action_open_pickup.get('domain'), '')
        self.assertEqual(action_open_pickup.get('xml_id'), 'stock.action_picking_tree_all')
        self.assertEqual(action_open_return.get('res_id'), 0)
        self.assertEqual(action_open_return.get('domain'), [('id', 'in', rental_order_1.picking_ids.ids)])
        self.assertEqual(action_open_return.get('xml_id'), 'stock.action_picking_tree_all')

        ready_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        ready_picking.button_validate()
        self.assertEqual(rental_order_1.rental_status, 'return')

        action_open_return_2 = rental_order_1.action_open_return()
        self.assertEqual(action_open_return_2.get('res_id'), rental_order_1.picking_ids[1].id)
        self.assertEqual(action_open_return_2.get('domain'), '')
        self.assertEqual(action_open_return_2.get('xml_id'), 'stock.action_picking_tree_all')

    def test_create_rental_transfers(self):
        """ E.g., a public/portal user signs & pays for an order via the portal
        """
        public_user = self.env.ref('base.public_user')
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 1, 'is_rental': True})
        rental_order_1.with_user(public_user).sudo().action_confirm()
        self.assertTrue(rental_order_1.picking_ids)

    def test_reordering_rule_forecast(self):
        """ Test the rental orders will only consider outgoing rental move in the forecast
        computation. """
        # Set a fixed visibility_days
        self.product_id.stock_quant_ids.sudo().unlink()
        self.env['ir.config_parameter'].sudo().set_param('stock.visibility_days', 7)
        date = Date.today() + timedelta(days=7)

        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 1, 'is_rental': True})
        rental_order_1.rental_start_date = Datetime.now() + timedelta(days=2)
        rental_order_2 = self.sale_order_id.copy()
        rental_order_2.order_line.write({'product_uom_qty': 2, 'is_rental': True})
        rental_order_2.rental_start_date = Datetime.now() + timedelta(days=4)
        rental_order_2.rental_return_date = Datetime.now() + timedelta(days=5)
        self.assertEqual(self.product_id.with_context(date=date).qty_available, 0)
        (rental_order_1 | rental_order_2).action_confirm()
        self.env['stock.warehouse.orderpoint'].action_open_orderpoints()
        self.assertEqual(self.product_id.orderpoint_ids.lead_days_date, date)
        self.assertEqual(self.product_id.orderpoint_ids.qty_forecast, -2)

    def test_rental_available_reserved_lots(self):
        """
            The aim is to check if the `available_reserved_lots` compute
            field correctly determines whether a batch we want to reserve
            will be available or not.
        """
        # Create a sale order to reserve a lot.
        sale_order_id1 = self.env['sale.order'].create({
            'partner_id': self.cust1.id,
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=4),
        })
        order_line_id1 = self.env['sale.order.line'].create({
            'order_id': sale_order_id1.id,
            'product_id': self.tracked_product_id.id,
            'reserved_lot_ids': [Command.set(self.lot_id1.ids)],
            'product_uom_qty': 1.0,
        })
        order_line_id1.update({'is_rental': True})
        sale_order_id1.action_confirm()

        # Create a second sale order and modify reserved lots, start date
        # and return date to check if `available_reserved_lots` is correct.
        sale_order_id = self.env['sale.order'].create({
            'partner_id': self.cust1.id,
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=4),
        })
        order_line_id = self.env['sale.order.line'].create({
            'order_id': sale_order_id.id,
            'product_id': self.tracked_product_id.id,
            'product_uom_qty': 1.0,
        })
        order_line_id.update({'is_rental': True})

        self.assertEqual(order_line_id.available_reserved_lots, True)
        order_line_id.reserved_lot_ids = self.lot_id2
        self.assertEqual(order_line_id.available_reserved_lots, True)
        order_line_id.reserved_lot_ids += self.lot_id1
        self.assertEqual(order_line_id.available_reserved_lots, False)
        sale_order_id.write({
            'rental_start_date': Datetime.today() + timedelta(days=1),
            'rental_return_date': Datetime.today() + timedelta(days=2),
        })
        self.assertEqual(order_line_id.available_reserved_lots, True)
        sale_order_id.write({
            'rental_start_date': Datetime.today() + timedelta(days=5),
            'rental_return_date': Datetime.today() + timedelta(days=6),
        })
        # will return in stock in time
        self.assertEqual(order_line_id.available_reserved_lots, True)

        # Validate the delivery of the first order to test the flow
        # when the product is not in stock
        delivery = sale_order_id1.picking_ids.filtered(lambda p: p.picking_type_id == self.warehouse_id.out_type_id)
        delivery.button_validate()
        self.assertEqual(delivery.state, 'done')
        self.assertEqual(delivery.move_ids.lot_ids, self.lot_id1)
        self.assertEqual(order_line_id1.available_reserved_lots, True)
        sale_order_id.write({
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=4),
        })
        order_line_id.reserved_lot_ids = self.lot_id2
        self.assertEqual(order_line_id.available_reserved_lots, True)
        order_line_id.reserved_lot_ids += self.lot_id1
        self.assertEqual(order_line_id.available_reserved_lots, False)
        sale_order_id.write({
            'rental_start_date': Datetime.today() + timedelta(days=1),
            'rental_return_date': Datetime.today() + timedelta(days=2),
        })
        self.assertEqual(order_line_id.available_reserved_lots, False)
        sale_order_id.write({
            'rental_start_date': Datetime.today() + timedelta(days=5),
            'rental_return_date': Datetime.today() + timedelta(days=6),
        })
        self.assertEqual(order_line_id.available_reserved_lots, True)

    def test_no_cogs_for_rental_invoice_anglo_saxon(self):
        """Ensure no COGS or inventory valuation journal entries are created for rental products in Anglo-Saxon mode."""

        # Setup: Anglo-Saxon mode and real-time inventory valuation
        self.env.company.anglo_saxon_accounting = True
        self.product_id.categ_id.property_valuation = 'real_time'
        self.product_id.standard_price = 100.0

        sale_order = self.env['sale.order'].create({
            'partner_id': self.cust1.id,
            'rental_start_date': Datetime.now(),
            'rental_return_date': Datetime.now() + timedelta(days=3),
            'order_line': [
                Command.create({
                    'product_id': self.product_id.id,
                    'product_uom_qty': 2,
                    'price_unit': 1000.0,
                    'is_rental': True,
                }),
                Command.create({
                    'product_id': self.product_id.id,
                    'product_uom_qty': 1,
                    'price_unit': 1000.0,
                }),
            ],
        })

        sale_order.action_confirm()
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Get the invoice lines
        rental_lines = invoice.line_ids.filtered(lambda l: any(sl.is_rental for sl in l.sale_line_ids))
        non_rental_lines = invoice.line_ids.filtered(lambda l: all(not sl.is_rental for sl in l.sale_line_ids))

        # Fetch valuation-related journal lines from the invoice's journal entry
        move_lines = invoice.line_ids
        valuation_account_ids = {
            self.product_id.categ_id.property_stock_valuation_account_id.id,
            self.product_id.categ_id.property_account_expense_categ_id.id,
        }

        valuation_lines = move_lines.filtered(lambda l: l.account_id.id in valuation_account_ids)

        # Check: No valuation entries tied to rental lines
        for rental_line in rental_lines:
            self.assertFalse(
                valuation_lines.filtered(lambda l: l.cogs_origin_id == rental_line),
                "Rental invoice line should not generate COGS or inventory valuation journal entries."
            )

        # Check: Non-rental line should generate valuation
        self.assertTrue(
            valuation_lines.filtered(lambda l: l.cogs_origin_id == non_rental_lines[0]),
            "Non-rental invoice line should generate COGS or valuation entry."
        )
