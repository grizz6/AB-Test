-- Are any values blank?
-- One row per column: how many NULLs it has and what share of rows that is.
WITH nulls AS (
    UNPIVOT (
        SELECT
            COUNT(*) - COUNT(f0)  AS f0,  COUNT(*) - COUNT(f1)  AS f1,
            COUNT(*) - COUNT(f2)  AS f2,  COUNT(*) - COUNT(f3)  AS f3,
            COUNT(*) - COUNT(f4)  AS f4,  COUNT(*) - COUNT(f5)  AS f5,
            COUNT(*) - COUNT(f6)  AS f6,  COUNT(*) - COUNT(f7)  AS f7,
            COUNT(*) - COUNT(f8)  AS f8,  COUNT(*) - COUNT(f9)  AS f9,
            COUNT(*) - COUNT(f10) AS f10, COUNT(*) - COUNT(f11) AS f11,
            COUNT(*) - COUNT(treatment)  AS treatment,
            COUNT(*) - COUNT(conversion) AS conversion,
            COUNT(*) - COUNT(visit)      AS visit,
            COUNT(*) - COUNT(exposure)   AS exposure
        FROM criteo
    ) ON COLUMNS(*) INTO NAME column_name VALUE n_null
)
SELECT
    column_name,
    n_null,
    n_null / (SELECT COUNT(*) FROM criteo) AS share_null
FROM nulls;
