-- Migration: Add appeal history tracking system
-- Description: Creates appeal_history table for tracking all appeal status changes and actions

-- Create appeal_history table
CREATE TABLE appeal_history (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appeal_pk UUID NOT NULL REFERENCES appeals(pk) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    actor_pk UUID REFERENCES users(pk) ON DELETE SET NULL,
    details JSONB,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_appeal_history_appeal_pk ON appeal_history(appeal_pk);
CREATE INDEX idx_appeal_history_action ON appeal_history(action);
CREATE INDEX idx_appeal_history_actor_pk ON appeal_history(actor_pk);
CREATE INDEX idx_appeal_history_created_at ON appeal_history(created_at);

-- Create composite index for common queries
CREATE INDEX idx_appeal_history_appeal_created ON appeal_history(appeal_pk, created_at);

-- Add check constraint for valid actions
ALTER TABLE appeal_history ADD CONSTRAINT chk_appeal_history_action
CHECK (action IN (
    'submitted',
    'assigned',
    'under_review',
    'sustained',
    'denied',
    'withdrawn',
    'content_restored',
    'sanction_applied'
));

-- Create function to automatically log appeal status changes
CREATE OR REPLACE FUNCTION log_appeal_status_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Log status changes
    IF TG_OP = 'INSERT' THEN
        INSERT INTO appeal_history (appeal_pk, action, actor_pk, details)
        VALUES (NEW.pk, 'submitted', NEW.appellant_pk,
                jsonb_build_object('initial_status', NEW.status));
        RETURN NEW;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        -- Log status changes
        IF OLD.status != NEW.status THEN
            INSERT INTO appeal_history (appeal_pk, action, actor_pk, details)
            VALUES (NEW.pk, NEW.status, NEW.reviewed_by,
                    jsonb_build_object(
                        'old_status', OLD.status,
                        'new_status', NEW.status,
                        'auto_logged', true
                    ));
        END IF;

        -- Log assignment changes
        IF OLD.reviewed_by IS DISTINCT FROM NEW.reviewed_by AND NEW.reviewed_by IS NOT NULL THEN
            INSERT INTO appeal_history (appeal_pk, action, actor_pk, details)
            VALUES (NEW.pk, 'assigned', NEW.reviewed_by,
                    jsonb_build_object(
                        'assigned_to', NEW.reviewed_by,
                        'auto_logged', true
                    ));
        END IF;

        RETURN NEW;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic appeal history logging
CREATE TRIGGER trigger_log_appeal_status_change
    AFTER INSERT OR UPDATE ON appeals
    FOR EACH ROW
    EXECUTE FUNCTION log_appeal_status_change();

-- Backfill existing appeals with initial history entries
INSERT INTO appeal_history (appeal_pk, action, actor_pk, details, created_at)
SELECT
    pk as appeal_pk,
    'submitted' as action,
    appellant_pk as actor_pk,
    jsonb_build_object('initial_status', status, 'backfilled', true) as details,
    created_at
FROM appeals
WHERE NOT EXISTS (
    SELECT 1 FROM appeal_history ah WHERE ah.appeal_pk = appeals.pk
);

-- Add additional history entries for appeals that have been processed
INSERT INTO appeal_history (appeal_pk, action, actor_pk, details, created_at)
SELECT
    pk as appeal_pk,
    status as action,
    reviewed_by as actor_pk,
    jsonb_build_object('backfilled', true, 'final_status', status) as details,
    updated_at
FROM appeals
WHERE status IN ('sustained', 'denied')
AND reviewed_by IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM appeal_history ah
    WHERE ah.appeal_pk = appeals.pk
    AND ah.action = appeals.status
);
