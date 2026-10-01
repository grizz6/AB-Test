-- How big is the dataset?
-- Total rows, plus counts of rows that break the dataset's own logic.
SELECT
    COUNT(*)                                     AS n_rows,
    COUNT_IF(exposure = 1 AND treatment = 0)     AS exposed_but_control,     -- must be 0: control never sees ads
    COUNT_IF(conversion = 1 AND visit = 0)       AS converted_without_visit  -- counted, not assumed to be 0
FROM criteo;
