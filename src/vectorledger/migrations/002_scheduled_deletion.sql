ALTER TABLE vl_documents
    ADD COLUMN IF NOT EXISTS deletion_mode TEXT,
    ADD COLUMN IF NOT EXISTS deletion_requested_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS purge_after TIMESTAMPTZ;

ALTER TABLE vl_documents
    DROP CONSTRAINT IF EXISTS vl_documents_desired_state_check;

ALTER TABLE vl_documents
    ADD CONSTRAINT vl_documents_desired_state_check
    CHECK (desired_state IN ('active', 'pending_deletion', 'deleted'));

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'vl_documents_deletion_mode_check'
    ) THEN
        ALTER TABLE vl_documents
            ADD CONSTRAINT vl_documents_deletion_mode_check
            CHECK (deletion_mode IS NULL OR deletion_mode IN ('immediate', 'scheduled'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'vl_documents_deletion_schedule_check'
    ) THEN
        ALTER TABLE vl_documents
            ADD CONSTRAINT vl_documents_deletion_schedule_check
            CHECK (
                desired_state <> 'pending_deletion'
                OR (
                    deletion_mode = 'scheduled'
                    AND deletion_requested_at IS NOT NULL
                    AND purge_after IS NOT NULL
                    AND purge_after > deletion_requested_at
                )
            );
    END IF;
END $$;
