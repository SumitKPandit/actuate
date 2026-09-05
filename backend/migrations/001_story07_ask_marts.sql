ALTER TABLE daily_kpi ADD COLUMN IF NOT EXISTS open_sev1_count INTEGER;
ALTER TABLE daily_kpi ADD COLUMN IF NOT EXISTS unclassified_severity_count INTEGER;
ALTER TABLE vendor_kpi ADD COLUMN IF NOT EXISTS open_sev1_count INTEGER;
ALTER TABLE vendor_kpi ADD COLUMN IF NOT EXISTS unclassified_severity_count INTEGER;
ALTER TABLE vendor_kpi ADD COLUMN IF NOT EXISTS cost_outlier BOOLEAN;
ALTER TABLE office_kpi ADD COLUMN IF NOT EXISTS open_sev1_count INTEGER;
ALTER TABLE office_kpi ADD COLUMN IF NOT EXISTS unclassified_severity_count INTEGER;
CREATE TABLE IF NOT EXISTS shift_kpi (
    shift_type VARCHAR NOT NULL,
    cycle_or_month VARCHAR(32) NOT NULL,
    legs INTEGER,
    no_show_count INTEGER,
    no_show_rate FLOAT,
    PRIMARY KEY (shift_type, cycle_or_month)
);
