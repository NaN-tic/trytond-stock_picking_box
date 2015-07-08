#This file is part stock_picking_box module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from trytond.pool import Pool
from .stock_picking_box import *

def register():
    Pool.register(
        StockPickingBoxOut,
        StockPickingBoxOutAssign,
        StockPickingBoxShipmentOutStart,
        StockPickingBoxShipmentOutResult,
        module='stock_picking_box', type_='model')
    Pool.register(
        StockPickingBoxShipmentOut,
        module='stock_picking_box', type_='wizard')
