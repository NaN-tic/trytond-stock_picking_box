# This file is part of the stock_picking_box module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase


class StockPickingBoxTestCase(ModuleTestCase):
    'Test Stock Picking Box module'
    module = 'stock_picking_box'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        StockPickingBoxTestCase))
    return suite