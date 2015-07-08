#This file is part stock_picking_box module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Equal, Not
from trytond.transaction import Transaction
import logging

__all__ = ['StockPickingBoxOut', 'StockPickingBoxOutAssign',
    'StockPickingBoxShipmentOutStart', 'StockPickingBoxShipmentOutResult',
    'StockPickingBoxShipmentOut']


class StockPickingBoxOut(ModelSQL, ModelView):
    'Stock Picking Box Out'
    __name__ = 'stock.picking.box.out'
    name = fields.Char('Name', required=True)
    warehouse = fields.Many2One('stock.location', 'Warehouse',
        domain=[('type', '=', 'warehouse')], required=True)
    sequence = fields.Integer('Sequence')
    active = fields.Boolean('Active', select=True)

    @staticmethod
    def default_sequence():
        return 1

    @staticmethod
    def default_active():
        return True


class StockPickingBoxOutAssign(ModelSQL, ModelView):
    'Stock Picking Box Out Assign'
    __name__ = 'stock.picking.box.out.assign'
    shipment = fields.Many2One('stock.shipment.out', 'Shipment', required=True,
        states={
            'readonly': Not(Equal(Eval('state'), 'waiting')),
        }, depends=['state'])
    box = fields.Many2One('stock.picking.box.out', 'Box', required=True,
        states={
            'readonly': Not(Equal(Eval('state'), 'waiting')),
        }, depends=['state'])
    user = fields.Many2One('res.user', 'User', required=True,
        states={
            'readonly': Not(Equal(Eval('state'), 'waiting')),
        }, depends=['state'])
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('done', 'Done'),
        ], 'State', readonly=True)

    @classmethod
    def __setup__(cls):
        super(StockPickingBoxOutAssign, cls).__setup__()
        cls._buttons.update({
            'done': {
                'invisible': Eval('state') == 'done',
                },
            'waiting': {
                'invisible': Eval('state') == 'waiting',
                },
            })

    @staticmethod
    def default_state():
        return 'waiting'

    @staticmethod
    def default_user():
        return Transaction().user

    @classmethod
    @ModelView.button
    def done(cls, carts):
        cls.write(carts, {
            'state': 'done',
            })

    @classmethod
    @ModelView.button
    def waiting(cls, carts):
        cls.write(carts, {
            'state': 'waiting',
            })

    @classmethod
    def assign(cls, shipment, attempts=0, total_attempts=5):
        pool = Pool()
        StockPickingBoxOut = pool.get('stock.picking.box.out')
        User = pool.get('res.user')

        transaction = Transaction()
        user = User(transaction.user)

        warehouse = None
        if hasattr(user, 'stock_warehouse'):
            warehouse = user.stock_warehouse

        # check if shipment is assigned in a waiting box
        assigned = cls.search([
            ('shipment', '=', shipment),
            ('state', '=', 'waiting'),
            ])
        if assigned:
            return

        try:
            # Locks transaction. Nobody can query this table
            transaction.cursor.lock(cls._table)
        except:
            # Table is locked. Captures operational error and returns void list
            if attempts < total_attempts:
                cls.assign(shipment, attempts+1, total_attempts)
            else:
                logging.getLogger('Stock Picking Box').warning(
                    'Table Shipment Box Out is lock after %s attempts' % (total_attempts))
                return
        else:
            # find boxes are available to assign
            domain = [('state', '=', 'waiting')]
            if warehouse:
                domain.append(('box.warehouse', '=', warehouse))
            boxes_assigned = cls.search(domain)

            domain = []
            if boxes_assigned:
                domain.append(('id', 'not in', [b.box.id for b in boxes_assigned]))
            if warehouse:
                domain.append(('warehouse', '=', warehouse))

            boxes = StockPickingBoxOut.search(domain, limit=1)
            if not boxes:
                return
            box, = boxes

            # assign shipment to box
            cls.create([{
                'shipment': shipment,
                'box': box,
                }])
            return box


class StockPickingBoxShipmentOutStart(ModelView):
    'Shipment Picking Box Shipment Out Start'
    __name__ = 'stock.picking.box.shipment.out.start'
    shipment = fields.Many2One('stock.shipment.out', 'Shipment', required=True)


class StockPickingBoxShipmentOutResult(ModelView):
    'Shipment Picking Box Shipment Out Result'
    __name__ = 'stock.picking.box.shipment.out.result'
    shipment = fields.Many2One('stock.shipment.out', 'Shipment', readonly=True)
    box = fields.Many2One('stock.picking.box.out', 'Box', readonly=True)


class StockPickingBoxShipmentOut(Wizard):
    'Shipment Picking Box Out'
    __name__ = 'stock.picking.box.shipment.out'
    start = StateTransition()
    picking = StateView('stock.picking.box.shipment.out.start',
        'stock_picking_box.shipment_out_start', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Assign', 'assign', 'tryton-ok', True),
            ])
    assign = StateTransition()
    result = StateView('stock.picking.box.shipment.out.result',
        'stock_picking_box.shipment_out_result', [
            Button('New Assign', 'picking', 'tryton-go-next', True),
            Button('Done', 'end', 'tryton-ok'),
            ])

    @classmethod
    def __setup__(cls):
        super(StockPickingBoxShipmentOut, cls).__setup__()
        cls._error_messages.update({
            'not_box': 'Shipment"%(shipment)s" could not assign any box. '
                'Please try again or wait to available new box.',
        })

    def transition_start(self):
        return 'picking'

    def transition_assign(self):
        pool = Pool()
        StockPickingBoxOutAssign = pool.get('stock.picking.box.out.assign')

        shipment = self.picking.shipment

        box = StockPickingBoxOutAssign.assign(shipment)
        if not box:
            self.raise_user_error('not_box', {
                'shipment': shipment.rec_name,
                })

        self.result.shipment = shipment
        self.result.box = box
        return 'result'

    def default_result(self, fields):
        return {
            'shipment': self.result.shipment.id,
            'box': self.result.box.id if self.result.box else None,
            }
