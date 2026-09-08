-- Migración: Auditoría de envío de comprobante electrónico por correo (PDF + XML)
-- Añade email_enviado y fecha_envio_email a facturas_electronicas.

ALTER TABLE facturas_electronicas
    ADD COLUMN IF NOT EXISTS email_enviado BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS fecha_envio_email TIMESTAMP;
