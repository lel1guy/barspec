-- 015: purchase orders + receiving (the buy -> goods-in loop)
-- A PO freezes unit prices at creation (invoice-line honesty, same rule as
-- sales snapshots). Receiving records qty_in + unit price per line, so the
-- purchase ledger doubles as the item's price history. No mutation of the
-- count-based stock levels: counts own the physical numbers, POs own the
-- money trail. price drift vs the stored cost is detected at receive time
-- and the UI offers to apply it (with the usual ripple report).
CREATE TABLE purchase_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'received', 'cancelled')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    received_at TEXT
);

CREATE TABLE purchase_order_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    stock_item_id INTEGER NOT NULL REFERENCES stock_items(id),
    qty REAL NOT NULL DEFAULT 0,          -- in purchase units (bottles/cans/kegs)
    unit_price_eur REAL NOT NULL DEFAULT 0,  -- frozen at order time
    qty_received REAL NOT NULL DEFAULT 0
);
CREATE INDEX idx_po_lines_po ON purchase_order_lines(po_id);
CREATE INDEX idx_po_lines_item ON purchase_order_lines(stock_item_id);
