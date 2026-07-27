-- Adds the token-payment columns to the existing bookings table.
-- Run this once against your database (create_tables.py only creates
-- missing tables, it never alters existing ones).

ALTER TABLE bookings ADD COLUMN token_amount DECIMAL(10, 2) NULL;
ALTER TABLE bookings ADD COLUMN token_paid BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE bookings ADD COLUMN razorpay_payment_id VARCHAR(100) NULL;
